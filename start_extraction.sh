#!/bin/sh

# file: start_extraction.sh
# description: Starts complete extraction of newest wikidata dump.
#              Merges extracted data with data from entity_kb_czech9.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# edited by: René Rešetár (xreset00@stud.fit.vutbr.cz)
# added extraction from entity_kb_czech9 project

project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
export project_folder

dump_parser="$project_folder"/start_parsing_parallel.sh
merge_script="$project_folder"/merge_KB/start_merge.sh

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage:"
  echo "  sh start_extraction.sh"
  echo "  sh start_extraction.sh dump_name"
  echo "Arguments:"
  echo "  dump_name     Name of the dump to process. If not supplied,"
  echo "                newest available dump is used automatically."
  echo "  --list        Prints list of dump available for processing."
  echo "Description:"
  echo "  Starts extraction of wikidata dump and merges resulting data"
  echo "  with data from entity_kb_czech9 project."
  echo "  Only czech KB is processed because entity_kb_czech9 does not"
  echo "  provide english data. Use $(echo "$dump_parser" | awk -F'/' '{ print $NF }') directly"
  echo "  to extract english data from dump."
  exit 0
fi

# print available dumps
if [ "$1" = "--list" ]; then
  sh "$dump_parser" --list
  exit $?
fi

# select dump to process
if [ -n "$1" ]; then
  # select dump from argument
  dump_name="$1"
else
  # select newest dump available if not selected by user
  dump_name="$(sh "$dump_parser" --list | tail -n1 | grep -v 'Available dumps:')"
  # check if dump was selected
  if [ -z "$dump_name" ]; then
    echo "No dump available for extraction!" >&2
    exit 1
  fi
fi

# start dump extraction
sh "$dump_parser" "$dump_name" cs
parser_error_code=$?

if [ $parser_error_code -ne 0 ]; then
  echo "Dump extraction failed!" >&2
  exit $parser_error_code
fi

# change parser and start extraction
dump_parser="$project_folder"/additional_types/start_parsing.sh
sh "$dump_parser" -d "$dump_name"
ent9_parser_error_code=$?

if [ $ent9_parser_error_code -ne 0 ]; then
  echo "Dump extraction from entity_kb_czech9 failed!" >&2
  exit $ent9_parser_error_code
fi

# merge dump with entity_kb_czech9
sh "$merge_script" "$dump_name"
merge_error_code=$?

if [ $merge_error_code -ne 0 ]; then
  echo "Merging with entity_kb_czech9 failed!" >&2
  exit $merge_error_code
fi

# Extraction complete
echo "Extraction and merging complete!"
echo "See output above for time statistics."

exit 0
