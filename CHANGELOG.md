# Changelog

## v0.4.0 - unreleased

- Added two methods to find _exactly_ one file or path (and raise an error otherwise):
  `FileFinder.find_single_file` and `FileFinder.find_single_path`
  ([#101](https://github.com/mathause/filefinder/pull/101)).
- Raise an error if an unnamed placeholder (e.g., `"{}"`) is passed
  ([#110](https://github.com/mathause/filefinder/pull/110))
- The `FileFinder.find_files` arguments `on_parse_error` and `_allow_empty` can no
  longer be passed by position ([#99](https://github.com/mathause/filefinder/pull/99)).
- `FileFinder` now raises an error if an invalid `"{placeholder}"` is used
   ([#99](https://github.com/mathause/filefinder/pull/99)).
- An empty `FileContainer` is returned instead of an empty list when no files/ paths are
  found ([#114](https://github.com/mathause/filefinder/pull/114))

- Changes to `FileContainer`:

  - Renamed the `"filename"` column to `"path"` and made it a `pd.Index`, thus removing
    this column from the underlying `DataFrame` ([#113](https://github.com/mathause/filefinder/pull/113)).
  - Deprecated `combine_by_key` ([#115](https://github.com/mathause/filefinder/pull/115)).
  - Added the number of paths to the repr ([#116](https://github.com/mathause/filefinder/pull/116)).

- Explicitly test on python 3.13 ([#103](https://github.com/mathause/filefinder/pull/103)).
- Drop support for python 3.9 ([#102](https://github.com/mathause/filefinder/pull/102)).

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
