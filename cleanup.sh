#!/bin/sh

# file: cleanup.sh
# description: Cleans up data after wikidata dump extraction.
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)

rm_empty() {  # remove empty dir
  if [ -d "$1" ] && [ -z "$(ls "$1")" ]; then
    rmdir "$1"
  fi
}

# setup project folder
if [ -n "$2" ]; then # passed in by arg
  project_folder="$2"
  export project_folder
elif [ -z "$project_folder" ]; then # not passed in
  # get absolute path to folder this script is in. (/mnt/minerva1/nlp/projects/wikidata2)
  project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
  export project_folder
fi
# else passed by environment variable (export project_folder)

# print help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo 'Usage:'
  echo '  sh cleanup.sh dump_name [project_folder]'
  echo ''
  echo "  --list   - lists dumps available for clean up"
  echo "  If dump name is 'all', cleans all dumps."
  exit 0
fi

if [ "$1" = "--list" ]; then
  echo 'Dumps to clean up:'
  for d in $(ls "$project_folder"/tsv_extracted_from_wikidata); do
    echo "$d"
  done
  exit 0
fi

if [ -z "$1" ]; then
  echo "Dump name not specified, see '--help' for more information"'!'
  exit 1
fi

export dump_name="$1"

# cleanup temp data
for host in $(cat "$project_folder"/config/hosts.list); do
  printf "%s" "Cleaning up $host ... "
  ssh "$host" bash -s "$dump_name" << 'END'
rm_empty() {
  if [ -d "$1" ] && [ -z "$(ls "$1")" ]; then
    rmdir "$1"
  fi
}

rm_all() {
  if [ -d "/tmp/$USER/classes" ]; then
    rm -rf "/tmp/$USER/classes"
  fi
  if [ -d "/tmp/$USER/expanded_instance_kb" ]; then
    rm -rf "/tmp/$USER/expanded_instance_kb"
  fi
  if [ -d "/tmp/$USER/instances" ]; then
    rm -rf "/tmp/$USER/instances"
  fi
  if [ -n "$(ls "/tmp/$USER/" | grep -F 'wikidata' | grep -F 'all.json')" ]; then
    for d in $(ls "/tmp/$USER/" | grep -F 'wikidata' | grep -F 'all.json'); do
      rm -rf "/tmp/$USER/$d"
    done
  fi
}

rm_class() {
  if [ -d "/tmp/$USER/classes" ]; then
    rm -rf "/tmp/$USER/classes/$1"
  fi
  rm_empty "/tmp/$USER/classes"
  if [ -d "/tmp/$USER/expanded_instance_kb" ]; then
    rm -rf "/tmp/$USER/expanded_instance_kb/$1"
  fi
  rm_empty "/tmp/$USER/expanded_instance_kb"
  if [ -d "/tmp/$USER/instances" ]; then
    rm -rf "/tmp/$USER/instances/$1"
  fi
  rm_empty "/tmp/$USER/instances"
  if [ -d "/tmp/$USER/$1" ]; then
    rm -rf "/tmp/$USER/$1"
  fi
}

# ============== main ==============
if [ -d "/tmp/$USER" ]; then
  if [ "$1" = "all" ]; then # remove all
    rm_all
  else # remove specific class
    rm_class "$1"
  fi
  rm_empty "/tmp/$USER"
fi
END
if [ $? -eq 0 ]; then
  echo "OK"
else
  echo "FAILED"
fi
done

# clean up project folder
if [ -d "$project_folder"/tmp_extracted_data ]; then
  if [ "$dump_name" = "all" ]; then # - remove all
    rm -rf "$project_folder"/tmp_extracted_data
  else # - remove only specific dump

    for folder in classes expanded_instance_kb instances; do
      # remove dump tc data
      if [ -d "$project_folder"/tmp_extracted_data/"$folder" ] && \
      [ -d "$project_folder"/tmp_extracted_data/"$folder"/"$dump_name" ]; then
        rm -rf "$project_folder"/tmp_extracted_data/"$folder"/"$dump_name"
      fi
      # remove folders if empty
      rm_empty "$project_folder"/tmp_extracted_data/"$folder"
    done

    # remove dump folder
    rm -rf "$project_folder"/tmp_extracted_data/"$dump_name"
    # remove tmp_extracted_data if empty
    rm_empty "$project_folder"/tmp_extracted_data

  fi # - end
fi

echo "Data in $project_folder/tsv_extracted_from_wikidata are skipped, remove them manually if needed"'!'

exit
