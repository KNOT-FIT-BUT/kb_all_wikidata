#!/usr/bin/env python3
# encoding UTF-8

# File: parseJson2.py
# Author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# Project: wikidata2
# Description: Parses wikidata json dump to tsv. Uses classes as entity ids.
#              Builds relation graph of entities and sorts type according to the most specific class.

import sys  # stderr, exit, ...
import argparse
import json  # load data from dump
import os  # filesystem
import hashlib  # generate temp file name
import time  # generate temp file name, timestamps
import re  # find ids for substitution
import traceback  # for printing exceptions

# get script name
SCRIPT_NAME = os.path.basename(sys.argv[0])


def get_args():
    """
    Parses arguments from command line.
    :return: parsed arguments
    """
    argparser = argparse.ArgumentParser(
        'Parses wikidata json dump to tsv and parses wikidata classes relations.'
    )
    argparser.add_argument(
        '-f', '--input-file',
        help='Input file to process.',
        required=True,
        type=argparse.FileType('r')
    )
    argparser.add_argument(
        '-o', '--output-file',
        help='TSV output file.',
        required=True,
        type=argparse.FileType('w')
    )
    argparser.add_argument(
        '-d', '--dict-file',
        help='Output dictionary file, with entity names.',
        required=False
    )
    argparser.add_argument(
        '-c', '--class-relations-dump',
        help='Class relations dump file.',
        required=False
    )
    argparser.add_argument(
        '--show-missing',
        help='Display ids with missing translation.',
        required=False,
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '-b', '--buffer-level',
        help='Specifies how much memory buffering is used. '
             'Level 0: No buffering. '
             'Level 1: Buffer dictionary. '
             'Level 2: Buffer dictionary and parsed entities.',
        required=False,
        default=0,
        type=int
    )
    argparser.add_argument(
        '--full-paths',
        help='Sets type of entities to show full path to entity class instead of just list of all types.',
        required=False,
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '--keep-root-class',
        help='If this option is used, root class is not removed from list of ids in type of entity.',
        required=False,
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '--root-class-id',
        help='Defines root class id that will be removed from list of ids in type of entity.'
             ' Default: Q35120 (entity)',
        required=False,
        default='Q35120'
    )
    argparser.add_argument(
        '--no-cleanup',
        help='Disable automatic removal of temporary files.',
        required=False,
        default=False,
        action='store_true'
    )
    # create group for arguments that should not be given together
    # this automatically handles bad argument combinations
    parsing_restrictions_group = argparser.add_mutually_exclusive_group()
    parsing_restrictions_group.add_argument(
        '-n', '--number-of-entities',
        help='Parse only given number of entities.',
        required=False,
        type=int,
        default=None
    )
    parsing_restrictions_group.add_argument(
        '-l', '--line',
        help='Parse only line with given number.',
        required=False,
        type=int,
        default=None
    )
    # mutually exclusive group for parsing sections
    parsing_sections = argparser.add_mutually_exclusive_group()
    parsing_sections.add_argument(
        '--parse-only',
        help='Only parse wikidata dump to tsv, without type and name substitution. Can also generate class relations '
             'dump and dictionary file.',
        default=False,
        action='store_true'
    )
    parsing_sections.add_argument(
        '--substitute-type-only',
        help='Only substitute type of entities. Input must be already parsed dump without translated names. '
             'Class relations dump must be specified!',
        default=False,
        action='store_true'
    )
    parsing_sections.add_argument(
        '--substitute-names-only',
        help='Translates wikidata ids for entity names. Input file must be already parsed dump. Dictionary file must '
             'be specified!',
        default=False,
        action='store_true'
    )
    return argparser.parse_args()


class WikidataDumpManipulator:
    """
    Includes some common functions needed for manipulating wikidata dump
    """

    @staticmethod
    def gen_multival_field(*args):
        """
        Generates multiple value field
        :param args: list of input arguments
        :return: string where arguments are separated by |
        """
        return '|'.join(arg for arg in args if arg)

    @staticmethod
    def write_entity_to_tsv(entity, file):
        """
        Writes entity to tsv file
        :param entity: entity to write
        :param file: file where entity will be written to
        """
        for i in range(0, len(entity) - 1):
            file.write(entity[i] + '\t')  # add tabs between fields
        file.write(entity[-1] + '\n')  # add eol after last field


