import functools
import warnings

import pandas as pd


def _wrap_filecontainer(func):
    @functools.wraps(func)
    def _inner(*args, **kwargs):

        from filefinder import FileContainer

        obj, *args = args

        is_filecontainer = False
        if isinstance(obj, FileContainer):
            obj = obj.df
            is_filecontainer = True

        obj = func(obj, *args, **kwargs)

        if is_filecontainer:
            obj = FileContainer(obj)

        return obj

    return _inner


@_wrap_filecontainer
def priority_filter(obj, column, order, *, on_missing="raise", groupby=None):
    """filter a dataframe on for nonunique entries according to a priority list

    Parameters
    ----------
    obj : pd.DataFrame | FileContainer
        Pandas DataFrame or FileContainer to filter.
    column : str
        The columt to apply the priority filter to.
    order : list of str
        The priority order.
    on_missing : "raise" | "warn" | "ignore", default "raise"
        Behaviour if none of the elements is found.
    groupby : None | list of str, default None
        Which columns to groupby over for the priority filter. Per default it uses all
        columns except `column`.

    """

    if on_missing == "error":
        warnings.warn(
            "on_missing value 'error' has been renamed to 'raise'", FutureWarning
        )
        on_missing = "raise"

    if on_missing not in ["raise", "warn", "ignore"]:
        raise ValueError(
            f"Unknown value for 'on_missing': '{on_missing}'. Must be one of 'raise', 'warn' or 'ignore'."
        )

    if column not in obj.columns:
        raise ValueError(f"column ('{column}') must be available in df")

    if groupby is None:
        groupby = set(obj.columns) - {column, "filename"}

    if column in groupby:
        raise ValueError(f"`groupby` may not contain column ('{column}')")

    groupby = list(groupby)

    # create a MultiIndex -> can directly index over multiple keys
    mi = pd.MultiIndex.from_frame(obj[groupby])

    # there are models with more than one grid
    if mi.has_duplicates:

        obj = _prioritize(obj, column, order, on_missing, mi)

        # double check
        mi = pd.MultiIndex.from_frame(obj[groupby])

        if mi.has_duplicates:
            raise ValueError("Something went wrong")

    return obj


def _prioritize(df, key, order, on_missing, multiindex):

    out = list()

    # loop entries
    for idx in multiindex.unique():

        one_ = df.iloc[multiindex.get_locs(idx)]

        # select the first that is found
        for element in order:
            if element in one_[key].values:

                selected = one_[one_[key] == element]

                if len(selected) != 1:
                    idx_string = one_.to_string()
                    raise ValueError(
                        f"Found more than one `df[{key}] == '{element}'` for\n{idx_string}"
                    )

                out.append(selected)
                break

        # no entry was found
        else:
            idx_string = one_.to_string()

            if on_missing == "raise":
                raise ValueError(
                    f"Did not find any element from the priority list for\n{idx_string}"
                )
            elif on_missing == "warn":
                warnings.warn(
                    f"Did not find any element from the priority list for\n{idx_string}"
                )
            elif on_missing == "ignore":
                pass

    df = pd.concat(out, axis=0)
    df = df.reset_index(drop=True)

    return df
