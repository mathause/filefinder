import textwrap

import pandas as pd
import pytest

from filefinder import FileFinder


@pytest.fixture(scope="module", params=["from_filesystem", "from_string"])
def test_paths(request, tmp_path):

    if request.param == "from_filesystem":
        return None

    paths = ["a1/foo/file", "a2/foo/file"]
    paths = [str(tmp_path / path) for path in paths]

    return paths


def test_pattern_no_fmt_spec():

    path_pattern = "{path:l}_{pattern:2d}_{no_fmt}/"
    file_pattern = "{file}_{pattern:2d}"

    path_pattern_no_fmt = "{path}_{pattern}_{no_fmt}/"
    file_pattern_no_fmt = "{file}_{pattern}"

    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    assert ff.path._pattern_no_fmt_spec == path_pattern_no_fmt
    assert ff.file._pattern_no_fmt_spec == file_pattern_no_fmt

    assert ff.full._pattern_no_fmt_spec == path_pattern_no_fmt + file_pattern_no_fmt


def test_keys():

    file_pattern = "{a:l}_{b}_{c:d}"
    path_pattern = "{ab}_{c:d}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = ("ab", "c", "a", "b")
    assert ff.keys == expected

    expected = ("a", "b", "c")
    assert ff.keys_file == expected

    expected = ("ab", "c")
    assert ff.keys_path == expected


def test_repr():

    path_pattern = "/{a:l}/{b}"
    file_pattern = "{b}_{c:d}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    expected = """\
    <FileFinder>
    path_pattern: '/{a:l}/{b}/'
    file_pattern: '{b}_{c:d}'

    keys: 'a', 'b', 'c'
    """
    expected = textwrap.dedent(expected)
    assert expected == ff.__repr__()


def test_create_name():

    path_pattern = "{a:w}/{b}"
    file_pattern = "{b}_{c:l}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    result = ff.create_path_name(a="a", b="b")
    assert result == "a/b/"

    result = ff.create_file_name(b="b", c="c")
    assert result == "b_c"

    result = ff.create_full_name(a="a", b="b", c="c")
    assert result == "a/b/b_c"


def test_create_name_dict():

    path_pattern = "{a:w}/{b}"
    file_pattern = "{b}_{c:d}"
    ff = FileFinder(path_pattern=path_pattern, file_pattern=file_pattern)

    result = ff.create_path_name(dict(a="a", b="b"))
    assert result == "a/b/"

    result = ff.create_file_name(dict(b="b", c="c"))
    assert result == "b_c"

    result = ff.create_full_name(dict(a="a", b="b", c="c"))
    assert result == "a/b/b_c"


def test_find_paths_fmt():

    test_paths = ["a1/a1_abc", "ab200/ab200_aicdef"]

    path_pattern = "{letters:l}{num:d}"
    file_pattern = "{letters:l}{num:d}_{beg:2}{end}"

    ff = FileFinder(
        path_pattern=path_pattern, file_pattern=file_pattern, test_paths=test_paths
    )

    expected = {
        "filename": {0: "a1/a1_abc", 1: "ab200/ab200_aicdef"},
        "letters": {0: "a", 1: "ab"},
        "num": {0: 1, 1: 200},
        "beg": {0: "ab", 1: "ai"},
        "end": {0: "c", 1: "cdef"},
    }
    expected = pd.DataFrame.from_dict(expected)

    result = ff.find_files()
    pd.testing.assert_frame_equal(result.df, expected)

    result = ff.find_files(num=[1])
    pd.testing.assert_frame_equal(result.df, expected.iloc[[0]])
