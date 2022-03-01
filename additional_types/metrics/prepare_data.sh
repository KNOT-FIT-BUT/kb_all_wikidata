#!/bin/bash

set -o pipefail

#cp -v ../HEAD-KB HEAD-KB && #Copies ../HEAD-KB to HEAD-KB
# my code (xreset)
cp -v ../final/udalosti udalosti && # pridaj /final pre vsetky
cp -v ../final/organizace organizace &&
cp -v ../final/vizual_umelci vizual_umelci &&
touch KBstatsMetrics.all-appendix
touch wiki_stats &&
rm kb_cs &&
touch kb_cs &&
cat udalosti >> kb_cs &&
sed -i '$G' kb_cs &&      #Gets us to the end of the file and puts empty line
cat organizace >> kb_cs &&
sed -i '$G' kb_cs &&      #Gets us to the end of the file and puts empty line
cat vizual_umelci >> kb_cs &&
sed -i '/^$/d' kb_cs &&   #Deletes empty lines

sed -i '$G' HEAD-KB &&      #Gets us to the end of the file and puts empty line
python2 create_head_kb.py
sed -i '/^$/d' HEAD-KB &&   #Deletes empty lines
sed -i '$G' HEAD-KB &&      #Gets us to the end of the file and puts empty line
date +%s > VERSION &&       #Writes date as version to VERSION
python3 prepare_kb_to_stats_and_metrics.py < kb_cs | python3 check_columns_in_kb.py --cat | python3 wiki_stats_to_KB.py > KBstats.all &&
python3 metrics_to_KB.py -k KBstats.all | sed '/^\s*$/d' > KBstatsMetrics.all &&
cat KBstatsMetrics.all-appendix >> KBstatsMetrics.all &&
echo -n "VERSION=" | cat - VERSION HEAD-KB KBstatsMetrics.all > KB-HEAD.all
exit_status=$?

(( exit_status == 0 )) && rm KBstats.all wiki_stats

exit $exit_status

