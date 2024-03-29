import itertools
import re

import pandas as pd


def _find_keys(string):
    """find keys in a format string

    find all keys enclosed by curly brackets

    >>> _find_keys("/path/{var_name}/{year}") == ("var_name", "year")
    True

    >>> _find_keys("/path/{var_name}/{year:d}") == ("var_name", "year")
    True
    """

    # match group
    pattern = (
        r"\{"
        r"([A-Za-z0-9_]+)"  # capturing group with one or more characters, number or _
        r"(?::.*?)?"  # non-capturing group, non greedy matching any char, zero or once
        r"\}"
    )

    keys = re.findall(pattern, string)
    keys = tuple(pd.Series(keys).unique())

    return keys


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """key for natural sorting order

    Examples
    --------
    >>> l = ['a10', 'a1']
    >>> l.sort(key=natural_keys)
    >>> l
    ['a1', 'a10']

    References
    ----------
    http://nedbatchelder.com/blog/200712/human_sorting.html
    """
    return [atoi(c) for c in re.split(r"(\d+)", text)]


def product_dict(**kwargs):
    """generate list of dictionaries with all possible combinations

    Examples
    --------
    >>> list(product_dict(**{"a": [1, 2], "b": [3, 4], "c": [5]}))
    [{'a': 1, 'b': 3, 'c': 5}, {'a': 1, 'b': 4, 'c': 5}, {'a': 2, 'b': 3, 'c': 5}, {'a': 2, 'b': 4, 'c': 5}]

    References
    ----------
    https://stackoverflow.com/a/5228294/3010700
    """

    keys = kwargs.keys()
    for instance in itertools.product(*kwargs.values()):
        yield dict(zip(keys, instance))


def update_dict_with_kwargs(dictionary, /, **kwargs):
    """update a dictionary with keyword arguments. The kwargs take precedence

    Parameters
    ----------
    dictionary : dict, optional
        The dictionary to update with the keyword arguments.
    **kwargs : keyword arguments
        The keyword arguments.

    Examples
    --------
    >>> update_dict_with_kwargs({"a": 1}, a=2)
    {'a': 2}
    >>> update_dict_with_kwargs({"a": 1, "b":2}, b=3, c=5)
    {'a': 1, 'b': 3, 'c': 5}
    """

    if not isinstance(dictionary, (dict, type(None))):
        raise TypeError(
            f"First argument must be a dict or None, got '{type(dictionary).__name__}'"
        )

    return (dictionary or {}) | kwargs
