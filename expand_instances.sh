#!/bin/sh

# file: expand_instances.sh
# description: Expands relations of wikidata instances in parallel.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: Tomáš Volf (ivolf@fit.vut.cz)

# help
if [ "$1" = "--help" ]; then
  echo "Usage:"
  echo "  sh expand_instances.sh name_of_wikidata_json_dump project_folder_full_path kb_language"
  exit 0
fi

# setup
if [ ! "$1" ] || [ ! "$2" ] || [ ! "$3" ]; then
  echo "Wrong arguments!" >&2
  exit 1
fi

export dump_name="$1"
export project_folder="$2"
export lang="$3"
export tag="${4}"

# Include timestamp functions
. "$project_folder"/timestamp.sh

. "${project_folder}/wikidata_lib.sh"

# create folder where classes will be stored
classes_dir=`getProjectTempClassesDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
recreate_dir "${classes_dir}"

# concatenate class relations
echo "Starting class relations concatenation"
fpath_full_classes="${classes_dir}/classes_full.json"
concatenation_start=`timestamp`
python3 "$project_folder"/classRelationsBuilder.py -s -r -d `getLocalProcessingClassesDir "${dump_name}" "${lang}" "${tag}"` \
 -c "${fpath_full_classes}"
concatenation_end=`timestamp`


proj_tmp_dicts_dir=`getProjectTempDictsDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
proj_tmp_types_dir=`getProjectTempTypesDataDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
out_dir=`getProjectOutBaseDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`

# expand instances
echo "Starting to expand instances"
expansion_start=`timestamp`
local_instances_dir=`getLocalProcessingInstancesDir "${dump_name}" "${lang}" "${tag}"`
mkdir -p "${local_instances_dir}"
parallel-ssh -h "$project_folder"/config/hosts.list -p 100 -t 0 -i \
"[ -d \"${local_instances_dir}\" ] && [ -w \"${local_instances_dir}\" ] || \
{ echo \"Instances not found (${local_instances_dir}).\" >&2; exit 1; }
cd \"${local_instances_dir}\"
ls | awk -F'_' '{ if(\$1==\"instances\") print }' | awk -F'.' '{ if(\$4==\"json\") print }' | parallel -j6 \
  \"$project_folder/classRelationsBuilder.py -i {} -e {.}.tsv \
    -c "${fpath_full_classes}"
    sort {.}.tsv > {.}.tsv_sorted
    mv {.}.tsv_sorted {.}.tsv\"
"
expansion_end=`timestamp`


# expand instances in expanded instances kb
echo "Starting to generate expanded instance KB parts"
kb_expansion_start=`timestamp`
local_expanded_instances_dir=`getLocalProcessingExpandedInstancesDir "${dump_name}" "${lang}" "${tag}"`
mkdir -p "${local_expanded_instances_dir}"
parallel-ssh -h "$project_folder"/config/hosts.list -p 100 -t 0 -i \
"[ -d \"${local_expanded_instances_dir}\" ] && [ -w \"${local_expanded_instances_dir}\" ] || \
{ echo \"Expanded instances not found (${local_expanded_instances_dir}).\" >&2; exit 1; }
cd \"${local_expanded_instances_dir}\"
ls | awk -F'_' '{ if(\$1==\"expanded\" && \$2==\"instances\") print }' | awk -F'.' '{ if(\$4==\"tsv\") print }' | parallel -j6 \
    $project_folder/classRelationsBuilder.py -l {} -o {.}.processed.tsv \
    -c \"${fpath_full_classes}\"
"
kb_expansion_end=`timestamp`

# create folder where instances will be stored
master_instances_dir=`getMasterInstancesDir "${dump_name}" "${lang}" "${tag}"`
recreate_dir "${master_instances_dir}"

# create folder where expanded instance kb will be stored
master_expanded_instances_dir=`getMasterExpandedInstancesDir "${dump_name}" "${lang}" "${tag}"`
recreate_dir "${master_expanded_instances_dir}"

# download processed instances
error_code=0
echo "Collecting instances from nodes"
collection_start=`timestamp`
cat "$project_folder"/config/hosts.list | while read host; do
  printf "%s" "Collecting instances from $host ... "
  ssh -4 "$host" bash -s "${local_instances_dir}" "${master_instances_dir}" "${local_expanded_instances_dir}" \
         "${master_expanded_instances_dir}" "$(cat /etc/hostname)" $(cat ${project_folder}/${FILE_MASTER_IPS}) << 'END'
  local_instances_dir="${1}"
  master_instances_dir="${2}"
  local_expanded_instances_dir="${3}"
  master_expanded_instances_dir="${4}"
  master_destinations=("${@:5}")
  cd "${local_instances_dir}"
  files="`ls | awk -F'_' '{ if($1=="instances") print }' | awk -F'.' '{ if($4=="tsv") print }'`"
  echo "$files" | while read fn; do
    cmd="rsync \"$fn\" \"\$master_dst\":\"${master_instances_dir}\""
    for master_dst in "${master_destinations[@]}"
    do
      echo "[`date "+%Y-%m-%d %H:%M:%S.%N"`]   RSYNC \"${fn}\" to master destination \"${master_dst}\".."
      eval $cmd
      if test "$?" == 0
      then
        break
      fi
    done
  done
  cd "${local_expanded_instances_dir}"
  files="`ls | awk -F'_' '{ if($1=="expanded" && $2=="instances") print }' | awk -F'.' '{ if($4=="processed" && $5=="tsv") print }'`"
  echo "$files" | while read fn; do
    cmd="rsync \"$fn\" \"\$master_dst\":\"${master_expanded_instances_dir}\""
    for master_dst in "${master_destinations[@]}"
    do
      echo "[`date "+%Y-%m-%d %H:%M:%S.%N"`]   RSYNC \"${fn}\" to master destination \"${master_dst}\".."
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
collection_end=`timestamp`

# error exit
if [ $error_code -ne 0 ]; then
  echo "Failed to download instances!" >&2
  exit $error_code
fi

# create final output folder for instances
tmp_instances_dir=`getProjectTempInstancesDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
mkdir -p "${tmp_instances_dir}"

