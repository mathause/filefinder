import pandas as pd

from filefinder import FileContainer
from filefinder.cmip import create_ensnumber, ensure_unique_grid, parse_ens


def test_parse_ens_cmip5():

    # pattern: "r{r}i{i}p{p}"

    df = pd.DataFrame.from_records(
        [
            ("file1", "r1i1p1"),
            ("file2", "r2i1p1"),
            ("file3", "r3i1p1"),
            ("file4", "r1i2p1"),
            ("file5", "r1i1p2"),
        ],
        columns=("filename", "ens"),
    )

    fc = FileContainer(df)

    expected_df = pd.DataFrame.from_records(
        [
            ("file1", "r1i1p1", "1", "1", "1"),
            ("file2", "r2i1p1", "2", "1", "1"),
            ("file3", "r3i1p1", "3", "1", "1"),
            ("file4", "r1i2p1", "1", "2", "1"),
            ("file5", "r1i1p2", "1", "1", "2"),
        ],
        columns=("filename", "ens", "r", "i", "p"),
    )

    result = parse_ens(fc)
    assert isinstance(result, FileContainer)

    pd.testing.assert_frame_equal(result.df, expected_df)


def test_parse_ens_cmip6():

    # pattern: "r{r}i{i}p{p}f{f}"

    df = pd.DataFrame.from_records(
        [
            ("file1", "r1i1p1f1"),
            ("file2", "r2i1p1f2"),
            ("file3", "r3i1p1f1"),
            ("file4", "r1i2p1f1"),
            ("file5", "r1i1p2f1"),
        ],
        columns=("filename", "ens"),
    )

    fc = FileContainer(df)

    expected_df = pd.DataFrame.from_records(
        [
            ("file1", "r1i1p1f1", "1", "1", "1", "1"),
            ("file2", "r2i1p1f2", "2", "1", "1", "2"),
            ("file3", "r3i1p1f1", "3", "1", "1", "1"),
            ("file4", "r1i2p1f1", "1", "2", "1", "1"),
            ("file5", "r1i1p2f1", "1", "1", "2", "1"),
        ],
        columns=("filename", "ens", "r", "i", "p", "f"),
    )

    result = parse_ens(fc)
    assert isinstance(result, FileContainer)

    pd.testing.assert_frame_equal(result.df, expected_df)


def test_create_ensnumber():
    columns = ("filename", "model", "exp", "table", "varn", "ens")

    common = ("exp", "table", "varn")

    records = [
        ("file0", "CESM2", *common, "r1i1p1f1"),
        ("file1", "CESM2", *common, "r2i1p1f1"),
        ("file2", "CESM2", *common, "r3i1p1f1"),
        ("file3", "UKESM", *common, "r1i2p1f1"),
        ("file4", "UKESM", *common, "r1i3p1f1"),
    ]

    df = pd.DataFrame.from_records(
        records,
        columns=columns,
    )

    expected_df = pd.DataFrame.from_records(
        records,
        columns=columns,
    )
    expected_df["ensnumber"] = (0, 1, 2, 0, 1)

    fc = FileContainer(df)

    result = create_ensnumber(fc)
    assert isinstance(result, FileContainer)

    pd.testing.assert_frame_equal(result.df, expected_df)


def test_ensure_unique_grid():

    columns = ("model", "exp", "table", "varn", "ens", "grid")

    # VALID_GRIDS = ("gn", "gr", "gr1", "gm")

    common = ("exp", "table", "varn", "ens")

    df = pd.DataFrame.from_records(
        [
            ("CESM2", *common, "gr"),
            ("CESM2", *common, "gn"),
            ("CESM2", *common, "gm"),
            ("UKESM", *common, "gr"),
            ("UKESM", *common, "gr1"),
        ],
        columns=columns,
    )

    expected = pd.DataFrame.from_records(
        [
            ("CESM2", *common, "gn"),
            ("UKESM", *common, "gr"),
        ],
        columns=columns,
    )

    result = ensure_unique_grid(df)

    pd.testing.assert_frame_equal(result, expected)
