import os
import textwrap

import pandas as pd
import pytest

from filefinder import FileFinder


@pytest.fixture(scope="module")
def path(tmp_path_factory):
    """
    Creates the following temporary structure:
    - /tmp/filefinder/a1/foo/file
    - /tmp/filefinder/a2/foo/file
    """

    tmp_path = tmp_path_factory.mktemp("filefinder")

    d = tmp_path / "a1" / "foo"
    d.mkdir(parents=True)
    f = d / "file"
    f.write_text("")

    d = tmp_path / "a2" / "foo"
    d.mkdir(parents=True)
    f = d / "file"
    f.write_text("")

    return tmp_path


def test_pattern_property():

    path_pattern = "path_pattern/"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    assert ff.path_pattern == path_pattern
    assert ff.file_pattern == file_pattern

    assert ff._full_pattern == path_pattern + file_pattern

    assert ff.path.pattern == path_pattern
    assert ff.file.pattern == file_pattern

    assert ff.full.pattern == path_pattern + file_pattern


def test_file_pattern_no_sep():

    path_pattern = "path_pattern"
    file_pattern = "file" + os.path.sep + "pattern"

    with pytest.raises(ValueError, match="cannot contain path separator"):
        FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)


def test_pattern_sep_added():

    path_pattern = "path_pattern"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)
    assert ff.path_pattern == path_pattern + os.path.sep


def test_keys():

    file_pattern = "{a}_{b}_{c}"
    path_pattern = "{ab}_{c}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = set(("a", "b", "c", "ab"))
    assert ff.keys == expected

    expected = set(("a", "b", "c"))
    assert ff.keys_file == expected

    expected = set(("ab", "c"))
    assert ff.keys_path == expected


