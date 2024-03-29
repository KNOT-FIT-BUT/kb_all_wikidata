#!/bin/sh

# file: start_extraction.sh
# description: Starts complete extraction of newest wikidata dump.
#              Merges extracted data with data from entity_kb_czech9.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: Tomáš Volf (ivolf@fit.vut.cz)
# Can not use readlink, due to calling subscript by absolute path with following symlinks, but there are different mounting points of home folders on nodes.
# (this absolute path is then used in processing on multiple nodes, which however does not know this absolute path)
cwd_original=$PWD

project_folder=$(cd "$(dirname $0)" && pwd)
export project_folder

export LC_ALL=en_US.UTF-8

dump_parser="$project_folder"/start_parsing_parallel.sh
merge_script="$project_folder"/merge_KB/start_merge.sh
mkkb_script="$project_folder"/merge_KB/mkkb.sh

list_dumps=false
dump_name=''
print_help=false
lang='cs'
tag='default'
unknown=''  # unknown parameters

. "${project_folder}/wikidata_lib.sh"

# parse params
while true; do
  case "$1" in
    --help|-h )
      print_help=true
      shift
      ;;
    --list|-l )
      list_dumps=true
      shift
      ;;
    --dump|-d )
      dump_name="$2"
      if [ -z "$2" ]; then
        >&2 echo "Dump name missing!"
        exit 1
      fi
      shift 2
      ;;
    --dump=* )
      dump_name="$(echo "$1" | awk -F'=' '{ print $2 }')"
      shift
      ;;
    -d* )
      dump_name="$(echo "$1" | sed 's/^..\(.*\)/\1/')"
      shift
      ;;
    --lang|-g )
      lang="$2"
      if [ -z "$2" ]; then
        >&2 echo "Specify the language!"
        exit 1
      fi
      shift 2
      ;;
    --lang=* )
      lang="$(echo "$1" | awk -F'=' '{ print $2 }')"
      shift
      ;;
    -g* )
      lang="$(echo "$1" | sed 's/^..\(.*\)/\1/')"
      shift
      ;;
    --tag|-t )
      tag="$2"
      if [ -z "$2" ]; then
        >&2 echo "Tag name missing!"
        exit 1
      fi
      shift 2
      ;;
    --tag=* )
      tag="$(echo "$1" | awk -F'=' '{ print $2 }')"
      shift
      ;;
    -t* )
      tag="$(echo "$1" | sed 's/^..\(.*\)/\1/')"
      shift
      ;;
    * )
      unknown="$1"
      break
      ;;
  esac
done

if [ -n "$unknown" ]; then
  echo "Unknown argument $unknown"'!' >&2
  exit 1
fi

if $print_help; then
  echo "Usage:"
  echo "  sh start_extraction.sh"
  echo "  sh start_extraction.sh [--dump <dump_name>] [--lang ${lang}] [--tag ${tag}]"
  echo "Arguments:"
  echo "  --dump|-d     Name of the dump to process. If not supplied,"
  echo "                newest available dump is used automatically."
  echo "  --lang|-g     Selects language of the extracted KB (default: \"${lang}\")."
  echo "  --list|-l     Prints list of dump available for processing."
  echo "  --tag|-t      Tag output directory which allows to distinguish"
  echo "                outputs in case of multiple processing same dump"
  echo "                and same language (default: \"${tag}\")."
  echo "  --help|-h     Prints help."
  echo "Description:"
  echo "  Starts extraction of wikidata dump and merges resulting data"
  echo "  with data from entity_kb_czech9 project."
  echo "  Only czech KB is processed because entity_kb_czech9 does not"
  echo "  provide english data. Use $(echo "$dump_parser" | awk -F'/' '{ print $NF }') directly"
  echo "  to extract english data from dump."
  exit 0
fi

# print available dumps
if $list_dumps; then
  sh "$dump_parser" --list
  exit $?
fi

# select dump to process, if not selected by user
if [ -z "$dump_name" ]; then
  # select newest dump available
  dump_name="$(sh "$dump_parser" --list | tail -n1 | grep -v 'Available dumps:')"
  # check if dump was selected
  if [ -z "$dump_name" ]; then
    echo "No dump available for extraction!" >&2
    exit 1
  fi
  echo "Selected dump: $dump_name"
fi

out_dir=`getProjectOutBaseDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
persons_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-person.tsv
group_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-group.tsv
artist_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-person+artist.tsv
geographical_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-geographical.tsv
event_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-event.tsv
organization_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-organization.tsv
artwork_file="$out_dir"/"$(echo "$dump_name" | sed 's/-all.json//')"-"$lang"-artwork.tsv

# print warning about extraction of other than czech language
if [ "$lang" != 'cs' ]; then
  echo "Selected language is $lang"'!' >&2
  echo 'This language might not be supported by all merged KBs!' >&2
fi

# acquire master ip adresses to avoid rsyncs failed when DNS goes wrong
ip -4 addr | grep -PA1 "^[0-9]+:\se[nt]" | grep -oP "(?<=inet\s)\d+(\.\d+){3}" > "${project_folder}/${FILE_MASTER_IPS}"
ip -6 addr | grep -PA1 "^[0-9]+:\se[nt]" | grep -oP "(?<=inet6\s)[0-9a-f]+(\:+[0-9a-f]+)+" >> "${project_folder}/${FILE_MASTER_IPS}"

# start dump extraction
sh "$dump_parser" "$dump_name" "$lang" "${tag}"
parser_error_code=$?

if [ $parser_error_code -ne 0 ]; then
  echo "Dump extraction failed!" >&2
  exit $parser_error_code
fi

for file in ${persons_file} ${group_file} ${artist_file} ${geographical_file} ${event_file} ${organization_file} ${artwork_file}
do
  sed -i "s/^[^\t]*://" "${file}"
done

if [ "$lang" = 'cs' ]; then
  # merge dump with entity_kb_czech9
  sh "$merge_script" -d "$dump_name" -g "$lang"
  merge_error_code=$?

  if [ $merge_error_code -ne 0 ]; then
    echo "Merging with entity_kb_czech9 failed!" >&2
    exit $merge_error_code
  fi
else
  echo "Merging with entity_kb_czech9 skipped"'!'
  echo "Selected language is not supported"'!'
  echo "Generating KB without entity_kb_czech9"
  sh "$mkkb_script" -p "$persons_file"        \
                    -g "$group_file"          \
                    -a "$artist_file"         \
                    -l "$geographical_file"   \
                    -e "$event_file"          \
                    -o "$organization_file"   \
                    --artwork="${artwork_file}"   \
                    --dump=${dump_name}       \
                    --lang=${lang}

  mkkb_error_code=$?
  if [ $mkkb_error_code -ne 0 ]; then
    echo 'KB creation failed!' >&2
    exit $mkkb_error_code
  fi
fi

# Extraction complete
echo "Extraction and merging complete!"
echo "See output above for time statistics."

exit 0
