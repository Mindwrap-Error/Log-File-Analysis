#!/bin/bash

if [ $# -ne 1 ]; then
    exit 1
fi

LOG_FILE="$1"

if sed -n '/^\[[A-Z][a-z][a-z] [A-Z][a-z][a-z] [0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9] [0-9]\{4\}\] \[[a-z]\+\]/!q1' "$LOG_FILE"; then
    exit 0
else
    exit 1
fi
