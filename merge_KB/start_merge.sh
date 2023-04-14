#!/bin/sh

# file: start_merge.sh
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: René Rešetár (xreset00@stud.fit.vutbr.cz)
# description: merges entity_kb_czech9 and wikidata2 KB

# constants
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
wikidata2_path="$(echo "$project_folder" | xargs -I{} dirname {})"
entity_kb_czech9=/mnt/minerva1/nlp/projects/entity_kb_czech9
kb_compare="$project_folder"/kb_tools/kb_compare.py

# args
list_dumps=false
print_help=false
dump_name=''
lang='cs'
tag='default'
unknown=''

. "${wikidata2_path}/wikidata_lib.sh"

echo "Script \"${0}\" called with params: ${@}"

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
				echo "Dump name missing"'!' >&2
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
				echo "Specify the language"'!'
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
			lang="$2"
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

# help
if $print_help; then
	echo "Usage:"
	echo "  sh start_merge.sh [--dump DUMP_NAME] [--lang LANGUAGE] [--tag TAG]"
	echo "Example:"
	echo "  sh start_merge.sh --dump=wikidata-20210301-all.json"
	echo "Arguments:"
	echo "  --dump|-d  Name of dump to merge. Dump name is name of folder in"
	echo "             `getProjectOutRootDir "${wikidata2_path}"`"
	echo "             Default dump is the latest one."
	echo "  --lang|-g  Language of the merged kb (default: \"${lang}\")."
	echo "  --list|-l  List available dumps."
	echo "  --tag|-t   Tag output directory which allows to distinguish"
  echo "             outputs in case of multiple processing same dump"
  echo "             and same language (default: \"${tag}\")."
	echo "  --help|-h  Print help."
	echo "Description:"
	echo "  Merges data from wikidata2 and entity_kb_czech9 projects."
	exit 0
fi

wikidata_out_rootdir=`getProjectOutRootDir "${wikidata2_path}"`

# list dump names
if $list_dumps; then
	echo "Available dumps:"
	for f in $(ls "$wikidata_out_rootdir/");
	do
		echo "$f"
	done
	exit 0
fi

# if no dump is specified - use lates one (last in list)
if [ -z "$dump_name" ]; then
	dump_name="$(sh "$0" --list | tail -n1)"
fi

wikidata_out_dir=`getProjectOutBaseDir "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}"`
# pring language warning
if [ "$lang" != 'cs' ]; then
	echo "Selected language is ${lang}!" >&2
	echo 'This language might not be supported by all merged KBs!' >&2
fi

[ -d "${wikidata_out_dir}" ] || { echo "Dump \"${dump_name}\" not available for language \"${lang}\" and tag \"${tag}\"!" >&2; exit 1; }

wikidata_person=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "person"`
wikidata_arist=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "artist"`
wikidata_event=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "event"`
wikidata_organization=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "organization"`

# unmerged data
wikidata_groups=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "group"`
wikidata_geographical=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "geographical"`
wikidata_artwork=`getWikidataFilePathForType "${dump_name}" "${lang}" "${tag}" "${wikidata2_path}" "artwork"`

[ -f "$wikidata_person" ] || { echo "No data for selected language!" >&2; exit 1; }

entity_kb_czech9_artist="$entity_kb_czech9"/final/vizual_umelci
entity_kb_czech9_event="$entity_kb_czech9"/final/udalosti
entity_kb_czech9_organization="$entity_kb_czech9"/final/organizace

for t in artist event organization; do
	if [ ! -f "$(eval echo "\$entity_kb_czech9_$t")" ]; then
		eval echo "File \$entity_kb_czech9_$t not found"'!'
		exit 1
	fi
done

tmp_dir="${project_folder}/tmp/${dump_name}/${lang}"
output_dir="${project_folder}/output/${dump_name}/${lang}"

# setup
[ -d "${tmp_dir}" ] || mkdir -p "${tmp_dir}" # create temporary working folder
[ -d "${output_dir}" ] || mkdir -p "${output_dir}" # create output folder

mkdir "${tmp_dir}/artists/"
mkdir "${tmp_dir}/organizations/"
mkdir "${tmp_dir}/events/"

