import copy
import fnmatch
import glob
import logging
import os
import re
import warnings

import numpy as np
import pandas as pd
import parse

from .utils import _find_keys, natural_keys, product_dict, update_dict_with_kwargs

logger = logging.getLogger(__name__)

_FILE_FINDER_REPR = """<FileFinder>
path_pattern: '{path_pattern}'
file_pattern: '{file_pattern}'

keys: {repr_keys}
"""

_RESERVED_PLACEHOLDERS = {"keys", "on_parse_error", "_allow_empty"}


def _assert_valid_keys(keys):

    for key in _RESERVED_PLACEHOLDERS:
        if key in keys:
            raise ValueError(f"'{key}' is not a valid placeholder")


class _FinderBase:
    def __init__(self, pattern, suffix=""):

        self.pattern = pattern
        self.keys = _find_keys(pattern)
        _assert_valid_keys(self.keys)
        self.parser = parse.compile(self.pattern)
        self._suffix = suffix

        # replace the fmt spec - add the capture group again
        self._pattern_no_fmt_spec = re.sub(
            r"\{([A-Za-z0-9_]+)(:.*?)\}", r"{\1}", pattern
        )

    def create_name(self, keys=None, **keys_kwargs):
        """build name from keys

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the name.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.
        """

        keys = update_dict_with_kwargs(keys, **keys_kwargs)

        return self._pattern_no_fmt_spec.format(**keys)


class _Finder(_FinderBase):
    def _create_condition_dict(self, **kwargs):

        # add wildcard for all undefinded keys
        cond_dict = dict.fromkeys(self.keys, "*")
        cond_dict.update(**kwargs)

        return cond_dict

    def find(
        self, keys=None, *, on_parse_error="raise", _allow_empty=False, **keys_kwargs
    ):
        """find files in the file system using the file and path (folder) pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern. Several names can
            be passed for each key as list.
        on_parse_error : "raise" | "warn" | "ignore", default: "raise"
            What to do if a path/file name cannot be parsed. If "raise" raises a ValueError,
            if "warn" raises a warning and if "ignore" ignores the file.
        _allow_empty : bool, default: False
            If False (default) raises an error if no files are found. If True returns
            an empty list.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        """

        keys = update_dict_with_kwargs(keys, **keys_kwargs)

        if on_parse_error not in ["raise", "warn", "ignore"]:
            raise ValueError(
                f"Unknown value for 'on_parse_error': '{on_parse_error}'. Must be one of 'raise', 'warn' or 'ignore'."
            )

        # wrap strings and scalars in list
        for key, value in keys.items():
            if isinstance(value, str) or np.ndim(value) == 0:
                keys[key] = [value]

        all_paths = list()
        all_patterns = list()
        for one_search_dict in product_dict(**keys):

            cond_dict = self._create_condition_dict(**one_search_dict)
            full_pattern = self.create_name(**cond_dict)

            paths = sorted(self._glob(full_pattern), key=natural_keys)

            all_paths += paths

            all_patterns.append(full_pattern)

        if all_paths:
            df = self._parse_paths(all_paths, on_parse_error=on_parse_error)
        elif _allow_empty:
            return []
        else:
            msg = "Found no files matching criteria. Tried the following pattern(s):"
            msg += "".join(f"\n- '{pattern}'" for pattern in all_patterns)
            raise ValueError(msg)

        fc = FileContainer(df)

        len_all = len(fc.df)
        len_unique = len(fc.combine_by_key().unique())

        if len_all != len_unique:
            duplicated = fc.df[fc.df.duplicated()]
            msg = f"This query leads to non-unique metadata. Please adjust your query.\nFirst five duplicates:\n{duplicated.head()}"

            raise ValueError(msg)

        return fc

    @staticmethod
    def _glob(pattern):
        """Return a list of paths matching a pathname pattern

        Notes
        -----
        glob has it's own method so it can be mocked by the tests

        """

        return glob.glob(pattern)

    def _parse_paths(self, paths, on_parse_error):

        out = list()
        for path in paths:
            parsed = self.parser.parse(path)

            if parsed is None:
                if on_parse_error == "raise":
                    raise ValueError(
                        f"Could not parse '{path}' with the pattern '{self.pattern}' - are"
                        " there contradictory values?"
                    )
                elif on_parse_error == "warn":
                    warnings.warn(
                        f"Could not parse '{path}' with the pattern '{self.pattern}' - are"
                        " there contradictory values?"
                    )
                elif on_parse_error == "ignore":
                    pass
            else:
                out.append([path + self._suffix] + list(parsed.named.values()))

        keys = ["filename"] + list(self.keys)

        df = pd.DataFrame(out, columns=keys)
        return df


