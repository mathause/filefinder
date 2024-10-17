import pandas as pd
import parse

from filefinder.filters import priority_filter

# select preferred grid; order indicates priority
VALID_GRIDS = ("gn", "gr", "gr1", "gm")


def parse_ens(filelist):

    ens = filelist.df["ens"]

    # for cmip6
    if "f" in ens.iloc[0]:
        parser = parse.compile("r{r}i{i}p{p}f{f}")
    # for cmip5
    else:
        parser = parse.compile("r{r}i{i}p{p}")

    out = list()
    for i, one_ens in zip(ens.index, ens):
        parsed = parser.parse(one_ens)
        out.append(list(parsed.named.values()))

    keys = list(parsed.named.keys())

    df = pd.DataFrame(out, columns=keys)

    for key in df.columns:
        filelist.df[key] = df[key].values

    return filelist


def create_ensnumber(filelist, keys=None):

    if keys is None:
        keys = ("exp", "table", "varn", "model")

    keys = list(keys)
    df = filelist.df
    multiindex = pd.MultiIndex.from_frame(df[keys])

    df["ensnumber"] = -1

    for idx in multiindex.unique():

        sel = multiindex == idx
        numbers = list(range(sel.sum()))
        df.loc[sel, "ensnumber"] = numbers

    filelist.df = df
    return filelist


def ensure_unique_grid(filelist):
    """ensure there is only one grid per simulation"""

    # each simulation must be unique in the combination of these keys
    keys = ("exp", "table", "varn", "model", "ens")

    return priority_filter(filelist, column="grid", order=VALID_GRIDS, groupby=keys)