class WikidataDumpParser(WikidataDumpManipulator):
    """
    Parses wikidata dump and builds class relations
    """

    def __init__(self, input_file, output_file=None, dict_file=None, lang='en', class_relations_builder=None):
        # files
        self.input_file = input_file
        self.output_file = output_file
        self.dict_file = dict_file
        # data structures
        self.dictionary = {}  # dictionary for name substitution
        self.entities = []  # list of entities used if buffer_entities is true
        self.class_relations_builder = class_relations_builder  # class relations builder instance
        # counters
        self.line_number = 1
        self.processed_records = 0
        self.corrupted_records = 0
        # setup
        self.lang = lang  # parsed labels language
        self.buffer_entities = False  # store parsed entities in memory
        self.buffer_dictionary = False  # store dictionary in memory
        self.max_entities = 0  # maximum number of entities to parse (0 = disabled)
        self.dump_line = 0  # dump single line (0 = disabled)

    @property
    def max_entities(self):
        try:
            return self._max_entities
        except AttributeError:  # if used before value is set
            return 0

    @max_entities.setter
    def max_entities(self, value):
        if type(value) != int:
            raise TypeError("Value has to be int!")
        if self.dump_line:
            raise ValueError("dump_line and max_entities are mutually exclusive!")
        self._max_entities = value

    @property
    def dump_line(self):
        try:
            return self._dump_line
        except AttributeError:  # if used before value is set
            return 0

    @dump_line.setter
    def dump_line(self, value):
        if type(value) != int:
            raise TypeError("Value has to be int!")
        if self.max_entities:
            raise ValueError("dump_line and max_entities are mutually exclusive!")
        if self.max_entities < 0:
            raise ValueError("Value has to be higher or equal to 0!")
        self._dump_line = value

    def parse_record(self, record):
        """
        Parses one json record from wikidata dump file
        :param record: record converted to dict
        :return: parsed entity
        """

        """
        Parsed data:
        0 ID
        1 INSTANCE OF (MULTIPLE VALUES)  (TYPE of entity)
        2 NAME
        3 DISAMBIGUATION NAME
        4 ALIASES (MULTIPLE VALUES)
        5 DESCRIPTION
        6 ROLES (MULTIPLE VALUES)
        7 FICTIONAL
        8 WIKIPEDIA URL
        9 WIKIDATA URL
        10 DBPEDIA URL
        11 IMAGES (MULTIPLE VALUES)
        """
        entity = ['', '', '', '', '', '', '', '', '', '', '', '']

        # id
        if 'id' in record:
            entity[0] = record['id']
            if not entity[0]:  # sometimes id is empty
                return None
        else:  # fail if identifier is missing
            return None

        # name
        if 'labels' in record and self.lang in record['labels']:
            entity[2] = record['labels'][self.lang]['value']

        # aliases
        if 'aliases' in record and self.lang in record['aliases']:
            for value in record['aliases'][self.lang]:
                entity[4] = self.gen_multival_field(entity[4], value['value'])

        # description
        if 'descriptions' in record and self.lang in record['descriptions']:
            entity[5] = record['descriptions'][self.lang]['value']

        # instance of  and image
        if 'claims' in record:
            if 'P31' in record['claims']:  # P31 == instance of
                for statement in record['claims']['P31']:
                    try:
                        if statement['mainsnak']['datavalue']['value']['entity-type'] == 'item':
                            entity[1] = self.gen_multival_field(entity[1],
                                                                statement['mainsnak']['datavalue']['value']['id'])
                    except KeyError:
                        # no such value in the current statement - skip
                        pass

            if 'P18' in record['claims']:  # P18 == image
                for picture in record['claims']['P18']:
                    try:
                        # commonsMedia = is name of media file (picture)
                        if picture['mainsnak']['datavalue']['datatype'] == 'commonsMedia':
                            entity[11] = self.gen_multival_field(entity[11], picture['mainsnak']['datavalue']['value'])
                    except KeyError:
                        # can't extract image name - value not present - skip
                        pass

            # add relation to relations builder
            if 'P279' in record['claims']:  # P279 == subclass of
                for statement in record['claims']['P279']:
                    try:
                        # subclass of
                        if statement['mainsnak']['datavalue']['value']['entity-type'] == 'item':
                            if self.class_relations_builder:
                                self.class_relations_builder.add_ancestor(
                                    record['id'],  # entity id
                                    statement['mainsnak']['datavalue']['value']['id'])  # id of related entity
                    except KeyError:
                        # can't extract related class - value is not present - skip
                        pass

        # wikipedia url
        if 'sitelinks' in record and self.lang + 'wiki' in record['sitelinks']:
            try:
                entity[8] = 'http://' + self.lang + '.wikipedia.org/wiki/' + '_'.join(
                    record['sitelinks'][self.lang + 'wiki']['title'].split())
            except KeyError:  # title not found, record is corrupted
                entity[8] = ''

        # wikidata url
        entity[9] = 'https://www.wikidata.org/wiki/' + entity[0]

        return entity

    def parse_wikidump(self):
        """
        Parses wikidata dump file to tsv and creates dictionary for name substitution
        :return: execution status
        """

        for line in self.input_file:

            if self.dump_line:  # dump single line
                if self.line_number != self.dump_line:
                    self.line_number += 1
                    continue

            if len(line) > 2:  # first and last lines will be empty (contains only bracket removed by line = line[:-1])
                if line[-2] == ",":
                    line = line[:-2]  # remove comma and newline
                else:
                    line = line[:-1]  # last record doesn't have comma, remove only newline
                try:
                    record = json.loads(line)  # convert to dictionary
                except json.JSONDecodeError:
                    self.corrupted_records += 1
                else:
                    entity = self.parse_record(record)
                    if entity is None:  # entity missing id
                        self.corrupted_records += 1
                    else:
                        if self.output_file:  # write entity to output file
                            self.write_entity_to_tsv(entity, self.output_file)
                        if self.buffer_entities:  # add to memory list of entities
                            self.entities.append(entity)

                        # generate dictionary file to replace IDs for names
                        # written fields: entity[0] == id, entity[2] == name
                        if entity[2]:  # check if name is not empty
                            if self.dict_file:  # add to dictionary file
                                self.write_entity_to_tsv([entity[0], entity[2]], self.dict_file)
                            if self.buffer_dictionary:  # add to memory dictionary for name substitution
                                self.dictionary[entity[0]] = entity[2]

                        self.processed_records += 1

            # if dumping single line, break cycle after done
            if self.dump_line:
                break

            # maximum number of entities reached
            elif self.max_entities and self.max_entities <= self.processed_records:
                break

            self.line_number += 1

        return 0


