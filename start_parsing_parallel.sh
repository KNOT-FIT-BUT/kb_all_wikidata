#!/bin/sh

# file: start_parsing_parallel.sh
# description: Parses wikidata dump in parallel on all machines listed in config/hosts.list.
#              Requires additional tools from wikidata2 project to work.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: Tomáš Volf (ivolf@fit.vut.cz)

# get absolute path to folder this script is in. (/mnt/minerva1/nlp/projects/wikidata2)
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
export project_folder

# setup folder where dumps part are located
export dump_folder="/mnt/data/wikidata/"

. "${project_folder}/wikidata_lib.sh"

# print help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage:"
  echo "  sh start_parsing_parallel.sh name_of_wikidata_json_dump language tag"
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

if [ -n "$3" ]; then
  tag="$3"
else
  tag='default'
  echo "Using default tag (=\"${tag}\")"
fi

export lang;
export dump_name;

# Include timestamp functions
. "$project_folder"/timestamp.sh

# check if dump is available
dump_src="${dump_folder}/${dump_name}"
if [ ! -d "${dump_src}" ]; then
  echo "Selected dump not available!" >&2
  exit 1
fi

export local_processing_dir=`getLocalProcessingBaseDir "${dump_name}" "${lang}" "${tag}"`
export local_dicts_dir=`getLocalProcessingDictsDir "${dump_name}" "${lang}" "${tag}"`
export local_types_data_dir=`getLocalProcessingTypesDataDir "${dump_name}" "${lang}" "${tag}"`
export local_classes_dir=`getLocalProcessingClassesDir "${dump_name}" "${lang}" "${tag}"`
export master_classes_dir=`getMasterClassesDir "${dump_name}" "${lang}" "${tag}"`
export proj_tmp_dicts_dir=`getProjectTempDictsDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
export proj_tmp_types_data_dir=`getProjectTempTypesDataDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
export out_dir=`getProjectOutBaseDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`

# parse json dump
echo "Parsing started"
parsing_start=`timestamp`
ssh-keyscan -f "${project_folder}/config/hosts.list" >> ~/.ssh/known_hosts
parallel-ssh -h "${project_folder}/config/hosts.list" -p 100 -t 0 -i \
"[ -d \"$dump_src\" ] && [ -r \"$dump_src\" ] && [ -x \"$dump_src\" ] || { echo \"Can't read data from: $dump_src\" && exit 1; }; \
[ -d \"${local_types_data_dir}\" ] && [ -w \"${local_types_data_dir}\" ] || mkdir -p \"${local_types_data_dir}\";\
source ${project_folder}/wikidata_lib.sh; \
cd \"${dump_src}\"; \
find . -name '*.part????' -printf '%f\n' | \
parallel -j 6 \
\"${project_folder}/parseWikidataDump.py\" --language \"$lang\" -e -q -f {} -t \"`echo "{}" | awk -F'.' '{ print $NF }'`\" -p \"${local_processing_dir}\""
parsing_end=`timestamp`

# create folder where data will be collected
recreate_dir "${proj_tmp_dicts_dir}"
recreate_dir "${proj_tmp_types_data_dir}"

# create folder where classes will be collected
recreate_dir "${master_classes_dir}"

# copy files to project folder for id substitution
error_code=0
collecting_start=`timestamp`
cat "${project_folder}/config/hosts.list" | while read host; do
  printf "%s" "Collecting data from $host ... "
  ssh -4 "$host" bash -s "${local_types_data_dir}" "${proj_tmp_types_data_dir}" \
         "${local_dicts_dir}" "${proj_tmp_dicts_dir}" \
         "${local_classes_dir}" "${master_classes_dir}" \
         "$(cat /etc/hostname)" $(cat ${project_folder}/${FILE_MASTER_IPS}) << 'END'
  local_types_data_dir="${1}"
  proj_tmp_types_data_dir="${2}"
  local_dicts_dir="${3}"
  proj_tmp_dicts_dir="${4}"
  local_classes_dir="${5}"
  master_classes_dir="${6}"
  master_destinations=("${@:7}")
  if [ ! -d "${local_types_data_dir}" ] || [ ! -x "${local_types_data_dir}" ]; then
    echo "Parsed dump (${local_types_data_dir}) not found on $(cat /etc/hostname)"'!' >&2
    if [ ! -d "${local_types_data_dir}" ]
    then
      >&2 echo "FAILED: -d"
    fi
    if [ ! -x "${local_types_data_dir}" ]
    then
      >&2 echo "FAILED: -x"
    fi
    exit 2
  fi
  if [ ! -d "${proj_tmp_types_data_dir}" ] || [ ! -w "${proj_tmp_types_data_dir}" ] \
  ||  [ ! -d "${proj_tmp_dicts_dir}" ] || [ ! -w "${proj_tmp_dicts_dir}" ]; then
   echo "Failed to write dump data to project folder"'!'" Server: $(cat /etc/hostname)" >&2
   exit 1
  fi

  # download all types data files
  cd "${local_types_data_dir}"
  file_prefix="`ls | awk -F'.' '{ if($3~"part[0-9][0-9][0-9][0-9]" && $4=="tsv") print $1 }' | awk '{ if(!seen[$0]++) print $0 }' | grep -v -e instances`"
  echo "$file_prefix" | while read fp; do
    cat "$fp"* >> "${proj_tmp_types_data_dir}/`echo "$fp" | awk -F'_' '{ print $1 }'`.tsv"
  done


  # download all dicts data files
  cd "${local_dicts_dir}"
  file_prefix="`ls | awk -F'.' '{ if($3~"part[0-9][0-9][0-9][0-9]" && $4=="tsv") print $1 }' | awk '{ if(!seen[$0]++) print $0 }' | grep -v -e instances`"
  echo "$file_prefix" | while read fp; do
    cat "$fp"* >> "${proj_tmp_dicts_dir}/`echo "$fp" | awk -F'_' '{ print $1 }'`.tsv"
  done

  # download all class dump files
  cd "${local_classes_dir}"
  class_dumps="`ls | awk -F'_' '{ if($1=="classes") print }' | awk -F'.' '{ if($4=="json") print }'`"
  echo "$class_dumps" | while read file_name; do
    cmd="rsync \"$file_name\" \"\$master_dst\":\"${master_classes_dir}\"/"
    for master_dst in "${master_destinations[@]}"
    do
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
mkdir -p "${out_dir}"
if [ ! -d "${out_dir}" ] || [ ! -w "${out_dir}" ]; then
  echo "Can't write to ${out_dir} folder!" >&2
  exit 1
fi

# parallel name substitution (on localhost only)
echo "Starting name substitution"
substitution_start=`timestamp`
ls "${proj_tmp_types_data_dir}" | parallel \
eval "
if [ \"{}\" != \"dict.tsv\" ] ; then
  echo \"Substituting names of {.} entities\"; \
  \"$project_folder\"/substituteNames.py \
  -d \"${proj_tmp_dicts_dir}\"/dict.tsv \
  -f \"${proj_tmp_types_data_dir}\"/\"{}\" \
  -o \"${out_dir}\"/\"`echo "$dump_name" | sed 's/-all.json//'`\"-\"$lang\"-\"{.}\".tsv \
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
sh "$project_folder"/expand_instances.sh "$dump_name" "$project_folder" "$lang" "${tag}"
error_code=$?

# exit
echo "Finished, exiting."
exit $error_code
