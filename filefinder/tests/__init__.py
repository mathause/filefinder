import warnings
from contextlib import contextmanager


@contextmanager
def assert_no_warnings():

    with warnings.catch_warnings(record=True) as record:
        yield record
        assert len(record) == 0, "got unexpected warning(s)"