class WikidataNameInterchanger(WikidataDumpManipulator):
    """
    Substitutes wikidata ids for names in parsed dump
    """

    def __init__(self,
                 output_file,
                 input_file=None,
                 dict_file=None,
                 dictionary=None,
                 dump=None,
                 show_missing=False,
                 exclude=(0, 8, 9, 10, 11)
                 ):
        # files
        self.output_file = output_file  # output file where translated data will be written to
        self.input_file = input_file  # input file with entities for translation
        self.dict_file = dict_file  # file with dictionary used for translation

        # memory
        self.dictionary = dictionary  # dictionary buffered in memory
        self.dump = dump  # dump buffered in memory

        self.show_missing = show_missing  # enables additional info collecting
        # ids without translation are added to this list if show_missing == True
        # id without translation is any id from kb that is not found in dictionary
        self.ids_without_translation = []

        # excluded field indexes
        self.excluded = exclude  # array or tuple of indexes of fields where names will not be substituted
        # self.excluded: useful for site urls, ids, picture/file names, etc.

    @property
    def show_missing(self):
        return self._show_missing

    @show_missing.setter
    def show_missing(self, value):
        if type(value) is not bool:
            raise TypeError("Value must be bool!")
        else:
            self._show_missing = value

    def substitute_names(self):
        """
        Substitutes ids in parsed records for names matching this id from dictionary file.
        Note that if both input_file and dump variables are set, function will rather use file
        than memory dump buffer! To use buffer, don't set the input file variable!
        :raise ValueError if data source is not set
        :return: execution status
        """
        if self.input_file:  # input is read from file
            input_data = self.input_file
        elif self.dump:  # input is read from list in memory
            input_data = self.dump
        else:
            raise ValueError("Input data source is not set up!")

        if not self.dictionary:  # load dictionary from file
            self.load_dict_from_file()

        for line in input_data:
            if type(line) == str:  # if input is tsv file line, split it to list by tabs
                line = line[:-1]  # remove newline from end of the line
                line = line.split('\t')
            for i in range(len(line)):
                if i in self.excluded:  # skip entity id, urls, file names, etc. (indexes defined in self.excluded)
                    continue
                entity_ids = re.findall('Q\d+', line[i])  # match all ids on line
                # sort ids from longest to shortest (otherwise shorter id will replace first part of longer)
                entity_ids.sort(key=lambda x: len(x), reverse=True)
                for entity_id in entity_ids:  # replace id by name matched by dictionary
                    try:
                        line[i] = line[i].replace(entity_id, self.dictionary[entity_id])
                    except KeyError:  # entity name is not in dictionary
                        if self.show_missing and entity_id not in self.ids_without_translation:
                            self.ids_without_translation.append(entity_id)
            self.write_entity_to_tsv(line, self.output_file)

        return 0

    def load_dict_from_file(self):
        """
        Loads dictionary from file
        :raise ValueError if dictionary file is not set or if dictionary is loaded already
        """
        if not self.dict_file:
            raise ValueError("Dictionary file not set!")
        if self.dictionary:
            raise ValueError("Dictionary already full!")
        else:
            self.dictionary = {}
            for line in self.dict_file:
                line = line[:-1]  # remove newline
                line = line.split('\t')
                self.dictionary[line[0]] = line[1]
            return 0