class FileFinder:
    """find and create file names based on python format syntax

    Parameters
    ----------
    path_pattern : str
        String denoting the path (folder) pattern where everything variable is enclosed
        in curly braces.
    file_pattern : str
        String denoting the file pattern where everything variable is enclosed in curly
        braces.
    test_paths : list of str, default None
        A list of paths to use instead of querying the file system. To be used for
        testing and demonstration.

    Examples
    --------
    >>> path_pattern = "/root/{category}"
    >>> file_pattern = "{category}_file_{number}"

    >>> ff = FileFinder(path_pattern, file_pattern)
    """

    def __init__(
        self, path_pattern: str, file_pattern: str, *, test_paths=None
    ) -> None:

        if os.path.sep in file_pattern:
            raise ValueError(
                f"`file_pattern` cannot contain path separator ('{os.path.sep}')"
            )

        # cannot search for files (only paths and full)
        self.file = _FinderBase(file_pattern)
        # ensure path_pattern ends with a /
        self.path = _Finder(os.path.join(path_pattern, ""), suffix="*")
        self.full = _Finder(os.path.join(*filter(None, (path_pattern, file_pattern))))

        self.keys_path = self.path.keys
        self.keys_file = self.file.keys
        self.keys = self.full.keys

        self.file_pattern = self.file.pattern
        self.path_pattern = self.path.pattern
        self._full_pattern = self.full.pattern

        if test_paths is not None:
            self._set_test_paths(test_paths)

    def _set_test_paths(self, test_paths):

        if isinstance(test_paths, str):
            test_paths = [test_paths]

        # use fnmatch.filter to 'glob' pseudo-filenames
        def finder(pat):

            # make fnmatch work (almost) the same as glob
            if pat.endswith(os.path.sep):
                paths_ = [os.path.dirname(s) + os.path.sep for s in test_paths]
            else:
                paths_ = test_paths

            return fnmatch.filter(paths_, pat)

        # overwrite the glob implementation
        self.path._glob = finder
        self.full._glob = finder

    def create_path_name(self, keys=None, **keys_kwargs):
        """build path (folder) name from keys

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the path (folder) name.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Examples
        --------
        >>> path_pattern = "/root/{category}"
        >>> file_pattern = "{category}_file_{number}"

        >>> ff = FileFinder(path_pattern, file_pattern)
        >>> ff.create_path_name(category="foo")
        '/root/foo/'

        >>> ff.create_path_name(dict(category="foo"))
        '/root/foo/'

        >>> ff.create_path_name(dict(category="foo"), category="bar")
        '/root/bar/'
        """

        # warnings.warn("'create_path_name' is deprecated, use 'path.name' instead")
        return self.path.create_name(keys, **keys_kwargs)

    def create_file_name(self, keys=None, **keys_kwargs):
        """build file name from keys

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the file name.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Examples
        --------
        >>> path_pattern = "/root/{category}"
        >>> file_pattern = "{category}_file_{number}"

        >>> ff = FileFinder(path_pattern, file_pattern)
        >>> ff.create_file_name(category="foo", number=1)
        'foo_file_1'

        >>> ff.create_file_name(dict(category="foo", number=1))
        'foo_file_1'

        >>> ff.create_file_name(dict(category="foo", number=1), category="bar")
        'bar_file_1'
        """

        # warnings.warn("'create_file_name' is deprecated, use 'file.name' instead")
        return self.file.create_name(keys, **keys_kwargs)

    def create_full_name(self, keys=None, **keys_kwargs):
        """build full (folder + file) name from keys

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the full (folder + file) name.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Examples
        --------
        >>> path_pattern = "/root/{category}"
        >>> file_pattern = "{category}_file_{number}"

        >>> ff = FileFinder(path_pattern, file_pattern)
        >>> ff.create_full_name(category="foo", number=1)
        '/root/foo/foo_file_1'

        >>> ff.create_full_name(dict(category="foo", number=1))
        '/root/foo/foo_file_1'

        >>> ff.create_full_name(dict(category="foo", number=1), category="bar")
        '/root/bar/bar_file_1'
        """

        # warnings.warn("'create_full_name' is deprecated, use 'full.name' instead")
        return self.full.create_name(keys, **keys_kwargs)

    def find_paths(
        self, keys=None, *, on_parse_error="raise", _allow_empty=False, **keys_kwargs
    ):
        """find files in the file system using the file and path (folder) pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern. Several names can
            be passed for each key as list.
        on_parse_error : "raise" | "warn" | "skip", default: "raise"
            What to do if a path/file name cannot be parsed. If "raise" raises a ValueError,
            if "warn" raises a warning and if "skip" ignores the file.
        _allow_empty : bool, default: False
            If False (default) raises an error if no files are found. If True returns
            an empty list.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        Examples
        --------
        >>> path_pattern = "/root/{category}"
        >>> file_pattern = "{category}_file_{number}"
        >>> ff = FileFinder(path_pattern, file_pattern)

        >>> ff.find()   # doctest: +SKIP
        Looks for
        - "/root/*/"

        >>> ff.find(category="foo")   # doctest: +SKIP
        Looks for
        - "/root/foo/"

        >>> ff.find(dict(category=["foo", "bar"]))   # doctest: +SKIP
        Looks for
        - "/root/foo/"
        - "/root/bar/"
        """
        return self.path.find(
            keys,
            on_parse_error=on_parse_error,
            _allow_empty=_allow_empty,
            **keys_kwargs,
        )

    def find_files(
        self, keys=None, *, on_parse_error="raise", _allow_empty=False, **keys_kwargs
    ):
        """find files in the file system using the file pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern. Several names can
            be passed for each key as list.
        on_parse_error : "raise" | "warn" | "skip", default: "raise"
            What to do if a path/file name cannot be parsed. If "raise" raises a ValueError,
            if "warn" raises a warning and if "skip" ignores the file.
        _allow_empty : bool, default: False
            If False (default) raises an error if no files are found. If True returns
            an empty list.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        Examples
        --------
        >>> path_pattern = "/root/{category}"
        >>> file_pattern = "{category}_file_{number}"
        >>> ff = FileFinder(path_pattern, file_pattern)

        >>> ff.find_files()   # doctest: +SKIP
        Looks for
        - "/root/*/*_file_*"

        >>> ff.find_files(number=[1, 2])   # doctest: +SKIP
        Looks for
        - "/root/*/*_file_1"
        - "/root/*/*_file_2"

        >>> meta = {"category": "foo", "number": [1, 2]}
        >>> ff.find_files(meta, category="bar")   # doctest: +SKIP
        Looks for
        - "/root/bar/bar_file_1"
        - "/root/bar/bar_file_2"

        """
        return self.full.find(
            keys,
            on_parse_error=on_parse_error,
            _allow_empty=_allow_empty,
            **keys_kwargs,
        )

    def __repr__(self):

        repr_keys = "', '".join(sorted(self.full.keys))
        repr_keys = f"'{repr_keys}'"

        msg = _FILE_FINDER_REPR.format(
            path_pattern=self.path.pattern,
            file_pattern=self.file.pattern,
            repr_keys=repr_keys,
        )

        return msg


