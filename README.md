# ARG Monitoring

A semi-properly-not-really tool that checks the integrity of the ARG.

This repository runs scripts everyday at 00:00 GMT+00:00 to do the
following:
- Check the integrity of the YouTube videos
- Check the integrity of metadata (e.g. number of video uploads,
  number of soundcloud tracks, etc)

It makes use of GitHub Actions cache to store the "known" states. The
output of this repository is a RSS feed, which is pushed to this very
same repository on the `feed`
branch. [Here](https://raw.githubusercontent.com/neuro-arg/arg-monitoring/publish/atom.xml)
is a handy link; add it to your RSS reader.

(If you want the "live" JSON, use [this
link](https://raw.githubusercontent.com/neuro-arg/arg-monitoring/publish/cache.json))

## Twitch Intro Sequence

As part of monitoring, a intro sequence detection has been
implemented. This requires priming; to do so, navigate to `feed-generator/src/sources/twitch-source`.

It involves the following steps:

1. Create a bunch of reference squares using `frameviewer.py` (this is
   a little slow). (Parameters: input video, and output directory,
   either `neuro` or `evil`).
2. Analyze the SSIM mean and confidence interval between many videos
   using `analyze.py`. (Parameters: source directory, either `neuro`
   or `evil`, detection square, either `detectors/neuro_detector.png`
   or `detectors/evil_detector.png`. Modify the script's
   `YOUTUBE_VIDEOS` list to check it against multiple videos.
3. Rename the output (`result.npz`) to either `neuro.npz` or
   `evil.npz`. This is the thresholds file.
4. Run `scrutinize.py` to check the threshold against a particular
   video.

If the above steps are successful, the `neuro/`, `evil/` directories,
and `neruo.npz`, `evil.npz` files can be committed to be used as
threshold values for the upcoming stream.

There is also a Twitch Stream trigger, which relies on:

- A valid Twitch Client ID and Secret
- A valid GitHub Personal Access Token
- A valid callback URL (either `ngrok` or equivalent)

Run the file `hook_listener.py` to create the first skeleton for a
config file, which will be `secrets.ini`.

### Audio Monitoring

Audio monitoring is achieved with @owobred's
[pleep](https://github.com/owobred/pleep) program.

## Contributing

The repository is split into two parts: `feed-generator` and `web`.

### Feed Generator

The Feed Generator is written in Python.

``` text
cd feed-generator/
pip install -e . // or poetry install
```

If you hate red squiggly lines, run this as well:

``` text
mypy --install-types
```

### Web

The Web interface is written both in JavaScript and Rust (because I
wanted to).

Install pre-requisites:

``` text
cd web/
npm install -g wasm-pack
cd www/
npm install
cd -
```

Build the project:

``` text
wasm-pack build
```

To serve the development HTTP server, try:

``` text
cd www/
npm start
```
