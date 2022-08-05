import pandas as pd
import pytest

from filefinder import FileContainer
from filefinder.filters import priority_filter

from . import assert_no_warnings

# ({"model": ["a", "a", "b", "c", "c", "d"], "res": ["d", "h", "h", "h", "d", "z"]})


def test_priority_filter_errors():

    df = pd.DataFrame.from_records(
        [("a", "d")],
        columns=("model", "res"),
    )

    with pytest.raises(ValueError, match=r"column \('not_av'\) must be available"):
        priority_filter(df, "not_av", ["a"])

    with pytest.raises(ValueError, match=r"groupby` may not contain column \('res'\)"):
        priority_filter(df, "res", ["a"], groupby=["model", "res"])


def test_priority_filter_simple():

    df = pd.DataFrame.from_records(
        [("a", "d"), ("a", "h"), ("b", "h"), ("b", "d"), ("c", "d")],
        columns=("model", "res"),
    )

    expected = pd.DataFrame.from_records(
        [("a", "h"), ("b", "h"), ("c", "d")], columns=("model", "res")
    )

    result = priority_filter(df, "res", ["h", "d"])

    pd.testing.assert_frame_equal(result, expected)


def test_priority_filter_missing():

    df = pd.DataFrame.from_records(
        [("a", "d"), ("a", "h"), ("b", "d"), ("c", "z")], columns=("model", "res")
    )

    expected = pd.DataFrame.from_records(
        [("a", "h"), ("b", "d")], columns=("model", "res")
    )

    with pytest.raises(
        ValueError, match="Did not find any element from the priority list"
    ):
        priority_filter(df, "res", ["h", "d"])

    with pytest.warns(
        UserWarning, match="Did not find any element from the priority list"
    ):
        result = priority_filter(df, "res", ["h", "d"], on_missing="warn")

    pd.testing.assert_frame_equal(result, expected)

    with assert_no_warnings():
        res = priority_filter(df, "res", ["h", "d"], on_missing="ignore")

    pd.testing.assert_frame_equal(res, expected)


def test_priority_filter_duplicates():

    df = pd.DataFrame.from_records([("a", "d"), ("a", "d")], columns=("model", "res"))

    with pytest.raises(ValueError, match="Found more than one"):
        priority_filter(df, "res", ["h", "d"])


def test_priority_filter_multi():

    df = pd.DataFrame.from_records(
        [("a", 1, "d"), ("a", 2, "d"), ("a", 1, "h"), ("b", 1, "h")],
        columns=("model", "number", "res"),
    )

    expected = pd.DataFrame.from_records(
        [("a", 1, "h"), ("a", 2, "d"), ("b", 1, "h")],
        columns=("model", "number", "res"),
    )

    result = priority_filter(df, "res", ["h", "d"])

    pd.testing.assert_frame_equal(result, expected)


def test_priority_filter_groupby():

    df = pd.DataFrame.from_records(
        [("a", 1, "d"), ("a", 2, "h"), ("b", 1, "h"), ("b", 2, "d")],
        columns=("model", "number", "res"),
    )

    result = priority_filter(df, "res", ["h", "d"])
    expected = df

    pd.testing.assert_frame_equal(result, expected)

    expected = pd.DataFrame.from_records(
        [("a", 2, "h"), ("b", 1, "h")], columns=("model", "number", "res")
    )
    result = priority_filter(df, "res", ["h", "d"], groupby=["model"])
    pd.testing.assert_frame_equal(result, expected)


def test_priority_filter_filename():
    """the filename is per default unique -> must be excluded from groupby"""
    df = pd.DataFrame.from_records(
        [
            ("file1", "a", "d"),
            ("file2", "a", "h"),
            ("file3", "b", "h"),
            ("file4", "b", "d"),
            ("file5", "c", "d"),
        ],
        columns=("filename", "model", "res"),
    )

    expected = pd.DataFrame.from_records(
        [("file2", "a", "h"), ("file3", "b", "h"), ("file5", "c", "d")],
        columns=("filename", "model", "res"),
    )

    result = priority_filter(df, "res", ["h", "d"])

    pd.testing.assert_frame_equal(result, expected)


def test_priority_filter_filecontainer_simple():
    """the filename is per default unique -> must be excluded from groupby"""
    df = pd.DataFrame.from_records(
        [
            ("file1", "a", "d"),
            ("file2", "a", "h"),
            ("file3", "b", "h"),
            ("file4", "b", "d"),
            ("file5", "c", "d"),
        ],
        columns=("filename", "model", "res"),
    )

    fc = FileContainer(df)

    expected = pd.DataFrame.from_records(
        [("file2", "a", "h"), ("file3", "b", "h"), ("file5", "c", "d")],
        columns=("filename", "model", "res"),
    )

    result = priority_filter(fc, "res", ["h", "d"])

    assert isinstance(result, FileContainer)

    pd.testing.assert_frame_equal(result.df, expected)
