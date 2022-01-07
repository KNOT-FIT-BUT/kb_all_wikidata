#!/bin/sh

# file: start_merge.sh
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# author: René Rešetár (xreset00@stud.fit.vutbr.cz)
# description: merges entity_kb_czech9 and wikidata2 KB

# constants
project_folder="$(readlink -f $0 | xargs -I{} dirname {})"
wikidata2="$(echo "$project_folder" | xargs -I{} dirname {})"
#entity_kb_czech9=/mnt/minerva1/nlp/projects/entity_kb_czech9
kb_compare="$project_folder"/kb_tools/kb_compare.py

# list dump names
if [ "$1" = "--list" ]; then
	echo "Available dumps:"
	for f in $(ls "$wikidata2"/tsv_extracted_from_wikidata/);
	do
		echo "$f"
	done
	exit 0
fi

# help
if [ "$1" = "--help" ]; then
	echo "Usage:"
	echo "  sh start_merge.sh [ wikidata_dump_name ]"
	echo "Example:"
	echo "  sh start_merge.sh wikidata-20210301-all.json"
	echo "Description:"
	echo "  Dump name is name of folder in $wikidata2/tsv_extracted_from_wikidata/"
	echo "  When '--list' argument is used list of available dumps is printed."
	echo "  If no arguments are used latest available dump is used."
	exit 0
fi

# if no dump is specified - use lates one (last in list)
if [ -z "$1" ]; then
	dump_name="$(sh "$0" --list | tail -n1)"
else # dump name is passed in
	dump_name="$1"
fi

[ -d "$wikidata2"/tsv_extracted_from_wikidata/"$dump_name" ] || { echo "Dump $dump_name not available"'!'; exit 1; }

wikidata_person="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-person.tsv
wikidata_arist="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-artist.tsv
wikidata_event="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-event.tsv
wikidata_organization="$wikidata2"/tsv_extracted_from_wikidata/"$dump_name"/"`echo "$dump_name" | sed 's/-all.json//'`"-cs-organization.tsv

# TODO changed paths - check if it works with them
entity_kb_czech9_artist="$wikidata2"/additional_types/final/vizual_umelci
entity_kb_czech9_event="$wikidata2"/additional_types/final/udalosti
entity_kb_czech9_organization="$wikidata2"/additional_types/final/organizace

for t in artist event organization; do
	if [ ! -f "$(eval echo "\$entity_kb_czech9_$t")" ]; then
		eval echo "File \$entity_kb_czech9_$t not found"'!'
		exit 1
	fi
done

# setup
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

# start merge
cf="$pwd" # save location
[ -d "$project_folder"/output ] || mkdir "$project_folder"/output  # create output folder
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
sh "$project_folder"/mkkb.sh "$dump_name"

cd "$cf" # restore location

