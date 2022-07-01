#!/usr/bin/env python3
# encoding UTF-8

# File: substituteNames.py
# Author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# Project: wikidata2
# Description: Substitutes names in parsed wikidata dump with ids.

import argparse
import os  # filesystem
import sys  # stderr, exit, ...
import traceback  # for printing exceptions

import parseJson2  # for wikidata dump manipulator, WikidataNameInterchanger

# get script name
SCRIPT_NAME = os.path.basename(sys.argv[0])


def get_args():
    argparser = argparse.ArgumentParser("Substitutes names in parsed wikidata dump.")
    argparser.add_argument(
        "-d",
        "--dict-file",
        help="Dictionary file with names and ids relations.",
        type=argparse.FileType("r"),
        required=True,
    )
    argparser.add_argument(
        "-f",
        "--input-file",
        help="File with parsed KB where to substitute names.",
        type=argparse.FileType("r"),
        required=True,
    )
    argparser.add_argument(
        "-o",
        "--output-file",
        help="Output file with resulting KB.",
        type=argparse.FileType("w"),
        required=True,
    )
    argparser.add_argument(
        "--show-missing",
        help="Display ids with missing translation.",
        required=False,
        default=False,
        action="store_true",
    )
    argparser.add_argument(
        "--remove-missing",
        help="Remove ids with missing translation instead of keeping them in KB unchanged.",
        required=False,
        default=False,
        action="store_true",
    )
    argparser.add_argument(
        "--min-field",
        help="Index of first field where id will be substituted.",
        required=False,
        type=int,
        default=1,
    )
    argparser.add_argument(
        "--max-field",
        help="Index of last field where id will be substituted.",
        required=False,
        type=int,
        default=8,
    )
    argparser.add_argument(
        "-e",
        "--exclude",
        help="Indexes of fields to exclude during substitution.",
        required=False,
        type=int,
        nargs="+",
        default=[
            0,
            8,
            9,
            10,
            11,
        ],  # current ID(0), site urls(8, 9, 10), image names(11)
    )
    return argparser.parse_args()


def main():
    args = get_args()

    return_code = 0
    name_changer = parseJson2.WikidataNameInterchanger(
        input_file=args.input_file,
        dict_file=args.dict_file,
        output_file=args.output_file,
        show_missing=args.show_missing,
        exclude=args.exclude,
        remove_missing=args.remove_missing,
    )
    try:
        name_changer.substitute_names()
        if args.show_missing:
            print(
                "Number of entities without name: "
                + str(len(name_changer.ids_without_translation))
            )
            first = True
            for entity_id in name_changer.ids_without_translation:
                if first:
                    first = False
                    sys.stdout.write(str(entity_id))
                else:
                    sys.stdout.write(", " + str(entity_id))
            sys.stdout.write("\n")
    except:
        sys.stderr.write(
            SCRIPT_NAME
            + ": Failed to substitute ids for names! Handled error:\n"
            + str(traceback.format_exc())
            + "\n"
        )
        return_code = 1

    return return_code


# name guard for calling main function
if __name__ == "__main__":
    sys.exit(main())
