#!/usr/bin/env python3
# encoding UTF-8

# File: parseWikidataDump.py
# Author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# Project: wikidata2
# Description: Parses wikidata json dump to tsv.

import argparse
import json  # load data from dump
import os  # filesystem
import re  # find ids for substitution
import sys  # stderr, exit, ...
import traceback  # for printing exceptions

import classRelationsBuilder  # for ClassRelationsBuilder
import parseJson2  # for wikidata dump manipulator

# get script name
SCRIPT_NAME = os.path.basename(sys.argv[0])

try:
    for k in ["DIRNAME_CLASSES", "DIRNAME_DICTS", "DIRNAME_EXPANDED_INSTANCES", "DIRNAME_INSTANCES", "DIRNAME_LOCAL_PROCESSING", "DIRNAME_TYPES_DATA"]:
        os.environ[k]
except KeyError as x:
    from configobj import ConfigObj
    config = ConfigObj("env_variables.cfg")
    for k, v in config.items():
        os.environ[k] = v


def get_args():
    """
    Parses arguments from commandline.
    :return: parsed arguments
    """
    argparser = argparse.ArgumentParser(
        "Parses wikidata json dump to tsv files separated by type."
    )
    argparser.add_argument(
        "-f",
        "--input-file",
        help="Input file to process.",
        required=True,
        type=argparse.FileType("r"),
    )
    argparser.add_argument(
        "-t",
        "--output-files-tag",
        help="TSV output file tag, appended to all output file names.",
        required=True,
    )
    argparser.add_argument(
        "-p",
        "--output-folder-path",
        help="Path to folder where output files will be generated.",
        required=True,
    )
    argparser.add_argument(
        "--language",
        help="Language of output dictionary.",
        required=False,
        default="en",
    )
    argparser.add_argument(
        "-c",
        "--extract-class-relations",
        help="Extract class relations from dump.",
        required=False,
        default=False,
        action="store_true",
    )
    argparser.add_argument(
        "-e",
        "--parse-expanded-instances",
        help="Stores additional kb format where entity instance information is used as entity type.",
        required=False,
        default=False,
        action="store_true",
    )
    argparser.add_argument(
        "-q",
        "--quiet",
        help="Do not print statistics after parsing.",
        required=False,
        default=False,
        action="store_true",
    )
    parsing_restrictions_group = argparser.add_mutually_exclusive_group()
    parsing_restrictions_group.add_argument(
        "-n",
        "--number-of-entities",
        help="Parse only given number of entities.",
        required=False,
        type=int,
        default=None,
    )
    parsing_restrictions_group.add_argument(
        "-l",
        "--line",
        help="Parse only line with given number.",
        required=False,
        type=int,
        default=None,
    )
    return argparser.parse_args()


