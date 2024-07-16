#!/bin/bash
# Bash script that listens to a stream, redirects the video to vedal987_scrutinize.py, and audio to pleep-search
# Definitely not scuffed

STREAMLINK_VIDEO_AND_QUALITY="https://www.twitch.tv/vedal987 best"
# STREAMLINK_VIDEO_AND_QUALITY="https://www.twitch.tv/videos/2199274029 source"
TEMP_RESULT_JSON="temp_result.json"
TEMP_RESULT_WAV="for_pleep.wav"
REQUIRED_PROGRAMS="streamlink ffmpeg python3 jq"
REQUIRED_FILES="pleep-search out.bin"
AUDIO_THRESHOLD=0.8

trap quit_program INT

quit_program() {
    echo "Quitting..."
    # rm -f $TEMP_RESULT_JSON
    # rm -f $TEMP_RESULT_WAV
    exit 0
}

for program in $REQUIRED_PROGRAMS; do
    if ! [ -x "$(command -v $program)" ];
    then
        echo "Error: $program is not installed."
        exit 1
    fi
done

for file in $REQUIRED_FILES; do
    if ! [ -f $file ];
    then
        echo "Error: $file is not found."
        exit 1
    fi
done

STREAMLINK_ARGS=""
if [ -n "$TWITCH_OAUTH" ]; then
  STREAMLINK_ARGS+="--twitch-oauth-token $TWITCH_OAUTH"
fi
STREAMLINK_ARGS="--stdout $STREAMLINK_VIDEO_AND_QUALITY"

streamlink $STREAMLINK_ARGS | ffmpeg -i - -map 0:a -ar 44100 -ac 1 -f wav $TEMP_RESULT_WAV -map 0:v -c:v copy -f matroska - | python3 vedal987_scrutinize.py > $TEMP_RESULT_JSON

AUDIO_JSON=$(RUST_LOG=info ./pleep-search --json out.bin $TEMP_RESULT_WAV | python3 audio_threshold_parser.py)

NEURO_JSON=$(jq '.[] | select(.streamer=="neuro")' $TEMP_RESULT_JSON)
EVIL_JSON=$(jq '.[] | select(.streamer=="evil")' $TEMP_RESULT_JSON)

if [ -z "$NEURO_JSON" ]; then
    echo "Skipping Neuro result"
else
    echo $(echo -n $NEURO_JSON | jq '.result') > neuro.txt
    echo -n $AUDIO_JSON >> neuro.txt
fi

if [ -z "$EVIL_JSON" ]; then
    echo "Skipping Evil result"
else
    echo $(echo -n $EVIL_JSON | jq '.result') > evil.txt
    echo -n $AUDIO_JSON >> evil.txt
fi

quit_program
