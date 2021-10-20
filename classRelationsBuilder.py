#!/usr/bin/env python3

# Author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# Project: wikidata2
# Description: Creates wikidata class relations and generates transitive closure and new type definitions.

import parseJson2  # for WikidataClassManipulator
import json
import os  # filesystem
import sys  # stdin, stderr
import argparse

# get script name
SCRIPT_NAME = os.path.basename(sys.argv[0])


def get_args():
    argparser = argparse.ArgumentParser(
        'Generates description of class relations and instance to class relations'
        ' and calculates transitive closures of those relations.'
    )
    argparser.add_argument(
        '-s', '--save-dump',
        help='Save class relations dump and instance relations dump to file after finish.',
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '-r', '--complete-relations',
        help='Check and add all missing class relations.',
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '--tsv',
        help='File where to save relations in tsv format as subclass-superclass relations.'
    )
    argparser.add_argument(
        '-t', '--superclass-tc',
        help='File where transitive closure of superclasses will be saved.'
    )
    argparser.add_argument(
        '-a', '--subclasses',
        help='File where list of subclasses will be saved.'
    )
    argparser.add_argument(
        '-c', '--class-relations-dump',
        help='Class relations dump file.'
    )
    argparser.add_argument(
        '-d', '--dump-directory',
        help='Directory with distributed class relations dump.'
    )
    argparser.add_argument(
        '-i', '--instance-relations-dump',
        help='File with relations of classes and instances.'
    )
    argparser.add_argument(
        '-f', '--instances-directory',
        help='Directory with distributed instance relations dump.'
    )
    argparser.add_argument(
        '-e', '--expanded-instances',
        help='File where expanded instances will be stored.'
    )
    argparser.add_argument(
        '-v', '--verbose',
        help='Print additional information about what is being done.',
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '-p', '--full-path',
        help='Generate full path to each class in tc, instead of just class name.',
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '-l', '--replace-types',
        help='File with entities where to replace type. Output file for entities must be set!'
             ' See \'--entities-output-file\' and \'--field-index\' options.'
    )
    argparser.add_argument(
        '-o', '--entities-output-file',
        help='File where entities with replaced type will be stored.'
    )
    argparser.add_argument(
        '-x', '--field-index',
        help='Index of type field in entity. (default=1)',
        type=int,
        default=1
    )
    return argparser.parse_args()


