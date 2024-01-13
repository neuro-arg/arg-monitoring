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

## Contributing

``` text
pip install -e .
```

If you hate red squiggly lines, run this as well:

``` text
mypy --install-types
```