# create final output folder for expanded kb
tmp_expanded_instances_dir=`getProjectTempExpandedInstancesDir "${dump_name}" "${lang}" "${tag}" "${project_folder}"`
mkdir -p "${tmp_expanded_instances_dir}"

# parallel name substitution (on localhost only) (expanded instance kb)
echo "Starting name substitution"
kb_substitution_start=`timestamp`
ls "${master_expanded_instances_dir}" | parallel -j6 \
eval "
if [ \"{}\" != \"dict.tsv\" ] ; then
  echo \"Substituting names of {}\"; \
  \"$project_folder\"/substituteNames.py \
  -d \"${proj_tmp_dicts_dir}/dict.tsv\" \
  -f \"${master_expanded_instances_dir}/{}\" \
  -o \"${master_expanded_instances_dir}/{.}.name_substituted.tsv\" \
  -e 0 8 9 10 11 \
  --remove-missing
fi
"
kb_substitution_end=`timestamp`

# concatenate instance files and copy result to output folder
echo "Concatenating collected data to final result"
final_start=`timestamp`
cd "${master_instances_dir}" || { echo "Failed to concatenate instances!" >&2; exit 1; }
sort -m `ls` > instances_all.tsv
mv instances_all.tsv "${tmp_instances_dir}/"
cd "$project_folder" || { echo "Failed to change folder to $project_folder!"; exit 1; }
final_end=`timestamp`

# concatenate expanded instance kb and copy result to output folder
final_kb_start=`timestamp`
cd "${master_expanded_instances_dir}" || { echo "Failed to concatenate expanded instance kb!" >&2; exit 1; }
cat `ls | grep name_substituted` > wikidata_expanded_instance_kb.tsv
mv wikidata_expanded_instance_kb.tsv "${tmp_expanded_instances_dir}/wikidata_expanded_instance_kb_${lang}.tsv"
cd "$project_folder" || { echo "Failed to change folder to $project_folder!"; exit 1; }
final_kb_end=`timestamp`

# calculate time elapsed
concatenation_time="`timestamp_diff "$concatenation_start" "$concatenation_end"`"
expansion_time="`timestamp_diff "$expansion_start" "$expansion_end"`"
kb_expansion_time="`timestamp_diff "$kb_expansion_start" "$kb_expansion_end"`"
collection_time="`timestamp_diff "$collection_start" "$collection_end"`"
kb_substitution_time="`timestamp_diff "$kb_substitution_start" "$kb_substitution_end"`"
final_time="`timestamp_diff "$final_start" "$final_end"`"
final_kb_time="`timestamp_diff "$final_kb_start" "$final_kb_end"`"
total_time="`timestamp_diff "$concatenation_start" "$final_end"`"

# show time elapsed
echo "Class concatenation time: `show_time "$concatenation_time"`"
echo "Instance expansion time: `show_time "$expansion_time"`"
echo "KB expansion time: `show_time "$kb_expansion_time"`"
echo "Data collection time: `show_time "$collection_time"`"
echo "KB name substitution time: `show_time "$kb_substitution_time"`"
echo "Final data concatenation time: `show_time "$final_time"`"
echo "Final KB concatenation time: `show_time "$final_kb_time"`"
echo "Total time elapsed: `show_time "$total_time"`"

# exit
echo "Instance expansion finished."
exit 0
