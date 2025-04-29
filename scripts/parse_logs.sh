    #!/bin/bash

    if [ $# -ne 2 ]; then
        echo "Usage: $0 <input_log_file> <output_csv_file>" >&2
        exit 1
    fi

    LOG_FILE="$1"
    OUT_FILE="$2"
    NEW_FILE=temp.csv
    (tr -d "\r" < "$LOG_FILE") > "$NEW_FILE"
    mkdir -p "$(dirname "$OUT_FILE")"

    echo "Month,Day,Timestamp,Year,Level,Message,EventId" > "$OUT_FILE"
    while IFS= read -r line; do
        if [[ "$line" =~ \[([A-Za-z]{3})\ ([A-Za-z]{3})\ ([0-9]{2})\ ([0-9]{2}:[0-9]{2}:[0-9]{2})\ ([0-9]{4})\]\ \[([a-z]+)\]\ (.*) ]]; then
            DayOfWeek="${BASH_REMATCH[1]}"
            Month="${BASH_REMATCH[2]}"
            Day="${BASH_REMATCH[3]}"
            Timestamp="${BASH_REMATCH[4]}"
            Year="${BASH_REMATCH[5]}"
            Level="${BASH_REMATCH[6]}"
            Message="${BASH_REMATCH[7]}"

            EventId="Unknown"
            case "$Message" in
                "jk2_init() Found child "*) EventId="E1" ;;
                "workerEnv.init() ok "*) EventId="E2" ;;
                "mod_jk child workerEnv in error state "*) EventId="E3" ;;
                "[client "*"] Directory index forbidden by rule: "*) EventId="E4" ;;
                "jk2_init() Can't find child "*) EventId="E5" ;;
                "mod_jk child init "*) EventId="E6" ;;
            esac

            EscapedMessage=$(echo "$Message" | sed 's/"/""/g')
            echo "$Month,$Day,$Timestamp,$Year,$Level,\"$EscapedMessage\",$EventId" >> "$OUT_FILE"
        fi
    done < "$NEW_FILE"

    rm temp.csv

    exit 0