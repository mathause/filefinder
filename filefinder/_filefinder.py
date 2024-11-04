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

from filefinder._utils import (
    _find_keys,
    natural_keys,
    product_dict,
    update_dict_with_kwargs,
)

logger = logging.getLogger(__name__)

_FILE_FINDER_REPR = """<FileFinder>
path_pattern: '{path_pattern}'
file_pattern: '{file_pattern}'

keys: {repr_keys}
"""


def _deprecate_allow_empty(**kwargs):

    _allow_empty = kwargs.get("_allow_empty")

    if _allow_empty is not None:
        raise TypeError("`_allow_empty` has been deprecated in favour of `on_empty`")


_RESERVED_PLACEHOLDERS = {"keys", "on_parse_error", "on_empty", "_allow_empty"}


def _assert_valid_keys(keys) -> None:

    for key in _RESERVED_PLACEHOLDERS:
        if key in keys:
            raise ValueError(f"'{key}' is not a valid placeholder")


def _assert_unique(df) -> None:

    duplicates = df.duplicated()

    if duplicates.any():
        duplicated = df[duplicates].head()
        msg = f"Non-unique metadata detected.\nFirst five duplicates:\n{duplicated}"

        raise ValueError(msg)


class _FinderBase:
    def __init__(self, pattern, suffix=""):

        self.pattern = pattern
        self.keys = _find_keys(pattern)
        _assert_valid_keys(self.keys)
        self.parser = parse.compile(self.pattern)

        if self.parser.fixed_fields:
            msg = (
                "Only named fields are currently allowed: avoid empty braces and"
                " leading underscores."
            )
            raise ValueError(msg)

        self._suffix = suffix

        # replace the fmt spec - add the capture group again
        self._pattern_no_fmt_spec = re.sub(
            r"\{([A-Za-z0-9_]+)(:.*?)\}", r"{\1}", pattern
        )

    def create_name(self, keys=None, **keys_kwargs) -> str:
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
        self, keys=None, *, on_parse_error="raise", on_empty="raise", **keys_kwargs
    ) -> "FileContainer":
        """find files in the file system using the file and path (folder) pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern. Several names can
            be passed for each key as list.
        on_parse_error : "raise" | "warn" | "ignore", default: "raise"
            What to do if a path/file name cannot be parsed. If "raise" raises a ValueError,
            if "warn" raises a warning and if "ignore" ignores the file.
        on_empty : "raise" | "warn" | "allow", default: "raise"
            Behaviour when no files are found: "raise" (default) raises a ValueError,
            "warn" raises a warning. For "warn" and "allow" an empty FileContainer is returned.
            an empty list.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        """

        _deprecate_allow_empty(**keys_kwargs)

        keys = update_dict_with_kwargs(keys, **keys_kwargs)

        if on_parse_error not in ("raise", "warn", "ignore"):
            raise ValueError(
                f"Unknown value for 'on_parse_error': '{on_parse_error}'. Must be one of 'raise', 'warn' or 'ignore'."
            )

        if on_empty not in ("raise", "warn", "allow"):
            raise ValueError(
                f"Unknown value for 'on_empty': '{on_empty}'. Must be one of 'raise', 'warn' or 'allow'."
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

        if len(all_paths) == 0:
            msg = "Found no files matching criteria. Tried the following pattern(s):"
            msg += "".join(f"\n- '{pattern}'" for pattern in all_patterns)

            if on_empty == "raise":
                raise ValueError(msg)
            elif on_empty == "warn":
                # TODO: correct stack level
                warnings.warn(msg)

        # NOTE: also creates the correct (empty) df if no paths are found
        df = self._parse_paths(all_paths, on_parse_error=on_parse_error)
        _assert_unique(df)

        return FileContainer(df)

    def find_single(self, keys=None, **keys_kwargs) -> "FileContainer":
        """
        find exactly one file/ path in the file system using the file and path pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        Raises
        ------
        ValueError : if more or less than one file/ path is found
        """

        fc = self.find(keys, on_parse_error="raise", on_empty="raise", **keys_kwargs)

        if len(fc) > 1:
            n_found = len(fc)
            msg = (
                f"Found more than one ({n_found}) files/ paths. Please adjust your"
                f" query.\nFirst five files/ paths:\n{fc.df.head()}"
            )
            raise ValueError(msg)

        return fc

    @staticmethod
    def _glob(pattern) -> list[str]:
        """Return a list of paths matching a pathname pattern

        Notes
        -----
        glob has it's own method so it can be mocked by the tests

        """

        return glob.glob(pattern)

    def _parse_paths(self, paths, on_parse_error) -> pd.DataFrame:

        valid_paths, out = list(), list()
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
                valid_paths.append(path)
                out.append(list(parsed.named.values()))

        index = pd.Index(valid_paths, name="path") + self._suffix
        df = pd.DataFrame(out, columns=self.keys, index=index)
        return df


class FileFinder:

    def __init__(
        self, path_pattern: str, file_pattern: str, *, test_paths=None
    ) -> None:
        """find and create file names based on python format syntax

        Parameters
        ----------
        path_pattern : str
            String denoting the path (folder) pattern where everything variable is
            enclosed in curly braces.
        file_pattern : str
            String denoting the file pattern where everything variable is enclosed in
            curly braces.
        test_paths : list of str, default None
            A list of paths to use instead of querying the file system. To be used for
            testing and demonstration.

        Examples
        --------
        >>> path_pattern = "/root/{category}"
        >>> file_pattern = "{category}_file_{number}"

        >>> ff = FileFinder(path_pattern, file_pattern)
        """

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

        self._test_paths = test_paths

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

    def create_path_name(self, keys=None, **keys_kwargs) -> str:
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

    def create_file_name(self, keys=None, **keys_kwargs) -> str:
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

    def create_full_name(self, keys=None, **keys_kwargs) -> str:
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
        self, keys=None, *, on_parse_error="raise", on_empty="raise", **keys_kwargs
    ) -> "FileContainer":
        """find files in the file system using the file and path (folder) pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern. Several names can
            be passed for each key as list.
        on_parse_error : "raise" | "warn" | "skip", default: "raise"
            What to do if a path/file name cannot be parsed. If "raise" raises a ValueError,
            if "warn" raises a warning and if "skip" ignores the file.
        on_empty : "raise" | "warn" | "allow", default: "raise"
            Behaviour when no files are found: "raise" (default) raises a ValueError,
            "warn" raises a warning. For "warn" and "allow" an empty FileContainer is returned.
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

        >>> ff.find_paths()   # doctest: +SKIP
        Looks for
        - "/root/*/"

        >>> ff.find_paths(category="foo")   # doctest: +SKIP
        Looks for
        - "/root/foo/"

        >>> ff.find_paths(dict(category=["foo", "bar"]))   # doctest: +SKIP
        Looks for
        - "/root/foo/"
        - "/root/bar/"
        """
        return self.path.find(
            keys,
            on_parse_error=on_parse_error,
            on_empty=on_empty,
            **keys_kwargs,
        )

    def find_files(
        self, keys=None, *, on_parse_error="raise", on_empty="raise", **keys_kwargs
    ) -> "FileContainer":
        """find files in the file system using the file pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern. Several names can
            be passed for each key as list.
        on_parse_error : "raise" | "warn" | "skip", default: "raise"
            What to do if a path/file name cannot be parsed. If "raise" raises a ValueError,
            if "warn" raises a warning and if "skip" ignores the file.
        on_empty : "raise" | "warn" | "allow", default: "raise"
            Behaviour when no files are found: "raise" (default) raises a ValueError,
            "warn" raises a warning. For "warn" and "allow" an empty FileContainer is returned.
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
            on_empty=on_empty,
            **keys_kwargs,
        )

    def find_single_path(self, keys=None, **keys_kwargs) -> "FileContainer":
        """
        find exactly one path in the file system using the path pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        Raises
        ------
        ValueError : if more or less than one path is found
        """

        return self.path.find_single(keys, **keys_kwargs)

    def find_single_file(self, keys=None, **keys_kwargs) -> "FileContainer":
        """
        find exactly one file in the file system using the file and path pattern

        Parameters
        ----------
        keys : dict
            Dictionary containing keys to create the search pattern.
        **keys_kwargs : {key: indexer, ...}, optional
            The keyword arguments form of ``keys``. When the same key is passed in
            ``keys`` and ``keys_kwargs`` the latter takes priority.

        Notes
        -----
        Missing ``keys`` are replaced with ``"*"``.

        Raises
        ------
        ValueError : if more or less than one file is found
        """

        return self.full.find_single(keys, **keys_kwargs)

    def __repr__(self) -> str:

        repr_keys = "', '".join(sorted(self.full.keys))
        repr_keys = f"'{repr_keys}'"

        msg = _FILE_FINDER_REPR.format(
            path_pattern=self.path.pattern,
            file_pattern=self.file.pattern,
            repr_keys=repr_keys,
        )

        return msg


class FileContainer:

    def __init__(self, df: pd.DataFrame):
        """FileContainer gathers paths and their metadata

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with info about found paths from FileFinder.
        """

        self.df = df

    def __iter__(self):

        for index, element in self.df.iterrows():
            yield index, element.to_dict()

    def __getitem__(self, key):

        if isinstance(key, (int, np.integer)):
            # use iloc -> there can be more than one element with index 0
            element = self.df.iloc[key]

            return element.name, element.to_dict()
        # assume slice or [1]
        else:
            ret = copy.copy(self)
            ret.df = self.df.iloc[key]
            return ret

    def combine_by_key(self, keys=None, sep="."):
        warnings.warn(
            "`combine_by_key` has been deprecated and will be removed in a future version",
            FutureWarning,
        )

        return self._combine_by_keys(keys=keys, sep=sep)

    def _combine_by_keys(self, keys=None, sep="."):
        """combine columns"""

        if keys is None:
            keys = list(self.df.columns)

        return self.df[list(keys)].apply(lambda x: sep.join(x.map(str)), axis=1)

    def search(self, **query):
        """subset paths given a search query

        Parameters
        ----------
        **query: Mapping[str, str | int | list[str | int]]
            Search query.

        Notes
        -----
        - individual conditions are combined with "and", e.g., ``model="a", exp="b"``
          requires the model to be "a" and the experiment to be "b".
        - conditions for a key are combined with "or", e.g., ``model=["a", "b"]``
          matches for both.
        """

        df = self._get_subset(**query)
        return type(self)(df)

    def _get_subset(self, **query):
        if not query:
            return pd.DataFrame(
                [], columns=self.df.columns, index=pd.Index([], name="path")
            )

        sel = True
        for key, value in query.items():
            # isin does not handle scalars
            value = [value] if np.ndim(value) == 0 else value

            sel &= self.df[key].isin(value)

        return self.df[sel]

    def __len__(self):
        return self.df.__len__()

    def __repr__(self):

        n_paths = len(self)

        msg = f"<FileContainer: {n_paths} paths>\n"
        return msg + self.df.__repr__()
