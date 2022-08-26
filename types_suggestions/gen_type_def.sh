#!/bin/bash

# file: gen_type_def.sh
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
#         Tomas Volf (ivolf@fit.vut.cz)
# description: Generates KB type definition (selects classes to type) using combination of subclass lists
#              and transitive closures. Selects classes according to number of occurrences.

# prints help message
help() {
  echo "Usage:"
  echo "  sh gen_type_def.sh top_class path/to/wikidata/id/dictionary [ path/to/wikidata/subclass/list ] [ path/to/wikidata/transitive/closure ] [ path/to/project/folder ]"
}

# default values
subclass_list="subclass_list.tsv"
tc="tc.tsv"
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
substitute_names_script="${project_folder}/../substituteNames.py"
host_list="${project_folder}/../config/hosts.list"

class_relations_builder_path="${project_folder}/../classRelationsBuilder.py"
class_relations_builder_args=()

# print help
if [ "${1}" = "--help" ]; then
  help
  exit
fi

# check arguments
if ! echo "${1}" | grep -qE "Q[0-9]+"; then
  echo "Wrong top_class id, use wikidata id of the class!"
  exit 1
fi

if [ -z "${2}" ] || [ ! -f "${2}" ]; then
  echo "Wrong path to wikidata dictionary! See '--help' for usage information!"
  exit 1
fi

subclass_list_customized=false
if [ -n "${3}" ]; then
  subclass_list="${3}"
  subclass_list_customized=true
fi
if ! test -f "${subclass_list}"
then
  if test "${subclass_list_customized}" = true
  then
    echo -n "Wrong path to wikidata subclass list!"
  else
    echo -n "Default wikidata subclass list file (${subclass_list}) does not exist! Maybe you forgot to enter argument with wikidata subclass list file path?"
  fi
  echo " See '--help' for usage information!"
  exit 1
fi

tc_customized=false
if [ -n "${4}" ]; then
  tc="${4}"
  tc_customized=true
fi
if ! test -f "${tc}"
then
  if test "${tc_customized}" = true
  then
    echo -n "Wrong path to wikidata transitive closure!"
  else
    echo -n "Default wikidata transitive closure file (${tc}) does not exist! Maybe you forgot to enter argument with path of wikidata transitive closure file path?"
  fi
  echo " See '--help' for usage information!"
  exit 1
fi

if [ -n "${5}" ]; then
  if [ -d "${5}" ]; then
    project_folder="${5}"
  else
    echo "Wrong path to project folder! See '--help' for usage information!"
    exit 1
  fi
fi

# get subclass list
awk -v class="${1}" -F'\t' 'BEGIN{ print class } { if($1==class) print $2 }' "${subclass_list}" | sort | uniq > "$1.subclass_list"

# split the subclass list
prefix="/tmp/${USER}/types/parts/${1}.subclass_list.part"
mkdir -p "/tmp/${USER}/types/parts"
split -n l/$(cat $host_list | wc -l) -d "${1}.subclass_list" "${prefix}"

# distribute parts
val=0
for host in $(cat ${host_list}); do
  # create tmp folders
  ssh "${host}" bash -s "${1}" << 'END'
  if [ -d "/tmp/$USER/types/${1}" ]; then
    rm -rf "/tmp/$USER/types/${1}"
  fi
  mkdir -p "/tmp/$USER/types/${1}/tcs"
END
  # copy part
  printf -v fname "${prefix}%02d" $val
  rsync "${fname}" "${host}:/tmp/$USER/types/${1}/"
  # increase part value
  val="$((val + 1))"
done

# distribute tc
for host in $(cat ${host_list}); do
  rsync "${tc}" "${host}:/tmp/${USER}/types/"
done

# generate transitive closure for each subclass
parallel-ssh -h "${host_list}" -p 100 -t 0 -i \
"
cat /tmp/${USER}/types/${1}/${1}.subclass_list.part?? | parallel -j 6\
  \"awk -v class={} -F'\t' '{ if(\\\$1==class) print \\\$2 }' /tmp/${USER}/types/tc.tsv | sort | uniq > /tmp/${USER}/types/${1}/tcs/{}.tc\"
"

# collect generated transitive closures of subclasses
if [ -d "/tmp/${USER}/types/result/${1}" ]; then
  rm -rf "/tmp/${USER}/types/result/${1}"
fi
mkdir -p "/tmp/${USER}/types/result/${1}"
for host in $(cat ${host_list}); do
  rsync -r "${host}:/tmp/${USER}/types/${1}/tcs/" "/tmp/${USER}/types/result/${1}/"
done

# concatenate transitive closures and count occurrences

# cant be used because of maximum number of arguments is typically lower than number of files - see lines below
#sort -m /tmp/"$USER"/types/result/"$1"/* | uniq -c | awk '{ print $1"\t"$2 }' | sort -r -n -k 1 -k 2 > "/tmp/$USER/types/result/$1/tcs.all"

# clear the concatenation file
if [ -f "/tmp/${USER}/types/result/${1}.all" ]; then
  rm "/tmp/${USER}/types/result/${1}.all"
fi

# concatenate files to one (workaround too many arguments error)
for f in $(ls "/tmp/${USER}/types/result/${1}/"); do
  cat "/tmp/${USER}/types/result/${1}/${f}" >> "/tmp/${USER}/types/result/${1}.all"
done

# sort file
sort "/tmp/${USER}/types/result/${1}.all" | uniq -c | awk '{ print $1"\t"$2 }' | sort -r -n -k 1 -k 2 > "/tmp/${USER}/types/result/${1}/tcs.all"

# substitute names of classes for easier reading
awk -F'\t' '{ print $1"\t"$2"\t"$2}' "/tmp/${USER}/types/result/${1}/tcs.all" > "/tmp/${USER}/types/result/${1}/tcs.all.tmp"
python3 "${substitute_names_script}" -e 0 1 -d "${2}" -f "/tmp/${USER}/types/result/${1}/tcs.all.tmp" -o "/tmp/${USER}/types/result/${1}/tcs.all.names.tmp"
sort -r -n -k 1 -k 2 -k 3 "/tmp/${USER}/types/result/${1}/tcs.all.names.tmp" > "${1}.tcs.all.names"


# filtering out classes that are not subclasses of the top_class
awk -F'\t' 'NR==FNR{ classes[$1]++; next } (classes[$2]){ print }' "${1}.subclass_list" "${1}.tcs.all.names" > "${1}.subclass_tcs.names"

exit

# clean up
rm "${1}.subclass_list" "${1}.tcs.all.names"
for host in $(cat "${host_list}"); do
  ssh "${host}" bash -s "${1}" << 'END'
  if [ -d "/tmp/${USER}" ] && [ -d "/tmp/${USER}/types" ]; then
    if [ -d "/tmp/${USER}/types/${1}" ]; then
      rm -rf "/tmp/${USER}/types/${1}"
    fi
    if [ -d "/tmp/${USER}/types/result" ] && [ -d "/tmp/${USER}/types/result/${1}" ]; then
      rm -rf "/tmp/${USER}/types/result/${1}"
    fi
    if [ -z "$(ls "/tmp/${USER}/types/result")" ]; then
      rmdir "/tmp/${USER}/types/result"
    fi
    if [ -z "$(ls "/tmp/${USER}/types")" ]; then
      rmdir "/tmp/${USER}/types"
    fi
    if [ -z "$(ls "/tmp/${USER}")" ]; then
      rmdir "/tmp/${USER}"
    fi
  fi
END
done