def test_repr():

    path_pattern = "/{a}/{b}"
    file_pattern = "{b}_{c}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = """\
    <FileFinder>
    path_pattern: '/{a}/{b}/'
    file_pattern: '{b}_{c}'

    keys: 'a', 'b', 'c'
    """
    expected = textwrap.dedent(expected)
    assert expected == ff.__repr__()

    path_pattern = "{a}"
    file_pattern = "file_pattern"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = """\
    <FileFinder>
    path_pattern: '{a}/'
    file_pattern: 'file_pattern'

    keys: 'a'
    """
    expected = textwrap.dedent(expected)
    assert expected == ff.__repr__()


def test_create_name():

    path_pattern = "{a}/{b}"
    file_pattern = "{b}_{c}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    result = ff.create_path_name(a="a", b="b")
    assert result == "a/b/"

    result = ff.create_file_name(b="b", c="c")
    assert result == "b_c"

    result = ff.create_full_name(a="a", b="b", c="c")
    assert result == "a/b/b_c"


def test_create_name_dict():

    path_pattern = "{a}/{b}"
    file_pattern = "{b}_{c}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    result = ff.create_path_name(dict(a="a", b="b"))
    assert result == "a/b/"

    result = ff.create_file_name(dict(b="b", c="c"))
    assert result == "b_c"

    result = ff.create_full_name(dict(a="a", b="b", c="c"))
    assert result == "a/b/b_c"


def test_create_name_kwargs_priority():

    path_pattern = "{a}/{b}"
    file_pattern = "{b}_{c}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    result = ff.create_path_name(dict(a="XXX", b="b"), a="a")
    assert result == "a/b/"

    result = ff.create_file_name(dict(b="XXX", c="c"), b="b")
    assert result == "b_c"

    result = ff.create_full_name(dict(a="XXX", b="b"), a="a", c="c")
    assert result == "a/b/b_c"


def test_find_path_none_found(path):

    path_pattern = path / "{a}/foo/"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    with pytest.raises(ValueError, match="Found no files matching criteria"):
        ff.find_paths(a="foo")

    with pytest.raises(ValueError, match="Found no files matching criteria"):
        ff.find_paths({"a": "foo"})

    result = ff.find_paths(a="foo", _allow_empty=True)
    assert result == []

    result = ff.find_paths({"a": "foo"}, _allow_empty=True)
    assert result == []


def test_find_paths_simple(path):

    path_pattern = path / "a1/{a}/"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {"filename": {0: str(path / "a1/foo/*")}, "a": {0: "foo"}}
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_paths(a="foo")
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths(dict(a="foo"))
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths(dict(a="XXX"), a="foo")
    pd.testing.assert_frame_equal(result.df, expected)


@pytest.mark.parametrize("find_kwargs", [{"b": "foo"}, {"a": "*", "b": "foo"}])
def test_find_paths_wildcard(path, find_kwargs):

    path_pattern = path / "{a}/{b}"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {
        "filename": {0: str(path / "a1/foo/*"), 1: str(path / "a2/foo/*")},
        "a": {0: "a1", 1: "a2"},
        "b": {0: "foo", 1: "foo"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_paths(**find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths(find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths({"b": "XXX"}, **find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)


@pytest.mark.parametrize(
    "find_kwargs",
    [{"a": ["a1", "a2"], "b": "foo"}, {"a": ["a1", "a2"], "b": ["foo", "bar"]}],
)
def test_find_paths_several(path, find_kwargs):

    path_pattern = path / "{a}/{b}"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {
        "filename": {0: str(path / "a1/foo/*"), 1: str(path / "a2/foo/*")},
        "a": {0: "a1", 1: "a2"},
        "b": {0: "foo", 1: "foo"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_paths(**find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths(find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths({"a": "XXX", "b": "XXX"}, **find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)


@pytest.mark.parametrize(
    "find_kwargs",
    [{"a": "a1"}, {"a": "a1", "b": "foo"}, {"a": "a1", "b": ["foo", "bar"]}],
)
def test_find_paths_one_of_several(path, find_kwargs):

    path_pattern = path / "{a}/{b}"
    file_pattern = "file_pattern"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {
        "filename": {0: str(path / "a1/foo/*")},
        "a": {0: "a1"},
        "b": {0: "foo"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_paths(**find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths(find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_paths({"a": "XXX"}, **find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)


def test_find_file_none_found(path):

    path_pattern = path / "{a}/foo/"
    file_pattern = "{file_pattern}"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    with pytest.raises(ValueError, match="Found no files matching criteria"):
        ff.find_files(a="XXX")

    with pytest.raises(ValueError, match="Found no files matching criteria"):
        ff.find_files({"a": "XXX"})

    result = ff.find_files(a="XXX", _allow_empty=True)
    assert result == []

    result = ff.find_files({"a": "XXX"}, _allow_empty=True)
    assert result == []

    result = ff.find_files({"a": "XXX"}, _allow_empty=True, a="XXX")
    assert result == []


def test_find_file_simple(path):

    path_pattern = path / "a1/{a}/"
    file_pattern = "file"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {"filename": {0: str(path / "a1/foo/file")}, "a": {0: "foo"}}
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_files(a="foo")
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files({"a": "foo"})
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files({"a": "XXX"}, a="foo")
    pd.testing.assert_frame_equal(result.df, expected)


@pytest.mark.parametrize("find_kwargs", [{"b": "file"}, {"a": "*", "b": "file"}])
def test_find_files_wildcard(path, find_kwargs):

    path_pattern = path / "{a}/foo"
    file_pattern = "{b}"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {
        "filename": {0: str(path / "a1/foo/file"), 1: str(path / "a2/foo/file")},
        "a": {0: "a1", 1: "a2"},
        "b": {0: "file", 1: "file"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_files(**find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files(find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files({"b": "XXX"}, **find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)


@pytest.mark.parametrize(
    "find_kwargs",
    [{"a": ["a1", "a2"], "b": "file"}, {"a": ["a1", "a2"], "b": ["file", "bar"]}],
)
def test_find_files_several(path, find_kwargs):

    path_pattern = path / "{a}/foo"
    file_pattern = "{b}"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {
        "filename": {0: str(path / "a1/foo/file"), 1: str(path / "a2/foo/file")},
        "a": {0: "a1", 1: "a2"},
        "b": {0: "file", 1: "file"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_files(**find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files(find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files({"a": "XXX", "b": "XXX"}, **find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)


@pytest.mark.parametrize(
    "find_kwargs",
    [{"a": "a1"}, {"a": "a1", "b": "file"}, {"a": "a1", "b": ["file", "bar"]}],
)
def test_find_files_one_of_several(path, find_kwargs):

    path_pattern = path / "{a}/foo"
    file_pattern = "{b}"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = {
        "filename": {0: str(path / "a1/foo/file")},
        "a": {0: "a1"},
        "b": {0: "file"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_files(**find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files(find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files({"a": "XXX"}, **find_kwargs)
    pd.testing.assert_frame_equal(result.df, expected)