class ClassRelationsBuilder(parseJson2.WikidataDumpManipulator):
    """
    Builds class relation graph and replaces type of entities by class paths.
    """

    def __init__(self, classes=None, instances=None):
        """
        Initializes class dictionary
        :param classes: dictionary with existing class relations
        :param instances: dictionary with existing instance - class relations
        """
        self.classes = classes if classes else {}  # dictionary with class relations
        self.instances = instances if instances else {}  # dictionary with instance - class relations

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
        if ancestor_id not in self.classes[class_id]['ancestors']:
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
        if successor_id not in self.classes[class_id]['successors']:
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

    def add_instance(self, instance_id, class_ids):
        """
        Adds instance to relation.
        :param instance_id: id of instance entity
        :param class_ids: ids of classes of entity (multiple value field, or single class id)
        """
        ids = class_ids.split('|')
        for class_id in ids:
            if class_id not in self.instances:
                self.instances[class_id] = []
            if instance_id not in self.instances[class_id]:
                self.instances[class_id].append(instance_id)

    def remove_instance_class(self, class_id):
        """
        Removes class and all its instances.
        :param class_id: id of class to remove
        """
        if class_id in self.instances:
            self.instances.pop(class_id)

    def remove_instance(self, instance_id, class_id):
        """
        Removes instance from instance-class relations
        :param instance_id: id of instance to remove
        :param class_id: id of class instance is related to
        """
        if class_id in self.instances and instance_id in self.instances[class_id]:
            self.instances[class_id].remove(instance_id)

    def save_instances(self, dump_file):
        """
        Writes instance relations to json file.
        :param dump_file: file where instances will be written to
        :raise IOError if fails to write to file
        """
        json.dump(self.instances, dump_file, indent=4, sort_keys=True)

    def load_instances(self, dump_file):
        """
        Loads instances from dump file.
        :param dump_file: file with instance dump
        :raise IOError if fails to read from file
        """
        self.instances = json.loads(dump_file.read())

    def merge_instances(self, instances):
        """
        Merges instance relations given in argument to currently used instance relations
        :param instances: instances to merge
        """
        for class_id in instances:
            for instance_id in instances[class_id]:
                self.add_instance(instance_id, class_id)

    def save_dump(self, dump_file):
        """
        Writes class relations dictionary to json file.
        :param dump_file: file where dump will be written to
        :raise IOError if fails to write to file
        """
        json.dump(self.classes, dump_file, indent=4, sort_keys=True)

    def load_dump(self, dump_file):
        """
        Loads class relations from dump file
        :param dump_file: dump_file descriptor
        :raise IOError if fails to read from file
        """
        self.classes = json.loads(dump_file.read())

    def merge_class_relations(self, classes):
        """
        Merges class relations given in argument to currently used class relations
        :param classes: class relations to merge
        """
        for key in classes.keys():
            if key in self.classes:
                for class_id in classes[key]['ancestors']:
                    self.add_ancestor(key, class_id)
                for class_id in classes[key]['successors']:
                    self.add_successor(key, class_id)
            else:
                self.classes[key] = classes[key]

    def load_distributed_dump(self, dump_folder, instances=False):
        """
        Loads class relations from files in given folder
        :param dump_folder: path to folder where dump files are stored
        :param instances: tels if loaded data should be stored as instance relations or class relations
        :raise IOError if fails to read from file
        :raise OSError if directory can't be read
        """
        folder = os.scandir(dump_folder)
        for file in folder:
            if file.is_file():
                tmp_file = open(file.path, 'r')
                dump_part = json.load(tmp_file)
                tmp_file.close()
                if instances:
                    self.merge_instances(dump_part)
                else:
                    self.merge_class_relations(dump_part)

    def get_path_to_class(self, current_class, closed_nodes):
        """
        Returns path from root class to current class (recursively)
        :param current_class: class for which path is returned
        :param closed_nodes: classes that are successors of current class, used for cyclic dependency check
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

    def get_full_paths(self, classes):
        """
        Returns list of paths from root class to direct types of entity
        :param classes: list of classes for which tc with full paths will be generated
        :return: list of all paths from root class to direct types of entity sorted by classes in path
        """

        # list of paths
        paths = []

        # get all paths to each type
        for c in classes:
            paths.extend(self.get_path_to_class(c, []))

        # sort by path
        paths.sort()

        # remove duplicates
        if len(paths) > 1:
            i = 1
            while i < len(paths):
                if paths[i] == paths[i-1]:
                    paths.pop(i)
                else:
                    i += 1

        return paths

    def get_all_tcs(self, classes):
        """
        Generates transitive closures for all classes in list given in argument
        :param classes: list of classes for which tc will be generated
        :return list of all transitive closures of given classes
        """
        all_tcs = []
        for class_id in classes:
            try:
                tc = self.get_all_ancestors(class_id)
            except KeyError:  # class id is not listed in known class relations
                tc = []
            if class_id not in all_tcs:
                all_tcs.append(class_id)
            for cid in tc:
                if cid not in all_tcs:
                    all_tcs.append(cid)
        return all_tcs

    def replace_types_of_entities(self, entities, output_file=None, fi=1, full_path=False):
        """
        Replaces type of each entity on given field index by complete path to entity class.
        :param entities: entities in array or file descriptor to file with entities
        :param output_file: file, where to write processed entities
                            if not present, it is expected that parameter entities is of array type
        :param fi: field index of type
        :param full_path: defines if type will be paths to entity class from root class
                          or just list of all types and supertypes
        """
        if output_file is None and type(entities) != list:
            raise RuntimeError("If entities are read from file instead of list, output file must be set!")
        for entity in entities:
            if type(entity) == str:  # if input is tsv file line, split it to list by tabs
                entity = entity[:-1]  # remove newline from end of the line
                entity = entity.split('\t')
            if entity[fi]:  # process only if type field isn't empty
                types = entity[fi].split('|')  # fi == field with type of entity
                if full_path:
                    types = self.get_full_paths(types)
                else:
                    types = self.get_all_tcs(types)
                types = '|'.join(types)
                entity[fi] = types
            if output_file:
                self.write_entity_to_tsv(entity, output_file)

    def complete_relations(self):
        """
        Loops through all classes and adds missing successor and ancestor relations.
        """
        # create copy of the key list to prevent
        # RuntimeError: dictionary changed size during iteration
        for class_id in list(self.classes.keys()):
            # add this class as successor of all its ancestors
            for ancestor in self.classes[class_id]['ancestors']:
                self.add_successor(ancestor, class_id)
            # add this class as ancestor of all its successors
            for successor in self.classes[class_id]['successors']:
                self.add_ancestor(successor, class_id)

    def get_all_successors(self, class_id):
        """
        Generates list of all successors of the class.
        :param class_id: id of class for which successor list will be generated
        :raise KeyError if class_id isn't listed in relations in self.classes
        """
        successors = [class_id]  # add starting class id

        i = 0
        while i < len(successors):
            for subclass in self.classes[successors[i]]['successors']:
                if subclass not in successors:  # detect cyclic dependency
                    successors.append(subclass)
            i += 1

        successors.pop(0)  # remove class id from successor list

        return successors

    def get_all_ancestors(self, class_id):
        """
        Generates list of all ancestors of the class.
        :param class_id: id of class for which ancestor list will be generated
        :raise KeyError if class_id isn't listed in relations in self.classes
        """
        ancestors = [class_id]  # add starting class id

        i = 0
        while i < len(ancestors):
            for superclass in self.classes[ancestors[i]]['ancestors']:
                if superclass not in ancestors:
                    ancestors.append(superclass)
            i += 1

        ancestors.pop(0)  # remove class id from ancestor list

        return ancestors

    def get_superclass_tc(self, output_file):
        """
        Generates transitive closure of superclasses for each class.
        Fields are separated by tab, each line contains only one relation in format:
        subclass\tsuperclass\n
        :param output_file: output file
        """
        for class_id in self.classes:
            tc = self.get_all_ancestors(class_id)
            for record in tc:
                self.write_entity_to_tsv([class_id, record], output_file)

    def get_subclass_list(self, output_file):
        """
        Generates list of all subclasses for each class.
        Fields are separated by tab, each line contains only one relation in format:
        superclass\tsubclass\n
        :param output_file: output file
        """
        for class_id in self.classes:
            lst = self.get_all_successors(class_id)
            for record in lst:
                self.write_entity_to_tsv([class_id, record], output_file)

    def save_tsv(self, output_file):
        """
        Outputs class relations in format subclass-superclass to tsv file.
        :param output_file: tsv file where relations will be saved to
        """
        for class_id in self.classes:
            for ancestor in self.classes[class_id]['ancestors']:
                self.write_entity_to_tsv([class_id, ancestor], output_file)

    def expand_instances(self, output_file, full_path=False):
        """
        Expands instances type to transitive closure of its class.
        :param output_file: tsv file where expanded instances will be written
        :param full_path: tells if classes only or full paths to each class should be used
        """
        for class_id in self.instances:
            try:
                if full_path:
                    tc = self.get_full_paths([class_id])
                else:
                    tc = self.get_all_ancestors(class_id)
            except KeyError:
                tc = []  # class_id is not in relations (self.classes)!
            for instance_id in self.instances[class_id]:
                for cid in tc:
                    self.write_entity_to_tsv([instance_id, cid], output_file)
                self.write_entity_to_tsv([instance_id, class_id], output_file)


def main():
    args = get_args()

    # check dependent parameters
    if args.replace_types and not args.entities_output_file:
        sys.stderr.write("Output file for processed entities is not set!\n")
        sys.stderr.write("Use '--help' for more information about '--replace-types' option!\n")
        return 1

    if args.save_dump and not args.instance_relations_dump and not args.class_relations_dump:
        sys.stderr.write("'-s' option is set, but nothing to save!\n")
        sys.stderr.write("Use '--help' to see '-c' and '-i' options!")
        return 1

    # init
    error_code = 0  # error code to return
    crb = ClassRelationsBuilder()

    # load distributed dump
    if args.dump_directory:
        if args.verbose:
            print("Loading class dump from directory.")
        try:
            crb.load_distributed_dump(args.dump_directory)
        except IOError or OSError:
            sys.stderr.write("Cannot load class relations from given directory!\n")
            return 1

    # load dump from file
    if args.class_relations_dump:
        if not args.dump_directory:
            if args.verbose:
                print("Loading class dump from file.")
            try:
                file = open(args.class_relations_dump, 'r')
                crb.load_dump(file)
                file.close()
            except IOError:
                sys.stderr.write("Failed to read class relations dump file!\n")
                return 1

    # load distributed instance dump
    if args.instances_directory:
        if args.verbose:
            print("Loading instances from directory.")
        try:
            crb.load_distributed_dump(args.instances_directory, instances=True)
        except IOError or OSError:
            sys.stderr.write("Can't load instances from given directory!\n")
            return 1

    # load instance relations dump
    if args.instance_relations_dump:
        if not args.instances_directory:
            if args.verbose:
                print("Loading instances from file.")
            try:
                file = open(args.instance_relations_dump, 'r')
                crb.load_instances(file)
                file.close()
            except IOError:
                sys.stderr.write("Failed to read instance relations dump file!\n")
                return 1

    # check and add missing class relations
    if args.complete_relations:
        if args.verbose:
            print("Completing class relations.")
        # TODO check speed and optimize or use closure.py for superclass tc
        #      maybe simplify data model (too many memory jumps!)
        crb.complete_relations()

    # expand instances
    if args.expanded_instances:
        if args.verbose:
            print("Expanding instances and storing them to file.")
        try:
            output = open(args.expanded_instances, 'w')
            crb.expand_instances(output, args.full_path)
            output.close()
        except IOError:
            sys.stderr.write("Failed to write expanded instances to output!")
            error_code = 1

    # generate transitive closure
    if args.superclass_tc:
        if args.verbose:
            print("Generating transitive closure and storing in to file.")
        try:
            output = open(args.superclass_tc, 'w')
            crb.get_superclass_tc(output)
            output.close()
        except IOError:
            sys.stderr.write("Failed to generate tc tsv file!\n")
            error_code = 1

    # generate list of all subclasses
    # TODO
    #   This is not optimal - too many repetitive node passages
    #   Happens when:
    #   - multiple nodes have common successors
    #   - node is successor of another processed node
    #   Better approach - define list of top level nodes and expand only their successors, not all nodes in graph
    if args.subclasses:
        if args.verbose:
            print("Generating list of subclasses and storing it to file.")
        try:
            output = open(args.subclasses, 'w')
            crb.get_subclass_list(output)
            output.close()
        except IOError:
            sys.stderr.write("Failed to generate file with list of subclasses!\n")
            error_code = 1

    # replace types of entities with transitive closure
    if args.replace_types:
        if args.verbose:
            print("Replacing types of entities with tc.")
        try:
            output = open(args.entities_output_file, 'w')
            input_entities = open(args.replace_types, 'r')
            crb.replace_types_of_entities(input_entities, output, args.field_index, args.full_path)
            output.close()
            input_entities.close()
        except IOError:
            sys.stderr.write("Failed to replace types of entities!\n")
            error_code = 1
        except RuntimeError:
            sys.stderr.write("Internal runtime error!\nFailed to replace types of entities!\n")
            error_code = 1

    # save tsv
    if args.tsv:
        if args.verbose:
            print("Storing classes to tsv file.")
        try:
            output = open(args.tsv, 'w')
            crb.save_tsv(output)
            output.close()
        except IOError:
            sys.stderr.write("Failed to generate relations tsv file!\n")
            error_code = 1

    # save class relations to output file
    if args.save_dump:
        if args.class_relations_dump:
            if args.verbose:
                print("Saving class dump to file.")
            try:
                file = open(args.class_relations_dump, 'w')
                crb.save_dump(file)
                file.close()
            except IOError:
                sys.stderr.write("Failed to write class relations to file!\n")
                error_code = 1

        if args.instance_relations_dump:
            if args.verbose:
                print("Saving instances to file.")
            try:
                file = open(args.instance_relations_dump, 'w')
                crb.save_instances(file)
                file.close()
            except IOError:
                sys.stderr.write("Failed to write instance relations to file!\n")
                error_code = 1

    return error_code


if __name__ == '__main__':
    sys.exit(main())
