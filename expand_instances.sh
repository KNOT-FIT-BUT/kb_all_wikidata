#!/bin/sh

# file: expand_instances.sh
# description: Expands relations of wikidata instances in parallel.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)

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

# Include timestamp functions
. "$project_folder"/timestamp.sh

# create folder where classes will be stored
if [ ! -d "$project_folder"/tmp_extracted_data/classes ]; then
  mkdir "$project_folder"/tmp_extracted_data/classes/
fi
if [ -d "$project_folder"/tmp_extracted_data/classes/"$dump_name" ]; then
  rm -r "$project_folder"/tmp_extracted_data/classes/"$dump_name"
fi
mkdir "$project_folder"/tmp_extracted_data/classes/"$dump_name"

# concatenate class relations
echo "Starting class relations concatenation"
concatenation_start=`timestamp`
python3 "$project_folder"/classRelationsBuilder.py -s -r -d /tmp/"$USER"/classes/"$dump_name"/ \
 -c "$project_folder"/tmp_extracted_data/classes/"$dump_name"/classes_full.json
concatenation_end=`timestamp`


# expand instances
echo "Starting to expand instances"
expansion_start=`timestamp`
parallel-ssh -h "$project_folder"/config/hosts.list -p 100 -t 0 -i \
"[ -d /tmp/$USER ] && [ -w /tmp/$USER ] && \
[ -d /tmp/$USER/$dump_name ] && [ -w /tmp/$USER/$dump_name ] || \
{ echo \"Instances not found\" >&2; exit 1; }
cd /tmp/$USER/$dump_name
ls | awk -F'_' '{ if(\$1==\"instances\") print }' | awk -F'.' '{ if(\$4==\"json\") print }' | parallel -j6 \
  \"$project_folder/classRelationsBuilder.py -i {} -e {.}.tsv \
    -c $project_folder/tmp_extracted_data/classes/$dump_name/classes_full.json
    sort {.}.tsv > {.}.tsv_sorted
    mv {.}.tsv_sorted {.}.tsv\"
"
expansion_end=`timestamp`


# expand instances in expanded instances kb
echo "Starting to generate expanded instance KB parts"
kb_expansion_start=`timestamp`
parallel-ssh -h "$project_folder"/config/hosts.list -p 100 -t 0 -i \
"[ -d /tmp/$USER ] && [ -w /tmp/$USER ] && \
[ -d /tmp/$USER/$dump_name ] && [ -w /tmp/$USER/$dump_name ] || \
{ echo \"Instances not found\" >&2; exit 1; }
cd /tmp/$USER/$dump_name
ls | awk -F'_' '{ if(\$1==\"expanded\" && \$2==\"instances\") print }' | awk -F'.' '{ if(\$4==\"tsv\") print }' | parallel -j6 \
    $project_folder/classRelationsBuilder.py -l {} -o {.}.processed.tsv \
    -c $project_folder/tmp_extracted_data/classes/$dump_name/classes_full.json
"
kb_expansion_end=`timestamp`


# create folder where instances will be stored
if [ ! -d /tmp/"$USER"/instances/ ]; then
  mkdir /tmp/"$USER"/instances/
fi
if [ -d /tmp/"$USER"/instances/"$dump_name" ]; then
  rm -r /tmp/"$USER"/instances/"$dump_name"
fi
mkdir /tmp/"$USER"/instances/"$dump_name"

# create folder where expanded instance kb will be stored
if [ ! -d /tmp/"$USER"/expanded_instance_kb/ ]; then
  mkdir /tmp/"$USER"/expanded_instance_kb/
fi
if [ -d /tmp/"$USER"/expanded_instance_kb/"$dump_name" ]; then
  rm -r /tmp/"$USER"/expanded_instance_kb/"$dump_name"
fi
mkdir /tmp/"$USER"/expanded_instance_kb/"$dump_name"

# download processed instances
error_code=0
echo "Collecting instances from nodes"
collection_start=`timestamp`
cat "$project_folder"/config/hosts.list | while read host; do
  printf "%s" "Collecting instances from $host ... "
  ssh "$host" bash -s "$dump_name" "$project_folder" "$(cat /etc/hostname)" << 'END'
  dump_name=$1
  project_folder=$2
  master_node="$3"
  cd /tmp/"$USER"/"$dump_name"
  files="`ls | awk -F'_' '{ if($1=="instances") print }' | awk -F'.' '{ if($4=="tsv") print }'`"
  echo "$files" | while read fn; do
    rsync "$fn" "$master_node":/tmp/"$USER"/instances/"$dump_name"/
  done
  files="`ls | awk -F'_' '{ if($1=="expanded" && $2=="instances") print }' | awk -F'.' '{ if($4=="processed" && $5=="tsv") print }'`"
  echo "$files" | while read fn; do
    rsync "$fn" "$master_node":/tmp/"$USER"/expanded_instance_kb/"$dump_name"/
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

# create final output folder
mkdir -p "$project_folder"/tmp_extracted_data/instances/"$dump_name"

# create final output folder for expanded kb
mkdir -p "$project_folder"/tmp_extracted_data/expanded_instance_kb/"$dump_name"

# parallel name substitution (on localhost only) (expanded instance kb)
echo "Starting name substitution"
kb_substitution_start=`timestamp`
ls /tmp/"$USER"/expanded_instance_kb/"$dump_name" | parallel -j6 \
eval "
if [ \"{}\" != \"dict.tsv\" ] ; then
  echo \"Substituting names of {}\"; \
  \"$project_folder\"/substituteNames.py \
  -d \"$project_folder\"/tmp_extracted_data/\"$dump_name\"/dict.tsv \
  -f /tmp/\"$USER\"/expanded_instance_kb/\"$dump_name\"/\"{}\" \
  -o /tmp/\"$USER\"/expanded_instance_kb/\"$dump_name\"/\"{.}\".name_substituted.tsv \
  -e 0 8 9 10 11
fi
"
kb_substitution_end=`timestamp`

# concatenate instance files and copy result to output folder
echo "Concatenating collected data to final result"
final_start=`timestamp`
cd /tmp/"$USER"/instances/"$dump_name" || { echo "Failed to concatenate instances!" >&2; exit 1; }
sort -m `ls` > instances_all.tsv
mv instances_all.tsv "$project_folder"/tmp_extracted_data/instances/"$dump_name"/
cd "$project_folder" || { echo "Failed to change folder to $project_folder!"; exit 1; }
final_end=`timestamp`

# concatenate expanded instance kb and copy result to output folder
final_kb_start=`timestamp`
cd /tmp/"$USER"/expanded_instance_kb/"$dump_name" || { echo "Failed to concatenate expanded instance kb!" >&2; exit 1; }
cat `ls | grep name_substituted` > wikidata_expanded_instance_kb.tsv
mv wikidata_expanded_instance_kb.tsv "$project_folder"/tmp_extracted_data/expanded_instance_kb/"$dump_name"/wikidata_expanded_instance_kb_"$lang".tsv
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
