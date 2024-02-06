# Changelog

## v0.3.0 - unreleased

- Allow passing scalar numbers to `find_paths` and `find_files` ([#58](https://github.com/mathause/filefinder/issues/58)).

## v0.2.0 - 23.05.2023

New release that allows to specify a format spec which allows parsing more complex file name structures. It also drops python 3.6 support and modernizes the build system.

- Allow passing format spec to the captured names to allow more precise name matching
  ([#57](https://github.com/mathause/filefinder/pull/57)).
- Add tests for the cmip functionality and fix issue with `filefinder.cmip.ensure_unique_grid`
  ([#35](https://github.com/mathause/filefinder/pull/35)).
- Removed support for python 3.6.
- Explicitely test python 3.11.

## v0.1.0 - 05.08.2022

- First version released based on the code developped for my IPCC AR6 analyses and including some additions (e.g. `priority_filter`, prefering `kwargs` over keys passed via a dictionary, more complete tests).