class ClassRelationsBuilder(WikidataDumpManipulator):
    """
    Builds class relation graph and replaces type of entities by class paths.
    """

    def __init__(self, classes=None, dump_file=None, output_file=None):
        """
        Initializes class dictionary
        :param classes: dictionary with existing class relations
        :param dump_file: file with dump of class relations
        :param output_file: file where to put processed entities
        """
        self.classes = classes if classes else {}  # dictionary with class relations
        self.dump_file = dump_file  # file with dump of class relations
        self.output_file = output_file  # file where to put processed entities

    def add_class(self, class_id):
        """
        Adds new class to dictionary.
        :class_id: id of the class
        """
        if class_id not in self.classes:
            self.classes[class_id] = {}
            self.classes[class_id]['successors'] = []
            self.classes[class_id]['ancestors'] = []

    def add_ancestor(self, class_id, ancestor_id):
        """
        Adds new ancestor to class relations.
        :class_id: id of class where ancestor will be added to
        :ancestor_id: ancestor class id
        """
        if class_id not in self.classes:  # create new class item in dictionary
            self.add_class(class_id)
        # add ancestor class to list of ancestors
        self.classes[class_id]['ancestors'].append(ancestor_id)

    def add_successor(self, class_id, successor_id):
        """
        Adds new successor to class relations.
        :class_id: id of class where successor will be added to
        :successor_id: successor class id
        """
        if class_id not in self.classes:  # create new class item in dictionary
            self.add_class(class_id)
        # add successor class to list of successors
        self.classes[class_id]['successors'].append(successor_id)

    def clear_successors(self, class_id):
        """
        Removes all successors of the class.
        :class_id: id of class where successors will be removed
        """
        if class_id in self.classes:
            self.classes[class_id]['successors'] = []

    def clear_ancestors(self, class_id):
        """
        Removes all ancestors of the class.
        :class_id: id of class where ancestors will be removed
        """
        if class_id in self.classes:
            self.classes[class_id]['ancestors'] = []

    def remove_class(self, class_id):
        """
        Removes class from dictionary.
        :class_id: id of class to remove
        """
        if class_id in self.classes:
            self.classes.pop(class_id)

    def dump(self):
        """
        Writes class relations dictionary to json file.
        Doesn't do anything if file is not set.
        :raise IOError if fails to write to file
        """
        if self.dump_file:
            json.dump(self.classes, self.dump_file, indent=4, sort_keys=True)

    def load_dump(self, dump_file):
        """
        Loads class relations from dump file
        :param dump_file: dump_file descriptor
        :raise IOError if fails to read from file
        """
        self.classes = json.loads(dump_file.read())

    def get_path_to_class(self, current_class, closed_nodes):
        """
        Returns path from root class to current class (recursively)
        :param current_class: class for which path is returned
        :param closed_nodes: classes that are successors of current class, used for cyclic dependency check
        :raise NameError if class is not found
        :return: list of all paths to current class from root entity
        """

        # class data are not parsed / class is root class or have no ancestors
        if current_class not in self.classes or len(self.classes[current_class]['ancestors']) <= 0:
            return [current_class]
        # class is its successor with cyclic dependency to itself
        if current_class in closed_nodes:
            return [current_class]

        closed_nodes.append(current_class)  # append current class to closed

        all_paths = []  # all paths to this class
        for ancestor in self.classes[current_class]['ancestors']:
            paths_to_ancestor = self.get_path_to_class(ancestor, closed_nodes)  # get all paths to ancestor
            for path in paths_to_ancestor:  # append path to paths and add current class to end
                all_paths.append(path + '->' + current_class)

        closed_nodes.pop()  # pop current class from the list before return

        return all_paths

    def get_full_paths(self, entity_type):
        """
        Returns list of paths from root class to direct types of entity
        :param entity_type: type of entity (class that entity is instance of)
        :return: list of all paths from root class to direct types of entity sorted by classes in path
        """

        # list of paths
        paths = []

        # get all paths to each type
        for t in entity_type:
            paths.extend(self.get_path_to_class(t, []))

        # sort by path
        paths.sort()

        # remove duplicates
        if len(paths) > 1:
            i = 1
            while i < len(paths):
                if paths[i] == paths[i - 1]:
                    paths.pop(i)
                else:
                    i += 1

        return paths

    def get_parent_classes(self, current_class, depth, closed_nodes):
        """
        Returns current class and all parent classes on the path to the the root class
        Includes class depth for sorting
        :param current_class: class for which parent is returned
        :param depth: depth of current class
        :param closed_nodes: classes that are successors of current class and will not be expanded (detects cycles)
        :return: list of all parents of current class and their depth
        """

        classes = [[current_class, depth]]  # classes to return (with current class added)

        # class data are not parsed / class is root class or have no ancestors
        if current_class not in self.classes or len(self.classes[current_class]['ancestors']) <= 0:
            return classes
        # class is its successor with cyclic dependency to itself
        if current_class in closed_nodes:
            return classes

        closed_nodes.append(current_class)  # append current class to closed

        for ancestor in self.classes[current_class]['ancestors']:  # add all parents
            classes.extend(self.get_parent_classes(ancestor, depth + 1, closed_nodes))

        closed_nodes.pop()  # pop current class from the list before return

        return classes

    def get_all_parents(self, entity_type, remove_root_class, root_class):
        """
        Returns sorted list of classes according to how specific is the type represented by class
        to current entity
        :param entity_type: type of entity (class that entity is instance of)
        :param remove_root_class: if true, root class will be removed from list
        :param root_class: root class id
        :return: list of all types sorted according to how far is the type from entity (specificity)
        """

        # list of all types
        new_types = []

        # add all parents of direct types to new types
        for t in entity_type:
            new_types.extend(self.get_parent_classes(t, 0, []))

        # FORMAT:
        #  [ class_name , depth_number ]

        # sort according to the type name
        new_types.sort(key=lambda x: x[0])

        # NOTE:
        #  following constructions can't use for cycles
        #  because size of list can change during the iteration

        # remove root class from list
        if remove_root_class and root_class:
            i = 0
            while i < len(new_types):
                if new_types[i][0] == root_class:
                    new_types.pop(i)
                else:
                    i += 1

        # remove duplicates, keep only the those with lowes depth
        if len(new_types) >= 2:
            i = 1
            while i < len(new_types):
                if new_types[i][0] == new_types[i - 1][0]:
                    if new_types[i][1] > new_types[i - 1][1]:
                        new_types.pop(i)
                    else:
                        new_types.pop(i - 1)
                else:
                    i += 1

        # sort according to the depth (from highest to lowest)
        new_types.sort(key=lambda x: x[1])

        # remove depth numbers before return
        return [t[0] for t in new_types]

    def replace_types_of_entities(self, entities, full_path=False, remove_root_class=False, root_class=None):
        """
        Replaces type of each entity on given field number by complete path to entity class.
        :param entities: entities in array or file descriptor to file with entities
        :param full_path: defines if type will be paths to entity class from root class
                          or just list of all types and supertypes
        :param remove_root_class: if true, root class will be removed from list (used only if full_paths=False)
        :param root_class: root class id (used only if full_paths=False)
        """
        file = False
        for entity in entities:
            if type(entity) == str:  # if input is tsv file line, split it to list by tabs
                entity = entity[:-1]  # remove newline from end of the line
                entity = entity.split('\t')
                file = True
            types = entity[1].split('|')  # 1 == type of entity (see parser documentation)
            if full_path:
                types = self.get_full_paths(types)
            else:
                types = self.get_all_parents(types, remove_root_class, root_class)
            types = '|'.join(types)
            entity[1] = types
            if file:
                self.write_entity_to_tsv(entity, self.output_file)


