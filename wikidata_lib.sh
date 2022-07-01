#!/bin/bash
# Author: Tomáš Volf, ivolf@fit.vutbr.cz

FILE_MASTER_IPS=.master_ip_addresses.cfg
export DIRNAME_CLASSES=classes
export DIRNAME_DICTS=dicts
export DIRNAME_EXPANDED_INSTANCES=expanded_instances_kb
export DIRNAME_INSTANCES=instances
export DIRNAME_LOCAL_PROCESSING=local_partial_data
export DIRNAME_TYPES_DATA=types_data


getProcessingBaseDir() {
  dump_name="${1}"
  lang="${2}"
  tag="${3}"

  echo -n "/tmp/${USER}/${dump_name}/${lang}/${tag}"
}


# $1 = dump_name; $2 = $lang; $3 = tag
getMasterClassesDir() {
  basedir=`getProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_CLASSES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getMasterExpandedInstancesDir() {
  basedir=`getProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_EXPANDED_INSTANCES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getMasterInstancesDir() {
  basedir=`getProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_INSTANCES}"
}


# $1 = dump_name; $2 = $lang; $3 = tag
getLocalProcessingBaseDir() {
  basedir=`getProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_LOCAL_PROCESSING}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getLocalProcessingClassesDir() {
  basedir=`getLocalProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_CLASSES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getLocalProcessingDictsDir() {
  basedir=`getLocalProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_DICTS}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getLocalProcessingExpandedInstancesDir() {
  basedir=`getLocalProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_EXPANDED_INSTANCES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getLocalProcessingInstancesDir() {
  basedir=`getLocalProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_INSTANCES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag
getLocalProcessingTypesDataDir() {
  basedir=`getLocalProcessingBaseDir "${1}" "${2}" "${3}"`
  echo -n "${basedir}/${DIRNAME_TYPES_DATA}"
}


getProjectTempBaseDir() {
  dump_name="${1}"
  lang="${2}"
  tag="${3}"
  project_dir="${4}"

  echo -n "${project_dir}/tmp_extracted_data/${dump_name}/${lang}/${tag}"
}

# $1 = dump_name; $2 = $lang; $3 = tag, $4 = project_dir
getProjectTempClassesDir() {
  basedir=`getProjectTempBaseDir "${1}" "${2}" "${3}" "${4}"`
  echo -n "${basedir}/${DIRNAME_CLASSES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag, $4 = project_dir
getProjectTempDictsDir() {
  basedir=`getProjectTempBaseDir "${1}" "${2}" "${3}" "${4}"`
  echo -n "${basedir}/${DIRNAME_DICTS}"
}

# $1 = dump_name; $2 = $lang; $3 = tag, $4 = project_dir
getProjectTempExpandedInstancesDir() {
  basedir=`getProjectTempBaseDir "${1}" "${2}" "${3}" "${4}"`
  echo -n "${basedir}/${DIRNAME_EXPANDED_INSTANCES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag, $4 = project_dir
getProjectTempInstancesDir() {
  basedir=`getProjectTempBaseDir "${1}" "${2}" "${3}" "${4}"`
  echo -n "${basedir}/${DIRNAME_INSTANCES}"
}

# $1 = dump_name; $2 = $lang; $3 = tag, $4 = project_dir
getProjectTempTypesDataDir() {
  basedir=`getProjectTempBaseDir "${1}" "${2}" "${3}" "${4}"`
  echo -n "${basedir}/${DIRNAME_TYPES_DATA}"
}

getProjectOutRootDir() {
  project_dir="${1}"
  echo -n "${project_dir}/tsv_extracted_from_wikidata"
}

getProjectOutBaseDir() {
  dump_name="${1}"
  lang="${2}"
  tag="${3}"
  project_dir="${4}"
  root_dir=`getProjectOutRootDir "${project_dir}"`

  echo -n "${root_dir}/${dump_name}/${lang}/${tag}"
}


getWikidataFilePathForType() {
  dump_name="${1}"
  lang="${2}"
  type="${5}"

  basedir=`getProjectOutBaseDir "${dump_name}" "${lang}" "${3}" "${4}"`

  echo -n "${basedir}/`echo "${dump_name}" | sed 's/-all.json//'`-${lang}-${type}.tsv"
}

# $1 = dir to recreate
recreate_dir() {
  if test -d "${1}"
  then
    rm -r "${1}"
  fi
  mkdir -p "${1}"
}