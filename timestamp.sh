#!/bin/sh

# file: timestamp.sh
# description: Functions for working with timestamps in bash
# project: wikidata2
# author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)

# usage example:
# t_start=`timestamp`
# some_long_running_function
# t_end=`timestamp`
# total_time="`timestamp_diff "$t_start" "$t_end"`"
# echo "Total time elapsed: `show_time "$total_time"`"

# Displays time in format - days hours minutes seconds
# output example: 1d 5h 17m 15s
# param $1 time in seconds to parse
show_time() {
	t=$1
	seconds=0
	minutes=0
	hours=0
	days=0
	# get seconds
	if [ "$t" -ge 59 ]; then
		seconds="`echo "$t % 60" | bc`"
		t="`echo "$t / 60" | bc`"
		# get minutes
		if [ "$t" -ge 59 ]; then
			minutes="`echo "$t % 60" | bc`"
			t="`echo "$t / 60" | bc`"
			# get hours and days
			if [ "$t" -ge 23 ]; then
				hours="`echo "$t % 24" | bc`"
				days="`echo "$t / 24" | bc`"
			else
				# get hours if less than 1 day
				hours="$t"
			fi
		else
			# get minutes if less than 1 hour
			minutes="$t"
		fi
	else
		# get seconds if less than 1 second
		seconds="$t"
	fi
	echo "$days"d "$hours"h "$minutes"m "$seconds"s
}

# get current timestamp in unix time
timestamp() {
  echo "`date "+%s"`"
}

# get time between timestamps
# param $1 first timestamp
# param $2 second timestamp
timestamp_diff() {
  echo "`echo "$2 - $1" | bc`"
}