def gen_temp_file(file_path, mode, tag=''):
    """
    Generates temporary file in folder given by path
    :param file_path: path to the file that will be appended before the name
    :param mode: mode how to open file (read/write/...), compatible with build-in open() command
                 makes sense only for modes that will create file, because it doesnt exists before opening
    :param tag: string that is added to the name before suffix - hash_tag.suffix
    :return: opened temp file handle
    """
    if not os.path.isdir(file_path):
        return None

    # generate unique file name
    file_name = hashlib.sha1(str(time.time()).encode()).hexdigest() + '_' + str(tag) + ".temp"
    while os.path.exists(os.path.join(file_path, file_name)):
        file_name = hashlib.sha1(str(time.time()).encode() + file_name.encode()).hexdigest() \
                    + '_' + str(tag) + ".temp"

    # return file handle
    return open(os.path.join(file_path, file_name), mode)


def parse_only(args):
    """
    Parse wikidata dump to tsv, do not substitute type and entity names
    :param args: arguments parsed by argparse
    :return: execution status
    """

    # open files
    class_relations_dump = None
    dict_file = None
    if args.class_relations_dump:
        try:
            class_relations_dump = open(args.class_relations_dump, 'w')
        except Exception:
            sys.stderr.write(SCRIPT_NAME + ": Failed to open class relations dump! Handled error: "
                             + str(traceback.format_exc()) + "\n")
            args.output_file.close()
            args.input_file.close()
            return 1
    if args.dict_file:
        try:
            dict_file = open(args.dict_file, 'w+')
        except Exception:
            sys.stderr.write(SCRIPT_NAME + ": Failed to open dict file! Handled error: "
                             + str(traceback.format_exc()) + "\n")
            args.output_file.close()
            args.input_file.close()
            if args.class_relations_dump:
                class_relations_dump.close()
            return 1

    relations_builder = ClassRelationsBuilder(dump_file=class_relations_dump)
    parser = WikidataDumpParser(input_file=args.input_file,
                                output_file=args.output_file,
                                dict_file=dict_file,
                                class_relations_builder=relations_builder)
    return_code = 0
    try:
        start_time = time.time()
        parser.parse_wikidump()  # parse wikidata dump to tsv and dictionary
        relations_builder.dump()  # dump entity relations to file
        end_time = time.time()

        print("Processed entities: " + str(parser.processed_records))
        print("Corrupted entities: " + str(parser.corrupted_records))
        print("Start: " + time.ctime(start_time))
        print("End: " + time.ctime(end_time))
        print("Total execution time: " + time.strftime("%H:%M:%S", time.gmtime(end_time - start_time)))
    except Exception:
        sys.stderr.write(SCRIPT_NAME + ": Failed to parse wikidata dump! Handled error:\n"
                         + str(traceback.format_exc()) + "\n")
        return_code = 1
    finally:
        args.output_file.close()
        args.input_file.close()
        if args.dict_file:
            dict_file.close()
        if args.class_relations_dump:
            class_relations_dump.close()
        return return_code


