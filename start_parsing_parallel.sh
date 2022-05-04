#!/bin/sh

# file: start_parsing_parallel.sh
# description: Parses wikidata dump in parallel on all machines listed in config/hosts.list.
#              Requires additional tools from wikidata2 project to work.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)

# get absolute path to folder this script is in. (/mnt/minerva1/nlp/projects/wikidata2)
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
export project_folder

# setup folder where dumps part are located
export dump_folder="/mnt/data/wikidata/"

. "${project_folder}/global_vars.sh"

# print help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage:"
  echo "  sh start_parsing_parallel.sh name_of_wikidata_json_dump language"
  echo "  sh start_parsing_parallel.sh --list       prints list of available dumps"
  exit 0
fi

# print list of dumps
if [ "$1" = "--list" ]; then
  echo "Available dumps:"
  for d in $(ls "$dump_folder" | grep -E "wikidata-[0-9]{8}-all.json"); do
    echo "$d"
  done
  exit 0
fi

# check for host configuration file
if [ ! -r "$project_folder"/config/hosts.list ]; then
  echo "Failed to read hosts configuration!" >&2
  exit 1
fi

# parse dump name
if [ -n "$1" ]; then
  dump_name="$1"
else
  echo "Dump name required!" >&2
  exit 1
fi

if [ -n "$2" ]; then
  lang="$2"
else
  echo "Using default language (en)"
  lang='en'
fi

export lang;
export dump_name;

# Include timestamp functions
. "$project_folder"/timestamp.sh

# check if dump is available
if [ ! -d "$dump_folder"/"$dump_name" ]; then
  echo "Selected dump not available!" >&2
  exit 1
fi

# parse json dump
echo "Parsing started"
parsing_start=`timestamp`
ssh-keyscan -f "${project_folder}/config/hosts.list" >> ~/.ssh/known_hosts
parallel-ssh -h "$project_folder"/config/hosts.list -p 100 -t 0 -i \
"[ -d \"$dump_folder\"/\"$dump_name\" ] && [ -r \"$dump_folder\"/\"$dump_name\" ] && [ -x \"$dump_folder\"/\"$dump_name\" ] || { echo \"Can't read data from \"$dump_folder\"/\"$dump_name\"\" && exit 1; }; \
[ -d /tmp/\"$USER\" ] && [ -w /tmp/\"$USER\" ] || mkdir /tmp/\"$USER\";\
[ -d /tmp/\"$USER\"/\"$dump_name\" ] && [ -w /tmp/\"$USER\"/\"$dump_name\" ] && rm -r /tmp/\"$USER\"/\"$dump_name\"; mkdir /tmp/\"$USER\"/\"$dump_name\";\
cd \"$dump_folder\"/\"$dump_name\";\
find . -name '*.part????' -printf '%f\n' | \
parallel -j 6 \
\"$project_folder\"/parseWikidataDump.py --language \"$lang\" -e -q -f {} -t \"`echo "{}" | awk -F'.' '{ print $NF }'`\" -p /tmp/\"$USER\"/\"$dump_name\""
parsing_end=`timestamp`

# create folder where data will be collected
if [ ! -d "$project_folder"/tmp_extracted_data ]; then
  mkdir "$project_folder"/tmp_extracted_data
fi
if [ -d "$project_folder"/tmp_extracted_data/"$dump_name" ]; then
  rm -r "$project_folder"/tmp_extracted_data/"$dump_name"
fi
mkdir "$project_folder"/tmp_extracted_data/"$dump_name"

# create folder where classes will be collected
if [ ! -d /tmp/"$USER"/classes ]; then
  mkdir /tmp/"$USER"/classes
fi

if [ -d /tmp/"$USER"/classes/"$dump_name" ]; then
  rm -r /tmp/"$USER"/classes/"$dump_name"/
fi
mkdir /tmp/"$USER"/classes/"$dump_name"

