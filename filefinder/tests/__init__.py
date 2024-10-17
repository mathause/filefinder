import warnings
from contextlib import contextmanager
from typing import Iterable

import pandas as pd

from filefinder import FileContainer


@contextmanager
def assert_no_warnings():

    with warnings.catch_warnings(record=True) as record:
        yield record
        assert len(record) == 0, "got unexpected warning(s)"


def assert_filecontainer_empty(
    fc: FileContainer, columns: str | Iterable[str] | None = None
):
    """checks passed object is an empty `FileContainer`

    Parameters
    ----------
    fc : FileContainer
        Filecontainer to ensure is empty.
    columns : str, iterable of str | None, optional
        Keys/ columns the empty FileContainer should have.
    """

    assert isinstance(fc, FileContainer)

    assert isinstance(fc.df, pd.DataFrame)
    assert fc.df.index.name == "path"
    assert len(fc) == 0, f"FileContainer not empty ({len(fc)=})"

    if isinstance(columns, str):
        columns = {columns}

    # DataFrame should contain the keys as empty columns
    if columns:
        assert set(fc.df.columns) == set(columns)