class FileContainer:
    """docstring for FileContainer"""

    def __init__(self, df):

        self.df = df

    def __iter__(self):

        for index, element in self.df.iterrows():
            yield element["filename"], element.drop("filename").to_dict()

    def __getitem__(self, key):

        if isinstance(key, (int, np.integer)):
            # use iloc -> there can be more than one element with index 0
            element = self.df.iloc[key]

            return element["filename"], element.drop("filename").to_dict()
        # assume slice or [1]
        else:
            ret = copy.copy(self)
            ret.df = self.df.iloc[key]
            return ret

    def combine_by_key(self, keys=None, sep="."):
        """combine columns"""

        if keys is None:
            keys = list(self.df.columns.drop("filename"))

        return self.df[list(keys)].apply(lambda x: sep.join(x.map(str)), axis=1)

    def search(self, **query):

        ret = copy.copy(self)
        ret.df = self._get_subset(**query)
        return ret

    def _get_subset(self, **query):
        if not query:
            return pd.DataFrame(columns=self.df.columns)
        condition = np.ones(len(self.df), dtype=bool)
        for key, val in query.items():
            if isinstance(val, list):
                condition_i = np.zeros(len(self.df), dtype=bool)
                for val_i in val:
                    condition_i = condition_i | (self.df[key] == val_i)
                condition = condition & condition_i
            elif val is not None:
                condition = condition & (self.df[key] == val)
        query_results = self.df.loc[condition]
        return query_results

    def __len__(self):
        return self.df.__len__()

    def __repr__(self):

        msg = "<FileContainer>\n"
        return msg + self.df.__repr__()