class SimpleWikidataDumpParser(parseJson2.WikidataDumpManipulator):
    """
    Parses wikidata dump to output files. Each entity is parsed to file by its type.
    Gives each entity type as defined by its 'instance of' field id.
    """

    """
    README:

    Adding new type to parser
        Add name of type and its definition (wikidata ids of this type) to self.types in init
        Add name of type and its prefix to self.type_prefix
        Add new method parse_nameoftype(self, record) to the parser class
        - method will be automatically called if entity with this type is detected
        - see extend_entity_data() method
    """

    def __init__(
        self,
        input_file,
        output_folder,
        output_files_tag,
        lang="en",
        number_of_entities=0,
        line=0,
        class_relations_builder=None,
        parse_expanded_instances=False,
    ):
        """
        Initializes parser.
        :param input_file: input file to parse
        :param output_folder: path to folder, where output files will be stored in
        :param output_files_tag: tag added to name of each output file
        :param lang: language of labels parsed to dictionary
        :param number_of_entities: number of entities to parse (0 = whole dump)
        :param line: line of dump to parse (dumps single line) (0 = whole dump)
        :param class_relations_builder: ClassRelationsBuilder instance for class relations processing
        :param parse_expanded_instances: Tells if expanded instance kb should be generated (True/False)
        """
        self.lang = lang
        self.default_lang = "en"  # language for name extraction if name for selected language is missing
        self.max_entities = number_of_entities
        self.dump_line = line
        # regexp for parsing dates
        self.date_regexp = re.compile(
            "^([+-].*)T"
        )  # +1732-02-22T00:00:00Z - match +1732-02-22
        # counters
        self.line_number = 1
        self.processed_records = 0
        self.corrupted_records = 0
        # class relations builder to save class relations to file
        self.class_relations_builder = class_relations_builder
        # parse expanded instances
        self.parse_expanded_instances = parse_expanded_instances
        # types definition:
        self.types = {
            "person": ["Q5", "Q15632617", "Q3658341"],
            "group": ["Q16334295"],
            "artist": [],
            "geographical": [
                "Q15617994",
                "Q6256",
                "Q3336843",
                "Q112099",
                "Q7275",
                "Q1048835",
                "Q3624078",
                "Q185145",
                "Q619610",
                "Q859563",
                "Q4209223",
                "Q133442",
                "Q1520223",
                "Q35657",
                "Q107390",
                "Q185441",
                "Q160016",
                "Q15634554",
                "Q5119",
                "Q515",
                "Q1549591",
                "Q200250",
                "Q3957",
                "Q532",
                "Q14757767",
                "Q15284",
                "Q23442",
                "Q123705",
                "Q34038",
                "Q23397",
                "Q165",
                "Q1973404",
                "Q8514",
                "Q8502",
                "Q192287",
                "Q387917",
                "Q50231",
            ],
            "event": [
                "Q100886746",
                "Q101965",
                "Q1057954",
                "Q1072326",
                "Q10737",
                "Q1076105",
                "Q1079023",
                "Q10931",
                "Q11376059",
                "Q11483816",
                "Q114953",
                "Q11499267",
                "Q1150070",
                "Q1150958",
                "Q11514315",
                "Q11538952",
                "Q1156895",
                "Q1174599",
                "Q11783626",
                "Q11890047",
                "Q1190554",
                "Q1194317",
                "Q1199515",
                "Q124490",
                "Q124734",
                "Q12786121",
                "Q12897867",
                "Q1301203",
                "Q131288",
                "Q1318941",
                "Q1322005",
                "Q132241",
                "Q132821",
                "Q13357840",
                "Q13357858",
                "Q1344963",
                "Q135010",
                "Q13537604",
                "Q1375427",
                "Q14006248",
                "Q141022",
                "Q14208553",
                "Q1445650",
                "Q1456832",
                "Q1478437",
                "Q149086",
                "Q14914657",
                "Q15078788",
                "Q15091377",
                "Q15116915",
                "Q1520311",
                "Q152450",
                "Q15275719",
                "Q1572106",
                "Q15966540",
                "Q15974353",
                "Q16147386",
                "Q16466010",
                "Q16510064",
                "Q16513426",
                "Q1656682",
                "Q16622264",
                "Q16684585",
                "Q167170",
                "Q168983",
                "Q169950",
                "Q170774",
                "Q171558",
                "Q17195514",
                "Q17299750",
                "Q17317604",
                "Q17522177",
                "Q175331",
                "Q1763090",
                "Q1769698",
                "Q1772449",
                "Q177626",
                "Q17781833",
                "Q178131",
                "Q178561",
                "Q178651",
                "Q179057",
                "Q1800545",
                "Q1800556",
                "Q18033462",
                "Q180684",
                "Q1825417",
                "Q182832",
                "Q18325242",
                "Q184940",
                "Q18608583",
                "Q186361",
                "Q18669875",
                "Q187668",
                "Q18769744",
                "Q189760",
                "Q189819",
                "Q1914636",
                "Q191797",
                "Q192909",
                "Q1967459",
                "Q1975478",
                "Q198",
                "Q2001676",
                "Q200538",
                "Q20107484",
                "Q201676",
                "Q2020153",
                "Q2041929",
                "Q21143058",
                "Q21156425",
                "Q21163366",
                "Q21224061",
                "Q21246076",
                "Q2135540",
                "Q21368803",
                "Q21550582",
                "Q2210277",
                "Q2223653",
                "Q22275878",
                "Q2252077",
                "Q2259749",
                "Q22938576",
                "Q2303329",
                "Q2334719",
                "Q2380335",
                "Q23807345",
                "Q2401485",
                "Q24050099",
                "Q2495862",
                "Q24962887",
                "Q252000",
                "Q25379",
                "Q2540467",
                "Q25481968",
                "Q2571535",
                "Q26132862",
                "Q2620826",
                "Q2627975",
                "Q2648795",
                "Q2656967",
                "Q2672648",
                "Q26836193",
                "Q26861438",
                "Q26863790",
                "Q27020041",
                "Q2727213",
                "Q273120",
                "Q2761147",
                "Q279283",
                "Q280783",
                "Q28100974",
                "Q28813",
                "Q2881374",
                "Q28924760",
                "Q28972820",
                "Q29023906",
                "Q2912397",
                "Q29142",
                "Q29182544",
                "Q2956046",
                "Q3001412",
                "Q3002617",
                "Q301585",
                "Q3030248",
                "Q3109572",
                "Q31645",
                "Q3241045",
                "Q3242199",
                "Q3270632",
                "Q327742",
                "Q327765",
                "Q34548322",
                "Q34548368",
                "Q3454956",
                "Q3510594",
                "Q35140",
                "Q357104",
                "Q3587397",
                "Q3604747",
                "Q36963",
                "Q36993249",
                "Q375011",
                "Q3769186",
                "Q37937330",
                "Q381072",
                "Q3839081",
                "Q3882220",
                "Q3887",
                "Q4",
                "Q40231",
                "Q40244",
                "Q4026292",
                "Q4071928",
                "Q422695",
                "Q43414",
                "Q44512",
                "Q44637051",
                "Q4494907",
                "Q4504495",
                "Q451967",
                "Q4582333",
                "Q4618",
                "Q464980",
                "Q47092",
                "Q47217",
                "Q48004378",
                "Q4801521",
                "Q4817637",
                "Q483247",
                "Q4867756",
                "Q493386",
                "Q500834",
                "Q5070802",
                "Q50843134",
                "Q51031626",
                "Q5124704",
                "Q51404",
                "Q52260246",
                "Q52943",
                "Q5354663",
                "Q53706",
                "Q5386",
                "Q5393774",
                "Q56316064",
                "Q56321344",
                "Q573",
                "Q5801919",
                "Q580750",
                "Q5916",
                "Q602884",
                "Q60971579",
                "Q6160",
                "Q61628047",
                "Q6163243",
                "Q61788060",
                "Q625994",
                "Q628455",
                "Q63860191",
                "Q64250307",
                "Q64348974",
                "Q64569595",
                "Q645883",
                "Q646740",
                "Q64732777",
                "Q64918845",
                "Q650711",
                "Q6508605",
                "Q65742449",
                "Q657449",
                "Q667276",
                "Q673281",
                "Q6765918",
                "Q678146",
                "Q6823473",
                "Q686984",
                "Q6942562",
                "Q71266556",
                "Q7157572",
                "Q7283",
                "Q744913",
                "Q74948922",
                "Q75951701",
                "Q8016240",
                "Q8092",
                "Q81054",
                "Q815962",
                "Q82821",
                "Q837556",
                "Q841236",
                "Q841654",
                "Q844482",
                "Q8445",
                "Q8454",
                "Q851824",
                "Q858439",
                "Q861911",
                "Q864897",
                "Q868557",
                "Q872181",
                "Q87267404",
                "Q87267425",
                "Q87267436",
                "Q87267444",
                "Q87267448",
                "Q87268198",
                "Q878123",
                "Q917206",
                "Q918346",
                "Q93288",
                "Q96246183",
                "Q969079",
            ],
            "organization": [
                "Q1007311",
                "Q102121698",
                "Q1021290",
                "Q102356",
                "Q102538",
                "Q10358588",
                "Q104649845",
                "Q1080794",
                "Q11072804",
                "Q1109105",
                "Q1110684",
                "Q1137608",
                "Q1156831",
                "Q11635",
                "Q11707",
                "Q11771944",
                "Q11775750",
                "Q11799049",
                "Q1194951",
                "Q1194970",
                "Q12359039",
                "Q1248784",
                "Q124964",
                "Q1252971",
                "Q1254933",
                "Q1295201",
                "Q12973014",
                "Q131596",
                "Q131734",
                "Q132510",
                "Q1329623",
                "Q1331793",
                "Q133311",
                "Q1341387",
                "Q13414953",
                "Q134161",
                "Q13473501",
                "Q138796",
                "Q1391145",
                "Q1412224",
                "Q1416431",
                "Q1416636",
                "Q1426710",
                "Q14350",
                "Q1438040",
                "Q1451906",
                "Q14755054",
                "Q1477115",
                "Q14825551",
                "Q14869273",
                "Q149566",
                "Q1497649",
                "Q15091621",
                "Q15265344",
                "Q1530022",
                "Q15343039",
                "Q153936",
                "Q15627509",
                "Q157031",
                "Q1572070",
                "Q15734684",
                "Q1589009",
                "Q15911314",
                "Q15911738",
                "Q159334",
                "Q15944511",
                "Q162633",
                "Q163323",
                "Q163740",
                "Q16463",
                "Q16547029",
                "Q165758",
                "Q166118",
                "Q166280",
                "Q1664720",
                "Q167037",
                "Q16710795",
                "Q167346",
                "Q16735822",
                "Q1685451",
                "Q16873390",
                "Q16917",
                "Q169534",
                "Q17149090",
                "Q17270000",
                "Q1729207",
                "Q17456916",
                "Q1752346",
                "Q1762621",
                "Q176799",
                "Q1774898",
                "Q177634",
                "Q1785271",
                "Q178706",
                "Q178790",
                "Q1788992",
                "Q179076",
                "Q1792623",
                "Q17990971",
                "Q1802419",
                "Q180846",
                "Q180958",
                "Q18587469",
                "Q18624259",
                "Q187456",
                "Q1880737",
                "Q18810687",
                "Q188497",
                "Q189004",
                "Q192350",
                "Q1935049",
                "Q19358292",
                "Q194166",
                "Q1971849",
                "Q200023",
                "Q2003221",
                "Q200764",
                "Q2008856",
                "Q2061186",
                "Q20639856",
                "Q207320",
                "Q207694",
                "Q20820271",
                "Q20853538",
                "Q2085381",
                "Q20897549",
                "Q21073937",
                "Q210980",
                "Q211503",
                "Q212805",
                "Q213441",
                "Q2143354",
                "Q2169973",
                "Q21945604",
                "Q21980538",
                "Q22687",
                "Q22713629",
                "Q22950320",
                "Q23002037",
                "Q23002042",
                "Q23004361",
                "Q23005184",
                "Q23005223",
                "Q234497",
                "Q2366457",
                "Q2368252",
                "Q2373919",
                "Q2385804",
                "Q23905052",
                "Q2398990",
                "Q2401749",
                "Q24038970",
                "Q24354",
                "Q245065",
                "Q2485448",
                "Q249556",
                "Q2516357",
                "Q25510280",
                "Q256020",
                "Q2659904",
                "Q2663712",
                "Q27031009",
                "Q27032392",
                "Q27038993",
                "Q270791",
                "Q27116296",
                "Q2717262",
                "Q2738074",
                "Q2742167",
                "Q27686",
                "Q27728524",
                "Q28070878",
                "Q28083137",
                "Q2824642",
                "Q28564",
                "Q285852",
                "Q28599747",
                "Q2865305",
                "Q28737012",
                "Q288514",
                "Q29171",
                "Q294163",
                "Q2986700",
                "Q30022",
                "Q30313989",
                "Q3062125",
                "Q3152824",
                "Q3153117",
                "Q3154693",
                "Q31728",
                "Q31855",
                "Q32178211",
                "Q322563",
                "Q3244038",
                "Q327245",
                "Q327333",
                "Q33134112",
                "Q334453",
                "Q33506",
                "Q33685",
                "Q34651",
                "Q346575",
                "Q35535",
                "Q3726309",
                "Q3750285",
                "Q3754526",
                "Q37726",
                "Q3788231",
                "Q380342",
                "Q385994",
                "Q38723",
                "Q3874020",
                "Q3907564",
                "Q391009",
                "Q3914",
                "Q3917681",
                "Q3918",
                "Q4005763",
                "Q4005772",
                "Q40357",
                "Q41298",
                "Q41487",
                "Q41726",
                "Q417633",
                "Q423208",
                "Q4287745",
                "Q42998",
                "Q431603",
                "Q43229",
                "Q43501",
                "Q4358176",
                "Q4430243",
                "Q4438121",
                "Q4508",
                "Q45103187",
                "Q4539",
                "Q46398483",
                "Q4671277",
                "Q47272186",
                "Q47315",
                "Q477544",
                "Q48204",
                "Q4830453",
                "Q483242",
                "Q484652",
                "Q48748864",
                "Q4931391",
                "Q494230",
                "Q4959031",
                "Q507619",
                "Q51041800",
                "Q5135744",
                "Q5155040",
                "Q52252814",
                "Q52371",
                "Q5260792",
                "Q5283295",
                "Q5307737",
                "Q5341295",
                "Q536390",
                "Q55043",
                "Q55071047",
                "Q55097243",
                "Q55645123",
                "Q55657615",
                "Q5588651",
                "Q5589178",
                "Q5621421",
                "Q567521",
                "Q56876011",
                "Q57305",
                "Q57775519",
                "Q588140",
                "Q59055358",
                "Q59515313",
                "Q60170135",
                "Q6138528",
                "Q61740358",
                "Q623109",
                "Q62602544",
                "Q62832",
                "Q63046123",
                "Q63074246",
                "Q6498663",
                "Q6501447",
                "Q650241",
                "Q654772",
                "Q65553774",
                "Q665565",
                "Q6663997",
                "Q66736191",
                "Q679165",
                "Q681615",
                "Q68773434",
                "Q6881511",
                "Q688829",
                "Q6979593",
                "Q699386",
                "Q701632",
                "Q7075",
                "Q708676",
                "Q7188",
                "Q7210356",
                "Q7248094",
                "Q7257872",
                "Q726870",
                "Q7278",
                "Q730038",
                "Q7311343",
                "Q7315155",
                "Q732717",
                "Q734253",
                "Q73768821",
                "Q748019",
                "Q7574898",
                "Q7604698",
                "Q77115",
                "Q783794",
                "Q79913",
                "Q8031011",
                "Q814610",
                "Q83405",
                "Q847017",
                "Q848197",
                "Q861455",
                "Q875538",
                "Q88985865",
                "Q897403",
                "Q90049510",
                "Q9261468",
                "Q9305769",
                "Q93479232",
                "Q938236",
                "Q9392615",
                "Q939616",
                "Q94670589",
                "Q955824",
                "Q9592",
                "Q971045",
                "Q9822982",
                "Q9826",
                "Q9842",
                "Q988108",
                "Q98895450",
                "Q992253",
                "Q99536263",
                "Q996839",
            ],
            "person+artist": [],
        }
        # prefix for id of each type
        self.type_prefix = {
            "person": "p:",
            "group": "g:",
            "artist": "a:",
            "person+artist": "a:",
            "geographical": "l:",
            "event": "e:",
            "organization": "o:",
            "general": "x:",  # this is used when entity doesn't belong to any other type
        }
        # input file
        self.input_file = input_file
        # output files bindings
        self.output_files = {}
        # dictionary output file
        self.dict_file = None
        # class relations output file
        self.class_relations_file = None
        # instance - class relations output file
        self.instance_relations_file = None
        # expanded instances output file
        self.expanded_instances_output_file = None
        # call function for opening output files
        self.open_output_files(output_folder, output_files_tag)

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

    def open_output_files(self, output_folder, output_files_tag):
        """
        Opens output files for each type that have defined prefix in self.type_prefix
        File descriptors are stored in self.output_files, under name of type file belongs to
        :param output_folder: path to folder, where files will be generated
        :param output_files_tag: tag added to name of each file
        :raise IOError if fails to open output file
        """
        if output_folder[-1] == "/" or not os.path.isdir(output_folder):
            output_folder = os.path.dirname(output_folder)
        output_files_tag = "_" + output_files_tag if output_files_tag else ""

        # open output files for each type
        for type_name in self.type_prefix.keys():
            self.output_files[type_name] = open(
                f'{output_folder}/{os.environ["DIRNAME_TYPES_DATA"]}/{type_name}{output_files_tag}.tsv',
                "w",
            )  # mode
        # open dictionary file
        fpath_dict = f'{output_folder}/{os.environ["DIRNAME_DICTS"]}/dict{output_files_tag}.tsv'
        os.makedirs(os.path.dirname(fpath_dict), exist_ok=True)
        self.dict_file = open(fpath_dict, "w")
        # open expanded instances output file
        if self.parse_expanded_instances:
            fpath_expanded_instance = f'{output_folder}/{os.environ["DIRNAME_EXPANDED_INSTANCES"]}/expanded_instances{output_files_tag}.tsv'
            os.makedirs(os.path.dirname(fpath_expanded_instance), exist_ok=True)
            self.expanded_instances_output_file = open(
                fpath_expanded_instance,
                "w",
            )
        # open class relations builder output files
        if self.class_relations_builder:
            fpath_class = f'{output_folder}/{os.environ["DIRNAME_CLASSES"]}/classes{output_files_tag}.json'
            os.makedirs(os.path.dirname(fpath_class), exist_ok=True)
            self.class_relations_file = open(fpath_class, "w")
            fpath_instance = (
                f'{output_folder}/{os.environ["DIRNAME_INSTANCES"]}/instances{output_files_tag}.json'
            )
            os.makedirs(os.path.dirname(fpath_instance), exist_ok=True)
            self.instance_relations_file = open(fpath_instance, "w")

    def close_output_files(self):
        """
        Closes output files opened by self.open_output_files() method
        """
        for f in self.output_files.values():
            f.close()
        self.dict_file.close()
        if self.parse_expanded_instances:
            self.expanded_instances_output_file.close()
        if self.class_relations_builder:  # save buffers and close output
            self.class_relations_builder.save_dump(self.class_relations_file)
            self.class_relations_builder.save_instances(self.instance_relations_file)
            self.class_relations_file.close()
            self.instance_relations_file.close()

    def parse_name(self, label_field):
        """
        Extracts name/label from given field.
        If name for specified language is not available, then selects most common value.
        :param label_field: name / label field from parsed entity (entity['labels'])
        :return: entity name
        """

        # return label for selected language
        if self.lang in label_field:
            return label_field[self.lang]["value"]

        # return label for default language if label for selected language is missing
        if self.default_lang in label_field:
            return (
                label_field[self.default_lang]["value"] + "#lang=" + self.default_lang
            )

        return ""

    def parse_record(self, record):
        """
        Parses one json record from wikidata dump file
        :param record: record converted to dict
        :return: parsed entity
        """

        """
        Parsed data:
        0 ID
        1 INSTANCE OF (MULTIPLE VALUES) (TYPE of entity)
        2 NAME / LABEL
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
        entity = ["", "", "", "", "", "", "", "", "", "", "", ""]

        # 0 id
        if "id" in record:
            entity[0] = record["id"]
            if not entity[0]:  # sometimes id is empty
                return None
        else:  # fail if identifier is missing
            return None

        # 1 instance of (type)
        if "claims" in record:
            if "P31" in record["claims"]:  # P31 == instance of
                for statement in record["claims"]["P31"]:
                    try:
                        if (
                            statement["mainsnak"]["datavalue"]["value"]["entity-type"]
                            == "item"
                        ):
                            entity[1] = self.gen_multival_field(
                                entity[1],
                                statement["mainsnak"]["datavalue"]["value"]["id"],
                            )
                    except KeyError:
                        # no such value in the current statement - skip
                        pass
            # 11 images
            if "P18" in record["claims"]:  # P18 == image
                for picture in record["claims"]["P18"]:
                    try:
                        # commonsMedia = name of media file
                        if (
                            picture["mainsnak"]["datavalue"]["datatype"]
                            == "commonsMedia"
                        ):
                            entity[11] = self.gen_multival_field(
                                entity[11], picture["mainsnak"]["datavalue"]["value"]
                            )
                    except KeyError:
                        # can't extract image name - value not present - skip
                        pass
            # add relation to relations builder
            if "P279" in record["claims"]:  # P279 == subclass of
                for statement in record["claims"]["P279"]:
                    try:
                        # subclass of
                        if (
                            statement["mainsnak"]["datavalue"]["value"]["entity-type"]
                            == "item"
                        ):
                            if self.class_relations_builder:
                                self.class_relations_builder.add_ancestor(
                                    record["id"],  # entity id
                                    statement["mainsnak"]["datavalue"]["value"]["id"],
                                )  # id of related entity
                    except KeyError:
                        # can't extract related class - value is not present - skip
                        pass

        # add instance to relation builder
        if entity[1]:
            self.class_relations_builder.add_instance(entity[0], entity[1])

        # 2 name / label
        if "labels" in record:
            entity[2] = self.parse_name(record["labels"])

        # 3 disambiguation name - not parsed - no suitable attribute found

        # 4 aliases
        if "aliases" in record and self.lang in record["aliases"]:
            for value in record["aliases"][self.lang]:
                entity[4] = self.gen_multival_field(entity[4], value["value"])

        # 5 description
        if "descriptions" in record and self.lang in record["descriptions"]:
            entity[5] = record["descriptions"][self.lang]["value"]

        # 6 roles - not parsed - no suitable attribute found

        # 7 fictional - can't be determined from parsed data
        #             - this have to be determined according to class relations

        # 8 wikipedia url
        if "sitelinks" in record and self.lang + "wiki" in record["sitelinks"]:
            try:
                entity[8] = (
                    "https://"
                    + self.lang
                    + ".wikipedia.org/wiki/"
                    + "_".join(record["sitelinks"][self.lang + "wiki"]["title"].split())
                )
            except KeyError:  # title not found, record is corrupted
                entity[8] = ""

        # 9 wikidata url
        entity[9] = "https://www.wikidata.org/wiki/" + entity[0]

        # 10 dbpedia url - not parsed - no suitable attribute found

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

            if (
                len(line) > 2
            ):  # first and last lines will be empty (contains only bracket removed by line = line[:-1])
                if line[-2] == ",":
                    line = line[:-2]  # remove comma and newline
                else:
                    line = line[
                        :-1
                    ]  # last record doesn't have comma, remove only newline
                try:
                    record = json.loads(line)  # convert to dictionary
                except json.JSONDecodeError:
                    self.corrupted_records += 1
                else:
                    # parse common data for all entities
                    entity = self.parse_record(record)
                    if entity is None:  # drop entity if id is missing
                        self.corrupted_records += 1
                    elif not entity[2]:  # drop entities without names
                        self.corrupted_records += 1
                    else:
                        # generate dictionary file to replace IDs for names
                        # written fields: entity[0] == id, entity[2] == name / label
                        # add entity to dictionary
                        self.write_entity_to_tsv([entity[0], entity[2]], self.dict_file)

                        # write entity to expanded instances kb
                        if self.parse_expanded_instances:
                            self.write_entity_to_tsv(
                                entity, self.expanded_instances_output_file
                            )

                        # modify entity type to output format
                        entity = self.modify_type(entity)

                        # extend entity with type specific information
                        entity = self.extend_entity_data(entity, record)

                        # write entity to output file according to the type
                        self.write_entity_to_tsv(entity, self.output_files[entity[1]])

                        self.processed_records += 1

            # if dumping single line, break cycle after done
            if self.dump_line:
                break

            # maximum number of entities reached
            elif self.max_entities and self.max_entities <= self.processed_records:
                break

            self.line_number += 1

        return 0

    def extend_entity_data(self, entity, record):
        """
        Extends entity by adding type specific information.
        :param entity: entity to extend
        :param record: record where to take additional data
        :return: extended entity matching specific type
        """

        type = entity[1].replace("+", "_")  # remove + from compound entities
        # select method to parse additional data according to the entity type
        if "parse_" + type in dir(self):
            # add data to the end of the entity
            # for example, type 'geographical' getattr will expand to self.parse_geographical(record)
            entity = entity + getattr(self, "parse_" + type)(record)

        return entity

    def modify_type(self, entity):
        """
        Selects entity type and modifies entity to match output format.
        :param entity: general entity to modify
        :return: entity extended by specific fields
        """

        # get type
        entity[1] = self.get_entity_type(entity[1].split("|"))

        # add type letter to id (according to the type received above)
        entity[0] = self.type_prefix[entity[1]] + entity[0]

        return entity

    def get_entity_type(self, entity_type):
        """
        Returns type of entity based on criteria in self.types (see __init__).
        :param entity_type: list of entity types parsed from dump
        :return: name of type defined in types dictionary
        """
        for type_name in self.types.keys():  # names of types
            for entity_id in entity_type:  # list of data in entity type field
                if (
                    entity_id in self.types[type_name]
                ):  # check match in entity type field and type definition
                    if type_name == "person":  # check for person+artist type
                        for entity_id2 in entity_type:
                            if entity_id2 in self.types["artist"]:
                                return "person+artist"
                    return type_name  # return first matching type name
        return "general"  # nothing else fits

    def get_most_recent_value(self, field, data_field_name):
        """
        Returns most recent value from multiple value claims filed
        (suitable for extraction of populations of countries, etc.)
        :param field: claims field with data to parse
        :param data_field_name: name of datafield in json (last field of path to data)
        :return: most recent value from given filed
        """

        result = ""
        date = None

        # parse init value (also used if there are no date fields)
        try:
            result = field[0]["mainsnak"]["datavalue"]["value"][data_field_name]
        except KeyError:
            # value not present
            pass

        # exit if there are no other values
        if len(field) < 2:
            return result

        # parse date
        try:
            date = self.date_regexp.search(
                field[0]["qualifiers"]["P585"][0]["datavalue"]["value"]["time"]
            ).group(1)
        except (KeyError, AttributeError):
            # value not present or regexp doesn't match date
            pass

        for claim in field:
            # check other values
            if "qualifiers" in claim and "P585" in claim["qualifiers"]:
                try:
                    current_date = self.date_regexp.search(
                        claim["qualifiers"]["P585"][0]["datavalue"]["value"]["time"]
                    ).group(1)
                except (KeyError, AttributeError):
                    # value not present or regexp doesn't match date
                    pass
                else:  # if success, compare date and parse new data
                    try:
                        # check date (first letter == +|- where ord('-') > ord('+')
                        if (
                            not date
                            or (
                                current_date[0] == date[0]
                                and current_date[1:] > date[1:]
                            )
                            or current_date[0] < date[0]
                        ):
                            result = claim["mainsnak"]["datavalue"]["value"][
                                data_field_name
                            ]
                            date = current_date
                    except KeyError:
                        # value not present
                        pass

        return result

    def parse_person(self, record):
        """
        Parses person specific data.
        :param record: wikidata json record converted to dict
        :return: list of person claims
        """
        """
        Parsed data:
        0 GENDER
        1 DATE OF BIRTH
        2 PLACE OF BIRTH
        3 DATE OF DEATH
        4 PLACE OF DEATH
        5 COUNTRIES OF CITIZENSHIP (MULTIPLE VALUES)
        """
        data = ["", "", "", "", "", ""]

        if "claims" in record:
            claims = record["claims"]  # bind claims to variable
            # 0 Gender
            if "P21" in claims:
                try:
                    data[0] = claims["P21"][0]["mainsnak"]["datavalue"]["value"]["id"]
                except KeyError:
                    # can't extract value - skip
                    pass
            # 1 Date of birth
            if "P569" in claims:
                try:
                    data[1] = self.date_regexp.search(
                        claims["P569"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    ).group(1)
                except AttributeError:
                    # Regexp matches no data
                    pass
                except KeyError:
                    # Date field is not present
                    pass
            # 2 Place of birth
            if "P19" in claims:
                try:
                    data[2] = claims["P19"][0]["mainsnak"]["datavalue"]["value"]["id"]
                except KeyError:
                    # value not present
                    pass
            # 3 Date of death
            if "P570" in claims:
                try:
                    data[3] = self.date_regexp.search(
                        claims["P570"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    ).group(1)
                except AttributeError:
                    # Regexp matches no data
                    pass
                except KeyError:
                    # Date field is not present
                    pass
            # 4 Place of death
            if "P20" in claims:
                try:
                    data[4] = claims["P20"][0]["mainsnak"]["datavalue"]["value"]["id"]
                except KeyError:
                    # Value not present
                    pass
            # 5 Countries Of Citizenship
            if "P27" in claims:
                for claim in claims["P27"]:
                    try:
                        data[5] = self.gen_multival_field(
                            data[5], claim["mainsnak"]["datavalue"]["value"]["id"]
                        )
                    except KeyError:
                        # Value not present
                        pass

        # return parsed data
        return data

    def parse_group(self, record):
        """
        Parses group of people specific data.

        Important note!
        Values other than Individual names are not parsed because
        there are no suitable fields to obtain these information.
        All information have to be supplied in postprocessing from
        parsed personal entities. All personal entity ids are stored
        in field 0 - Individual names (those are ids, until substituted
        to names in id substitution phase). This obviously can't run
        distributed on multiple computers because all data have to be
        available to find these entities.

        :param record: wikidata json record converted to dict
        :return: list of group of people claims
        """
        """
        0 INDIVIDUAL NAMES (MULTIPLE VALUES)
        1 GENDERS (MULTIPLE VALUES)
        2 DATES OF BIRTH (MULTIPLE VALUES)
        3 PLACES OF BIRTH (MULTIPLE VALUES)
        4 DATES OF DEATH (MULTIPLE VALUES)
        5 PLACES OF DEATH (MULTIPLE VALUES)
        6 NATIONALITIES (MULTIPLE VALUES)
        """
        data = ["", "", "", "", "", "", ""]

        if "claims" in record:
            claims = record["claims"]  # bind claims to variable

            # 0 Individual names (has part)
            if "P527" in claims:
                for claim in claims["P527"]:
                    try:
                        data[0] = self.gen_multival_field(
                            data[0], claim["mainsnak"]["datavalue"]["value"]["id"]
                        )
                    except KeyError:
                        # value is missing
                        pass

            # Other values are not parsed - see note in function description!

        return data

    def ___temp_disabled_parse_artist(self, record):
        """
        Parses artist specific data.
        :param record: wikidata json record converted to dict
        :return: list of artist data
        """
        """
        0 ART FORMS (MULTIPLE VALUES)
        1 INFLUENCERS (MULTIPLE VALUES)
        2 INFLUENCEES (MULTIPLE VALUES)
        3 ULAN ID
        4 OTHER URLS (MULTIPLE VALUES)
        """
        data = ["", "", "", "", ""]

        if "claims" in record:
            claims = record["claims"]  # bind claims to variable

            # 0 Art Forms (occupation)
            if "P106" in claims:
                for claim in claims["P106"]:
                    try:
                        data[0] = self.gen_multival_field(
                            data[0], claim["mainsnak"]["datavalue"]["value"]["id"]
                        )
                    except KeyError:
                        # value is not present
                        pass
            # 1 influencers (influenced by)
            if "P737" in claims:
                for claim in claims["P737"]:
                    try:
                        data[1] = self.gen_multival_field(
                            data[1], claim["mainsnak"]["datavalue"]["value"]["id"]
                        )
                    except KeyError:
                        # value is not present
                        pass
            # 2 influencees - not parsed - inverse property of infuenced by
            # This can be added in postprocessing by searching for entities
            # influenced by this entity.

            # 3 ULAN ID
            if "P245" in claims:
                try:
                    data[3] = claims["P245"][0]["mainsnak"]["datavalue"]["value"]
                except KeyError:
                    # value no present
                    pass
            # 4 Other urls - not parsed
            # - this can be obtained in postprocessing if field P1343
            # (described by) is parsed.

        return data

    def ___temp_disabled_person_artist(self, record):
        """
        Parses person+artist specific data.
        :param record: wikidata json record converted to dict
        :return: list of person+artist claims
        """
        return self.parse_person(record) + self.parse_artist(record)

    def parse_geographical(self, record):  # GEOGRAPHICAL NAME
        """
        Parses geographical specific data.
        :param record: wikidata json record converted to dict
        :return: list of geographical claims
        """
        """
        Parsed data:
        0 LATITUDE
        1 LONGITUDE
        2 SETTLEMENT TYPES (MULTIPLE VALUES)
        3 COUNTRY
        4 POPULATION
        5 ELEVATION / HIGHEST POINT
        6 AREA
        7 TIMEZONES (MULTIPLE VALUES)
        8 COUNTRY CALLING CODE / FEATURE CODE
        9 GEONAMES IDS
        """
        data = ["", "", "", "", "", "", "", "", "", ""]

        if "claims" in record:
            claims = record["claims"]  # bind claims to variable
            # 0 Latitude, 1 Longitude
            if "P625" in claims:
                try:
                    latitude = claims["P625"][0]["mainsnak"]["datavalue"]["value"][
                        "latitude"
                    ]
                    longitude = claims["P625"][0]["mainsnak"]["datavalue"]["value"][
                        "longitude"
                    ]
                    data[0] = str(latitude)
                    data[1] = str(longitude)
                except KeyError:
                    # Value not present
                    pass
            # 2 Settlement type - not parsed - determined by class of entity

            # 3 Country
            if "P17" in claims:
                data[3] = self.get_most_recent_value(claims["P17"], "id")
            # 4 Population
            if "P1082" in claims:
                data[4] = self.get_most_recent_value(claims["P1082"], "amount")
            # 5 Elevation / Highest point
            if "P2044" in claims:
                try:
                    data[5] = claims["P2044"][0]["mainsnak"]["datavalue"]["value"][
                        "amount"
                    ]
                except KeyError:
                    # value not present
                    pass
            elif "P610" in claims:  # Highest point
                try:
                    data[5] = claims["P610"][0]["mainsnak"]["datavalue"]["value"]["id"]
                except KeyError:
                    # Value not present
                    pass
            # 6 Area
            if "P2046" in claims:
                try:
                    data[6] = claims["P2046"][0]["mainsnak"]["datavalue"]["value"][
                        "amount"
                    ]
                except KeyError:
                    # Value not present
                    pass
            # 7 Timezone
            if "P421" in claims:
                try:
                    data[7] = claims["P421"][0]["mainsnak"]["datavalue"]["value"]["id"]
                except KeyError:
                    # Value is not present
                    pass
            # 8 Country calling code / Feature code / Local dialing code
            if "P474" in claims:
                try:
                    data[8] = claims["P474"][0]["mainsnak"]["datavalue"]["value"]
                except KeyError:
                    # Value is not present
                    pass
            elif "P473" in claims:
                try:
                    data[8] = claims["P473"][0]["mainsnak"]["datavalue"]["value"]
                except KeyError:
                    # Value is not present
                    pass
            # 9 Geonames ID
            if "P1566" in claims:
                try:
                    data[9] = claims["P1566"][0]["mainsnak"]["datavalue"]["value"]
                except KeyError:
                    # value not present
                    pass

        return data

    def parse_event(self, record):
        """
        Parses event specific data.
        :param record: wikidata json record converted to dict
        :return: array of event specific claims
        """
        """
        Parsed data:
        0 START DATE
        1 END DATE
        2 LOCATIONS (MULTIPLE VALUES)
        3 EVENT TYPE - empty - this is determined according to class classification
        """
        data = ["", "", "", ""]

        if "claims" in record:
            claims = record["claims"]  # bind claims to variable
            # 0 Start date
            if "P580" in claims:
                try:
                    data[0] = self.date_regexp.search(
                        claims["P580"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    ).group(1)
                except AttributeError:
                    # Regexp matches no data
                    pass
                except KeyError:
                    # Date field is not present
                    pass
            #  1 End date
            if "P582" in claims:
                try:
                    data[1] = self.date_regexp.search(
                        claims["P582"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    ).group(1)
                except AttributeError:
                    # Regexp matches no data
                    pass
                except KeyError:
                    # Date field is not present
                    pass
            # 2 Locations
            if "P276" in claims:
                for claim in claims["P276"]:
                    try:
                        data[2] = self.gen_multival_field(
                            data[2], claim["mainsnak"]["datavalue"]["value"]["id"]
                        )
                    except KeyError:
                        # Value not present
                        pass
            # 3 Event type - no suitable attribute found

        return data

    def parse_organization(self, record):
        """
        Parses organization specific data.
        :param record: wikidata json record converted to dict
        :return: list of organization claims
        """
        """
        0 FOUNDED
        1 CANCELLED
        2 LOCATION
        3 ORGANIZATION TYPE
        """
        data = ["", "", "", ""]

        if "claims" in record:
            claims = record["claims"]
            # 0 Founded (Inception date)
            if "P571" in claims:
                try:
                    data[0] = self.date_regexp.search(
                        claims["P571"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    ).group(1)
                except AttributeError:
                    # Regexp matches no data
                    pass
                except KeyError:
                    # Date field is not present
                    pass
            # 1 Cancelled (dissolved, abolished or demolished date)
            if "P576" in claims:
                try:
                    data[1] = self.date_regexp.search(
                        claims["P582"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    ).group(1)
                except AttributeError:
                    # Regexp matches no data
                    pass
                except KeyError:
                    # Date field is not present
                    pass
            # 2 Location (headquarters location)
            if "P159" in claims:
                try:
                    data[2] = claims["P159"][0]["mainsnak"]["datavalue"]["value"]["id"]
                except KeyError:
                    # Value not present
                    pass
            # 3 Organization type - no suitable attribute found (determined by class relation)

        return data


def main():
    """
    Main function of the script
    Inits parser and parses wikidata dump
    """

    # get command line arguments
    args = get_args()

    # init parser
    try:
        class_relations_builder = classRelationsBuilder.ClassRelationsBuilder()
        parser = SimpleWikidataDumpParser(
            input_file=args.input_file,
            output_files_tag=args.output_files_tag,
            output_folder=args.output_folder_path,
            class_relations_builder=class_relations_builder,
            parse_expanded_instances=args.parse_expanded_instances,
            lang=args.language,
        )
    except Exception:
        sys.stderr.write(
            SCRIPT_NAME
            + ": Error has occurred during parser init:\n"
            + str(traceback.format_exc())
            + "\n"
        )
        args.input_file.close()
        return 1

    # setup additional parsing options (see parser __init__() or get_args() function)
    if args.line:
        parser.dump_line = args.line
    elif args.number_of_entities:
        parser.max_entities = args.number_of_entities

    # parse wikidata dump
    exit_code = 0
    try:
        parser.parse_wikidump()
    except Exception:
        sys.stderr.write(
            SCRIPT_NAME
            + ": Error has occurred during parsing:\n"
            + str(traceback.format_exc())
            + "\n"
        )
        exit_code = 1
    else:
        # entity info
        if not args.quiet:
            print("Processed entities: " + str(parser.processed_records))
            print("Corrupted entities: " + str(parser.corrupted_records))
    finally:
        args.input_file.close()
        parser.close_output_files()
        return exit_code


# name guard for calling main function
if __name__ == "__main__":
    sys.exit(main())

