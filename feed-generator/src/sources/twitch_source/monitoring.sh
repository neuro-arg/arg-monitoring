#!/bin/bash
# Bash script that listens to a stream, redirects the video to vedal987_scrutinize.py, and audio to pleep-search
# Definitely not scuffed
# Also supports JP and Bilibili through extremely unscuffed means

TEMP_RESULT_JSON="temp_result.json"
TEMP_RESULT_WAV="for_pleep.wav"
REQUIRED_PROGRAMS="streamlink ffmpeg python3 jq"
REQUIRED_FILES="pleep-search out.bin"
STREAM_TYPE="twitch"
AUDIO_THRESHOLD=0.8

case $MONITOR_SWITCH in
    JP)
        echo "JP stream"
        STREAMLINK_VIDEO_AND_QUALITY="https://www.twitch.tv/vedal987_jp best"
        OUTPUT_NEURO_FILE=neuro_jp.txt
        OUTPUT_EVIL_FILE=evil_jp.txt
        unset BILIBILI_TOKEN
        ;;
    CN)
        echo "CN stream"
        STREAMLINK_VIDEO_AND_QUALITY="https://live.bilibili.com/1852504554 best"
        OUTPUT_NEURO_FILE=neuro_cn.txt
        OUTPUT_EVIL_FILE=evil_cn.txt
        unset TWITCH_OAUTH # i don't want bilibili taking my twitch token thank you
        STREAM_TYPE="bilibili"
        ;;
    *)
        echo "EN stream (default)"
        STREAMLINK_VIDEO_AND_QUALITY="https://www.twitch.tv/vedal987 best"
        # STREAMLINK_VIDEO_AND_QUALITY="https://www.twitch.tv/videos/2218300447 best"
        OUTPUT_NEURO_FILE=neuro.txt
        OUTPUT_EVIL_FILE=evil.txt
        unset BILIBILI_TOKEN
        ;;
esac


trap quit_program INT

quit_program() {
    echo "Quitting..."
    rm -f $TEMP_RESULT_JSON
    rm -f $TEMP_RESULT_WAV
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

# NOTE: I couldn't think of another way to do this without it not
# recognizing "Authorization=OAuth $TWITCH_OAUTH" as one argument
if [ "$STREAM_TYPE" == "twitch" ]; then
    if [ -n "$TWITCH_OAUTH" ]; then
        echo "Have Twitch token, will skip ads"
        streamlink --stdout --hls-live-restart --twitch-low-latency --twitch-api-header "Authorization=OAuth $TWITCH_OAUTH" $STREAMLINK_VIDEO_AND_QUALITY | ffmpeg -i - -map 0:a -ar 44100 -ac 1 -f wav $TEMP_RESULT_WAV -map 0:v -c:v copy -f matroska - | python3 vedal987_scrutinize.py > $TEMP_RESULT_JSON
    else
        echo "No Twitch token, cannot skip ads"
        streamlink --stdout --hls-live-restart --twitch-low-latency $STREAMLINK_VIDEO_AND_QUALITY | ffmpeg -i - -map 0:a -ar 44100 -ac 1 -f wav $TEMP_RESULT_WAV -map 0:v -c:v copy -f matroska - | python3 vedal987_scrutinize.py > $TEMP_RESULT_JSON
    fi
fi

if [ "$STREAM_TYPE" == "bilibili" ]; then
    if [ -n "$BILIBILI_TOKEN" ]; then
        echo "Have B2 session data. Can get higher quality streams"
        streamlink --stdout --http-cookie SESSDATA=$BILIBILI_TOKEN --hls-live-restart $STREAMLINK_VIDEO_AND_QUALITY | ffmpeg -i - -map 0:a -ar 44100 -ac 1 -f wav $TEMP_RESULT_WAV -map 0:v -c:v copy -f matroska - | python3 vedal987_scrutinize.py > $TEMP_RESULT_JSON
    else
        echo "No B2 session data, stream will be low quality"
        streamlink --stdout --hls-live-restart $STREAMLINK_VIDEO_AND_QUALITY | ffmpeg -i - -map 0:a -ar 44100 -ac 1 -f wav $TEMP_RESULT_WAV -map 0:v -c:v copy -f matroska - | python3 vedal987_scrutinize.py > $TEMP_RESULT_JSON
    fi
fi

AUDIO_JSON=$(RUST_LOG=info ./pleep-search --json out.bin $TEMP_RESULT_WAV | python3 audio_threshold_parser.py)

NEURO_JSON=$(jq '.[] | select(.streamer=="neuro")' $TEMP_RESULT_JSON)
EVIL_JSON=$(jq '.[] | select(.streamer=="evil")' $TEMP_RESULT_JSON)

if [ -z "$NEURO_JSON" ]; then
    echo "Skipping Neuro result"
else
    echo $(echo -n $NEURO_JSON | jq '.result') > $OUTPUT_NEURO_FILE
    echo -n $AUDIO_JSON >> $OUTPUT_NEURO_FILE
fi

if [ -z "$EVIL_JSON" ]; then
    echo "Skipping Evil result"
else
    echo $(echo -n $EVIL_JSON | jq '.result') > $OUTPUT_EVIL_FILE
    echo -n $AUDIO_JSON >> $OUTPUT_EVIL_FILE
fi

quit_program
