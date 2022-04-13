#!/bin/sh

# file: start_merge.sh
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: René Rešetár (xreset00@stud.fit.vutbr.cz)
# description: merges entity_kb_czech9 and wikidata2 KB

# constants
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
wikidata2="$(echo "$project_folder" | xargs -I{} dirname {})"
entity_kb_czech9=/mnt/minerva1/nlp/projects/entity_kb_czech9
kb_compare="$project_folder"/kb_tools/kb_compare.py

# args
list_dumps=false
print_help=false
dump_name=''
lang='cs'
unknown=''

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
		* )
			unknown="$1"
			break
			;;
	esac
done

# help
if $print_help; then
	echo "Usage:"
	echo "  sh start_merge.sh [ --dump DUMP_NAME] [ --lang LANGUAGE ]"
	echo "Example:"
	echo "  sh start_merge.sh --dump=wikidata-20210301-all.json"
	echo "Arguments:"
	echo "  --dump|-d  Name of dump to merge. Dump name is name of folder in"
	echo "             $wikidata2/tsv_extracted_from_wikidata/"
	echo "             Default dump is the latest one."
	echo "  --lang|-g  Language of the merged kb. Default is czech (cs)."
	echo "  --list|-l  List available dumps."
	echo "  --help|-h  Print help."
	echo "Description:"
	echo "  Merges data from wikidata2 and entity_kb_czech9 projects."
	exit 0
fi

# list dump names
if $list_dumps; then
	echo "Available dumps:"
	for f in $(ls "$wikidata2"/tsv_extracted_from_wikidata/);
	do
		echo "$f"
	done
	exit 0
fi

# if no dump is specified - use lates one (last in list)
if [ -z "$dump_name" ]; then
	dump_name="$(sh "$0" --list | tail -n1)"
fi

# pring language warning
if [ "$lang" != 'cs' ]; then
	echo "Selected language is $lang"'!' >&2
	echo 'This language might not be supported by all merged KBs!' >&2
fi

[ -d "$wikidata2"/tsv_extracted_from_wikidata/"$dump_name" ] || { echo "Dump $dump_name not available"'!' >&2; exit 1; }

wikidata_person="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-"$lang"-person.tsv
wikidata_arist="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-"$lang"-artist.tsv
wikidata_event="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-"$lang"-event.tsv
wikidata_organization="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-"$lang"-organization.tsv

# unmerged data
wikidata_groups="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-"$lang"-group.tsv
wikidata_geographical="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-"$lang"-geographical.tsv

[ -f "$wikidata_person" ] || { echo "No data for selected language"'!' >&2; exit 1; }

entity_kb_czech9_artist="$entity_kb_czech9"/final/vizual_umelci
entity_kb_czech9_event="$entity_kb_czech9"/final/udalosti
entity_kb_czech9_organization="$entity_kb_czech9"/final/organizace

for t in artist event organization; do
	if [ ! -f "$(eval echo "\$entity_kb_czech9_$t")" ]; then
		eval echo "File \$entity_kb_czech9_$t not found"'!'
		exit 1
	fi
done

# setup
[ -d "$project_folder"/output ] || mkdir "$project_folder"/output  # create output folder
# entity_kb_czech9
cp "$entity_kb_czech9_artist" "$project_folder"/artists/ENTITY_KB_CZECH9
cp "$entity_kb_czech9_event" "$project_folder"/events/ENTITY_KB_CZECH9
cp "$entity_kb_czech9_organization" "$project_folder"/organizations/ENTITY_KB_CZECH9
# wikidata2
# remove the leading type specific prefix, for compatibility with entity_kb_czech9
sed -f "$project_folder"/remove_prefix.sed "$wikidata_person" > "$project_folder"/artists/WIKIDATA2_PERSONS_ALL
sed -f "$project_folder"/remove_prefix.sed "$wikidata_arist" > "$project_folder"/artists/WIKIDATA2
sed -f "$project_folder"/remove_prefix.sed "$wikidata_organization" > "$project_folder"/organizations/WIKIDATA2
sed -f "$project_folder"/remove_prefix.sed "$wikidata_event" > "$project_folder"/events/WIKIDATA2

# copy unmerged files
sed -f "$project_folder"/remove_prefix.sed "$wikidata_groups" > "$project_folder"/output/groups_wikidata2.tsv
sed -f "$project_folder"/remove_prefix.sed "$wikidata_geographical" > "$project_folder"/output/geographical_wikidata2.tsv

# start merge
cf="$pwd" # save location
cd "$project_folder"/artists/
# select artists by id from wikidata2 persons
awk -F'\t' 'NR==FNR{ id[$1]++; next } (id[$1]){ print }' ENTITY_KB_CZECH9 WIKIDATA2_PERSONS_ALL > WIKIDATA2_PERSONS
# merge wikidata2 persons and entity_kb_czech9 artists
python3 "$kb_compare" \
	--first WIKIDATA2_PERSONS \
	--second ENTITY_KB_CZECH9 \
	--first_fields WIKIDATA2_PERSONS.fields \
	--second_fields ENTITY_KB_CZECH9.fields \
	--rel_conf wikidata2_persons_entity_kb_rel.conf \
	--output_conf wikidata2_persons_output.conf \
	--other_output_conf wikidata2_persons_other_output.conf \
	--output PERSONS_ARTISTS_MERGED \
	--treshold 100

# merge wikidata2 artists and entity_kb_czech9 artists
python3 "$kb_compare" \
      --first WIKIDATA2 \
      --second PERSONS_ARTISTS_MERGED \
      --first_fields WIKIDATA2.fields \
      --second_fields PERSONS_ARTISTS_MERGED.fields \
      --rel_conf wikidata2_entity_kb_rel.conf \
      --output_conf wikidata2_output.conf \
      --other_output_conf wikidata2_other_output.conf \
      --output artists_merged.tsv \
      --treshold 100

# Subtract all artists from persons KB
awk -F'\t' 'NR==FNR{ id[$1]++; next }; (!(id[$1])){ print }' artists_merged.tsv WIKIDATA2_PERSONS_ALL > persons_unmerged.tsv

mv -t "$project_folder"/output/ artists_merged.tsv persons_unmerged.tsv
rm WIKIDATA2_PERSONS ENTITY_KB_CZECH9 PERSONS_ARTISTS_MERGED WIKIDATA2 WIKIDATA2_PERSONS_ALL

# merge
for type in events organizations; do
	cd "$project_folder/$type/"
	echo "Starting to merge $type KB"
	python3 "$kb_compare" \
	      --first WIKIDATA2 \
	      --second ENTITY_KB_CZECH9 \
	      --first_fields WIKIDATA2.fields \
	      --second_fields ENTITY_KB_CZECH9.fields \
	      --rel_conf wikidata2_entity_kb_rel.conf \
	      --output_conf wikidata2_output.conf \
	      --other_output_conf wikidata2_other_output.conf \
	      --output "$type"_merged.tsv \
	      --treshold 100
	mv -t "$project_folder"/output/ "$type"_merged.tsv
	rm WIKIDATA2 ENTITY_KB_CZECH9
done

# merge files into KB
sh "$project_folder"/mkkb.sh --dump=${dump_name} --lang=${lang}

cd "$cf" # restore location