def substitute_names_only(args):
    """
    Substitutes names in already parsed dump
    :param args: arguments parsed by argparse
    :return: execution status
    """

    if not args.dict_file:
        sys.stderr.write("Dict file not set! Cannot substitute names!\n")
        return 2
    else:
        try:
            dict_file = open(args.dict_file, 'r')
        except Exception:
            sys.stderr.write(SCRIPT_NAME + ": Failed to open dictionary file! Handled error:\n"
                             + str(traceback.format_exc()) + "\n")
            args.output_file.close()
            args.input_file.close()
            return 1

    name_changer = WikidataNameInterchanger(input_file=args.input_file,
                                            dict_file=dict_file,
                                            output_file=args.output_file,
                                            show_missing=args.show_missing)
    return_code = 0
    try:
        start_time = time.time()
        name_changer.substitute_names()
        end_time = time.time()

        if args.show_missing:
            print("Number of entities without name: " + str(len(name_changer.ids_without_translation)))
            for entity_id in name_changer.ids_without_translation:
                sys.stdout.write(str(entity_id) + " ")
            sys.stdout.write("\n")
        print("Start: " + time.ctime(start_time))
        print("End: " + time.ctime(end_time))
        print("Total execution time: " + time.strftime("%H:%M:%S", time.gmtime(end_time - start_time)))
    except Exception:
        sys.stderr.write(SCRIPT_NAME + ": Failed to substitute ids for names! Handled error:\n"
                         + str(traceback.format_exc()) + "\n")
        return_code = 1
    finally:
        args.output_file.close()
        args.input_file.close()
        dict_file.close()
        return return_code


