# Changelog

## v0.3.0 - 27.03.2024

New release that adds handling for parsing errors. It also drops python 3.7 and 3.8 support.

- Change `on_missing` option in the `priority_filter` from "error" to "raise".
  ([#79](https://github.com/mathause/filefinder/pull/79))
- Drop support for python 3.7 and 3.8 ([#80](https://github.com/mathause/filefinder/pull/80))
- Allow passing scalar numbers to `find_paths` and `find_files` ([#58](https://github.com/mathause/filefinder/issues/58)).
- Show duplicates for non-unique queries
    ([#73](https://github.com/mathause/filefinder/pull/73))
- Add options on how to handle parsing errors
    ([#75](https://github.com/mathause/filefinder/pull/75))

## v0.2.0 - 23.05.2023

New release that allows to specify a format spec which allows parsing more complex file name structures. It also drops python 3.6 support and modernizes the build system.

- Allow passing format spec to the captured names to allow more precise name matching
  ([#57](https://github.com/mathause/filefinder/pull/57)).
- Add tests for the cmip functionality and fix issue with `filefinder.cmip.ensure_unique_grid`
  ([#35](https://github.com/mathause/filefinder/pull/35)).
- Removed support for python 3.6.
- Explicitly test python 3.11.

## v0.1.0 - 05.08.2022

- First version released based on the code developed for my IPCC AR6 analyses and including some additions (e.g. `priority_filter`, preferring `kwargs` over keys passed via a dictionary, more complete tests).