# copy files to project folder for id substitution
error_code=0
collecting_start=`timestamp`
cat "$project_folder"/config/hosts.list | while read host; do
  printf "%s" "Collecting data from $host ... "
  ssh -4 "$host" bash -s "$dump_name" "$project_folder" "$(cat /etc/hostname)" $(cat ${project_folder}/${FILE_MASTER_IPS}) << 'END'
  dump_name="$1"
  project_folder="$2"
  master_destinations=("${@:3}")
  if [ ! -d /tmp/"$USER"/ ] || [ ! -x /tmp/"$USER"/ ] || [ ! -d /tmp/"$USER"/"$dump_name" ] || [ ! -x /tmp/"$USER"/"$dump_name" ]; then
    echo "Parsed dump not found on $(cat /etc/hostname)"'!' >&2
    exit 2
  fi
  if [ ! -d "$project_folder"/tmp_extracted_data/"$dump_name" ] || [ ! -w "$project_folder"/tmp_extracted_data/"$dump_name" ]; then
   echo "Failed to write dump data to project folder"'!'" Server: $(cat /etc/hostname)" >&2
   exit 1
  fi
  cd /tmp/"$USER"/"$dump_name"
  # download all tsv files
  file_prefix="`ls | awk -F'.' '{ if($3~"part[0-9][0-9][0-9][0-9]" && $4=="tsv") print $1 }' | awk '{ if(!seen[$0]++) print $0 }' | grep -v -e instances`"
  echo "$file_prefix" | while read fp; do
    cat "$fp"* >> "$project_folder"/tmp_extracted_data/"$dump_name"/"`echo "$fp" | awk -F'_' '{ print $1 }'`".tsv
  done
  # download all class dump files
  class_dumps="`ls | awk -F'_' '{ if($1=="classes") print }' | awk -F'.' '{ if($4=="json") print }'`"
  echo "$class_dumps" | while read file_name; do
    cmd="rsync \"$file_name\" \"\$master_dst\":/tmp/\"$USER\"/classes/\"$dump_name\"/"
    for master_dst in "${master_destinations[@]}"
    do
      echo "[`date "+%Y-%m-%d %H:%M:%S.%N"`]   RSYNC \"${file_name}\" to master destination \"${master_dst}\".."
      eval $cmd
      if test "$?" == 0
      then
        break
      fi
    done
  done
END
if [ $? -eq 0 ]; then
  echo "OK"
else
  echo "FAILED"
  exit 1
fi
done
error_code=$?
collecting_end=`timestamp`

# error exit
if [ $error_code -ne 0 ]; then
  echo "Failed to collect dump!" >&2
  exit $error_code
fi

# create folder where result will be stored
if [ ! -d "$project_folder"/tsv_extracted_from_wikidata/ ] || [ ! -w "$project_folder"/tsv_extracted_from_wikidata/ ]; then
  echo "Can't write to $project_folder/tsv_extracted_from_wikidata/ folder!" >&2
  exit 1
fi
mkdir -p "$project_folder"/tsv_extracted_from_wikidata/"$dump_name"

# parallel name substitution (on localhost only)
echo "Starting name substitution"
substitution_start=`timestamp`
ls "$project_folder"/tmp_extracted_data/"$dump_name" | parallel \
eval "
if [ \"{}\" != \"dict.tsv\" ] ; then
  echo \"Substituting names of {.} entities\"; \
  \"$project_folder\"/substituteNames.py \
  -d \"$project_folder\"/tmp_extracted_data/\"$dump_name\"/dict.tsv \
  -f \"$project_folder\"/tmp_extracted_data/\"$dump_name\"/\"{}\" \
  -o \"$project_folder\"/tsv_extracted_from_wikidata/\"$dump_name\"/\"`echo "$dump_name" | sed 's/-all.json//'`\"-\"$lang\"-\"{.}\".tsv \
  -e 0 8 9 10 11 \
  --remove-missing
fi
"
substitution_end=`timestamp`

# TODO
# call scripts for downloading images etc.

# print time for each section
parsing_time="`timestamp_diff "$parsing_start" "$parsing_end"`"
collecting_time="`timestamp_diff "$collecting_start" "$collecting_end"`"
substitution_time="`timestamp_diff "$substitution_start" "$substitution_end"`"
total_time="`timestamp_diff "$parsing_start" "$substitution_end"`"
echo "Parsing time: `show_time "$parsing_time"`"
echo "Collection time: `show_time "$collecting_time"`"
echo "Substitution time: `show_time "$substitution_time"`"
echo "Total time: `show_time "$total_time"`"

echo "Generating TC and expanding instances."
sh "$project_folder"/expand_instances.sh "$dump_name" "$project_folder" "$lang"
error_code=$?

# exit
echo "Finished, exiting."
exit $error_code