def substitute_type_only(args):
    """
    Substitutes types of entities in parsed dump without ids translated to names
    :param args: arguments parsed by argparse
    :return: execution status
    """

    if not args.class_relations_dump:
        sys.stderr.write("Relations dump not set! Cannot substitute types!\n")
        return 2
    else:
        try:
            class_relations_dump = open(args.class_relations_dump, 'r')
        except Exception:
            sys.stderr.write(SCRIPT_NAME + ": Failed to open dictionary file! Handled error:\n"
                             + str(traceback.format_exc()) + "\n")
            args.output_file.close()
            args.input_file.close()
            return 1

    relations_builder = ClassRelationsBuilder(output_file=args.output_file)

    return_code = 0
    try:
        relations_builder.load_dump(class_relations_dump)
        start_time = time.time()
        relations_builder.replace_types_of_entities(entities=args.input_file,
                                                    full_path=args.full_paths,
                                                    remove_root_class=not args.keep_root_class,
                                                    root_class=args.root_class_id)
        end_time = time.time()

        print("Start: " + time.ctime(start_time))
        print("End: " + time.ctime(end_time))
        print("Total execution time: " + time.strftime("%H:%M:%S", time.gmtime(end_time - start_time)))
    except Exception:
        sys.stderr.write(SCRIPT_NAME + ": Failed to substitute types of entities! Handled error:\n"
                         + str(traceback.format_exc()) + "\n")
        return_code = 1
    finally:
        args.input_file.close()
        args.output_file.close()
        return return_code