# entity_kb_czech9
cp "$entity_kb_czech9_artist" "${tmp_dir}/artists/ENTITY_KB_CZECH9"
cp "$entity_kb_czech9_event" "${tmp_dir}/events/ENTITY_KB_CZECH9"
cp "$entity_kb_czech9_organization" "${tmp_dir}/organizations/ENTITY_KB_CZECH9"
# wikidata2
# remove the leading type specific prefix, for compatibility with entity_kb_czech9
cp "$wikidata_person" "${tmp_dir}/artists/WIKIDATA2_PERSONS_ALL"
cp "$wikidata_arist" "${tmp_dir}/artists/WIKIDATA2"
cp "$wikidata_organization" "${tmp_dir}/organizations/WIKIDATA2"
cp "$wikidata_event" "${tmp_dir}/events/WIKIDATA2"

# copy unmerged files
cp "$wikidata_groups" "${output_dir}/groups_wikidata2.tsv"
cp "$wikidata_geographical" "${output_dir}/geographical_wikidata2.tsv"
cp "$wikidata_artwork" "${output_dir}/artwork_wikidata2.tsv"

# start merge
cf="$pwd" # save location
tmp_artists_dir="${tmp_dir}/artists"
cd "$project_folder"/artists/
# select artists by id from wikidata2 persons
awk -F'\t' 'NR==FNR{ id[$1]++; next } (id[$1]){ print }' "${tmp_artists_dir}/ENTITY_KB_CZECH9" "${tmp_artists_dir}/WIKIDATA2_PERSONS_ALL" > "${tmp_artists_dir}/WIKIDATA2_PERSONS"
# merge wikidata2 persons and entity_kb_czech9 artists
python3 "$kb_compare" \
	--first "${tmp_artists_dir}/WIKIDATA2_PERSONS" \
	--second "${tmp_artists_dir}/ENTITY_KB_CZECH9" \
	--first_fields WIKIDATA2_PERSONS.fields \
	--second_fields ENTITY_KB_CZECH9.fields \
	--rel_conf wikidata2_persons_entity_kb_rel.conf \
	--output_conf wikidata2_persons_output.conf \
	--other_output_conf wikidata2_persons_other_output.conf \
	--output "${tmp_artists_dir}/PERSONS_ARTISTS_MERGED" \
	--treshold 100

# merge wikidata2 artists and entity_kb_czech9 artists
python3 "$kb_compare" \
      --first "${tmp_artists_dir}/WIKIDATA2" \
      --second "${tmp_artists_dir}/PERSONS_ARTISTS_MERGED" \
      --first_fields WIKIDATA2.fields \
      --second_fields PERSONS_ARTISTS_MERGED.fields \
      --rel_conf wikidata2_entity_kb_rel.conf \
      --output_conf wikidata2_output.conf \
      --other_output_conf wikidata2_other_output.conf \
      --output "${output_dir}/artists_merged.tsv" \
      --treshold 100

# Subtract all artists from persons KB
awk -F'\t' 'NR==FNR{ id[$1]++; next }; (!(id[$1])){ print }' "${output_dir}/artists_merged.tsv" "${tmp_artists_dir}/WIKIDATA2_PERSONS_ALL" > "${output_dir}/persons_unmerged.tsv"

rm -r "${tmp_artists_dir}"

# merge
for type in events organizations; do
	cd "$project_folder/$type/"
	tmp_type_dir="${tmp_dir}/${type}/"
	echo "Starting to merge $type KB"
	python3 "$kb_compare" \
	      --first "${tmp_type_dir}/WIKIDATA2" \
	      --second "${tmp_type_dir}/ENTITY_KB_CZECH9" \
	      --first_fields WIKIDATA2.fields \
	      --second_fields ENTITY_KB_CZECH9.fields \
	      --rel_conf wikidata2_entity_kb_rel.conf \
	      --output_conf wikidata2_output.conf \
	      --other_output_conf wikidata2_other_output.conf \
	      --output "${output_dir}/${type}_merged.tsv" \
	      --treshold 100
	rm -r "${tmp_type_dir}"
done

# merge files into KB
sh "$project_folder"/mkkb.sh --dump=${dump_name} --lang=${lang}

cd "$cf" # restore location

