#!/bin/bash

input_file="$1"
output_file="$2"
month="$3"
day="$4"
hour="$5"
level="$6"
eventid="$7"

awk_script='
BEGIN { 
    FS = OFS = "," 
}
{
    if (NR == 1) {
        print $0
        next
    }

    for (i=1; i<=NF; i++) {
        orig[i] = $i
    }

    # Remove quotes for comparison
    for (i=1; i<=NF; i++) {
        gsub(/^["\047]|["\047]$/, "", $i)
    }

    match_found = 1

    if (month != "" && $1 != month) match_found = 0
    if (day != "" && $2 != day) match_found = 0
    if (hour != "" && substr($3, 1, length(hour)) != hour) match_found = 0
    if (level != "" && tolower($5) != tolower(level)) match_found = 0
    if (eventid != "" && $7 != eventid) match_found = 0

    if (match_found) {
        # Print original fields with proper CSV formatting
        for (i=1; i<=NF; i++) {
            printf "%s%s", orig[i], (i==NF ? "\n" : OFS)
        }
    }
}' 

awk -v month="$month" \
    -v day="$day" \
    -v hour="$hour" \
    -v level="$level" \
    -v eventid="$eventid" \
    "$awk_script" "$input_file" > "$output_file"