def complete_parsing(args):
    """
    Parses complete dump, substitutes type and names
    :param args: arguments parsed by argparse
    :return: execution status
    """

    # list of temp files
    temp_files = []

    # dictionary and class relations dump file
    class_relations_dump = None
    dict_file = None
    if args.class_relations_dump:
        try:
            class_relations_dump = open(args.class_relations_dump, 'w')
        except Exception:
            sys.stderr.write(SCRIPT_NAME + ": Failed to open class relations dump! Handled error:\n"
                             + str(traceback.format_exc()) + "\n")
            args.output_file.close()
            args.input_file.close()
            return 1
    if args.dict_file:
        try:
            dict_file = open(args.dict_file, 'w+')
        except Exception:
            sys.stderr.write(SCRIPT_NAME + ": Failed to open dict file! Handled error:\n"
                             + str(traceback.format_exc()) + "\n")
            args.output_file.close()
            args.input_file.close()
            if args.class_relations_dump:
                class_relations_dump.close()
            return 1

    # TODO
    #  add bigger buffers to files
    #  (about 8MB) - (default is 8kB)

    # class relations
    relations_builder = ClassRelationsBuilder()
    # add dump file
    if args.class_relations_dump:
        relations_builder.dump_file = class_relations_dump

    # dump parser
    parser = WikidataDumpParser(input_file=args.input_file,
                                class_relations_builder=relations_builder)
    # buffering
    if args.buffer_level > 0:
        parser.buffer_dictionary = True
    if args.buffer_level > 1:
        parser.buffer_entities = True
    else:  # file with dump
        parser.output_file = gen_temp_file(os.path.dirname(args.output_file.name), 'w+', 'output_file')
        temp_files.append(parser.output_file)
    # dictionary file
    if args.dict_file:
        parser.dict_file = dict_file
    elif args.buffer_level < 1:  # Dictionary buffering disabled
        parser.dict_file = gen_temp_file(os.path.dirname(args.output_file.name), 'w+', 'dict')
        temp_files.append(parser.dict_file)
    # number of parsed entities
    if args.number_of_entities:
        parser.max_entities = args.number_of_entities
    elif args.line:
        parser.line_number = args.line

    timestamp_parsing_start = time.time()
    try:
        parser.parse_wikidump()
    except Exception:
        sys.stderr.write(SCRIPT_NAME + ": Failed to parse wikidata dump! Handled error:\n"
                         + str(traceback.format_exc()) + "\n")

        # close output files
        args.output_file.close()
        if args.dict_file:
            dict_file.close()
        if args.class_relations_dump:
            class_relations_dump.close()

        # remove temp files
        if not args.no_cleanup:
            for file in temp_files:
                filename = file.name
                file.close()
                os.unlink(filename)

        return 1  # Return failure
    timestamp_parsed = time.time()

    # dump class relations to file
    if args.class_relations_dump:
        relations_builder.dump()
    # seek to beginning of each temp file
    for file in temp_files:
        file.seek(0)
    # set temp file for class relations output
    if args.buffer_level < 2:
        relations_builder.output_file = gen_temp_file(os.path.dirname(args.output_file.name),
                                                      'w+', 'class_relations_output')
        temp_files.append(relations_builder.output_file)

    # substitution of class types
    timestamp_types_substitution_start = time.time()
    try:
        relations_builder.replace_types_of_entities(parser.entities if args.buffer_level > 1 else parser.output_file,
                                                    args.full_paths, not args.keep_root_class, args.root_class_id)
    except Exception:
        sys.stderr.write(SCRIPT_NAME + ": Failed to substitute types of entities! Handled error:\n"
                         + str(traceback.format_exc()) + "\n")

        # close output files
        args.output_file.close()
        if args.dict_file:
            dict_file.close()
        if args.class_relations_dump:
            class_relations_dump.close()

        # remove temp files
        if not args.no_cleanup:
            for file in temp_files:
                filename = file.name
                file.close()
                os.unlink(filename)

        return 1  # return failure
    timestamp_types_substituted = time.time()
    # TODO
    #  add sorting according to the path to the entity

    # Name substitution
    name_changer = WikidataNameInterchanger(args.output_file, dump=parser.entities)
    # if dump is in tempfile not in memory, set input file descriptor
    if args.buffer_level < 2:
        name_changer.input_file = relations_builder.output_file if relations_builder.output_file else None
    # dictionary
    if args.buffer_level < 1:  # in file
        name_changer.dict_file = parser.dict_file
    else:  # in memory
        name_changer.dictionary = parser.dictionary
    # store info about failed translations
    if args.show_missing:
        name_changer.show_missing = True

    # seek to beginning of each temp file
    # - otherwise name substitution will read from end and exit immediately
    for file in temp_files:
        file.seek(0)
    # seek to the beginning of the dictionary file
    if args.dict_file:
        dict_file.seek(0)

    timestamp_names_substitution_start = time.time()
    try:
        name_changer.substitute_names()
    except ValueError:
        sys.stderr.write(SCRIPT_NAME + ": Failed to substitute ids for names! Handled error:\n"
                         + str(traceback.format_exc()) + "\n")

        # close output files
        args.output_file.close()
        if args.dict_file:
            dict_file.close()
        if args.class_relations_dump:
            class_relations_dump.close()

        # remove temp files
        if not args.no_cleanup:
            for file in temp_files:
                filename = file.name
                file.close()
                os.unlink(filename)

        return 3  # Failed to read from file
    timestamp_names_substituted = time.time()

    # cleanup and print info

    # close output files
    args.output_file.close()
    if args.dict_file:
        dict_file.close()
    if args.class_relations_dump:
        class_relations_dump.close()

    # remove temp files
    if not args.no_cleanup:
        for file in temp_files:
            filename = file.name
            file.close()
            os.unlink(filename)

    # entity info
    print("Processed entities: " + str(parser.processed_records))
    print("Corrupted entities: " + str(parser.corrupted_records))
    if args.show_missing:
        print("Number of entities without name: " + str(len(name_changer.ids_without_translation)))
        for entity_id in name_changer.ids_without_translation:
            sys.stdout.write(str(entity_id) + " ")
        sys.stdout.write("\n")
    # time info
    print("Start: " + time.ctime(timestamp_parsing_start))
    print("End: " + time.ctime(timestamp_names_substituted))
    # execution length
    print("Total execution time: " + time.strftime("%H:%M:%S", time.gmtime(
        timestamp_parsed - timestamp_parsing_start
        + timestamp_names_substituted - timestamp_names_substitution_start
        + timestamp_types_substituted - timestamp_types_substitution_start)))
    print("Parsing time: " + time.strftime("%H:%M:%S", time.gmtime(
        timestamp_parsed - timestamp_parsing_start)))
    print("Type substitution time: " + time.strftime("%H:%M:%S", time.gmtime(
        timestamp_types_substituted - timestamp_types_substitution_start)))
    print("Name substitution time: " + time.strftime("%H:%M:%S", time.gmtime(
        timestamp_names_substituted - timestamp_names_substitution_start)))
    if args.no_cleanup:
        print("Not removed temporary files:")
        for file in temp_files:
            print(file.name)

    return 0  # exit success


def main():
    """
    Main function, selects what will be done, according to the specified arguments
    :returns: execution status of the selected parsing plan
    """
    args = get_args()
    if args.parse_only:
        return parse_only(args)
    elif args.substitute_type_only:
        return substitute_type_only(args)
    elif args.substitute_names_only:
        return substitute_names_only(args)
    else:
        return complete_parsing(args)


# name guard for calling main function
if __name__ == "__main__":
    sys.exit(main())
