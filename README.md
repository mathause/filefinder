# FileFinder

_Find and parse file and folder names._

Define regular folder and file patterns with the intuitive python syntax:

```python
from filefinder import FileFinder

path_pattern = "/root/{category}"
file_pattern = "{category}_file_{number}"

ff = FileFinder(path_pattern, file_pattern)
```

## Create file and path names

Everything enclosed in curly brackets is a placeholder. Thus, you can create file and
path names like so:

```python
ff.create_path_name(category="a")
>>> /root/a/

ff.create_file_name(category="a", number=1)
>>> a_file_1

ff.create_full_name(category="a", number=1)
>>> /root/a/a_file_1
```

## Find files on disk

However, the strength of filefinder is parsing file names on disk. Assuming you have the
following folder structure:

```
/root/a1/a1_file_1
/root/a1/a1_file_2
/root/b2/b2_file_1
/root/b2/b2_file_2
/root/c3/c3_file_1
/root/c3/c3_file_2
```

You can then look for paths:

```python
ff.find_paths()
>>> <FileContainer>
>>>      filename category
>>> 0  /root/a1/*       a1
>>> 1  /root/b2/*       b2
>>> 2  /root/c3/*       c3
```
The placeholders (here `{category}`) is parsed and returned. You can also look for
files:

```python
ff.find_files()
>>> <FileContainer>
>>>              filename category number
>>> 0  /root/a1/a1_file_1       a1      1
>>> 1  /root/a1/a1_file_2       a1      2
>>> 2  /root/b2/b2_file_1       b2      1
>>> 3  /root/b2/b2_file_2       b2      2
>>> 4  /root/c3/c3_file_1       c3      1
>>> 5  /root/c3/c3_file_2       c3      2
```

It's also possible to filter for certain files:
```python
ff.find_files(category=["a1", "b2"], number=1)
>>> <FileContainer>
>>>              filename category number
>>> 0  /root/a1/a1_file_1       a1      1
>>> 2  /root/b2/b2_file_1       b2      1
```

Often we need to be sure to find _exactly one_ file or path. This can be achieved using

```python
ff.find_single_file(category="a1", number=1)
>>> <FileContainer>
>>>              filename category number
>>> 0  /root/a1/a1_file_1       a1      1
```

If none or more than one file is found a `ValueError` is raised.

## Format syntax

You can pass format specifiers to allow more complex formats, see
[format-specification](https://github.com/r1chardj0n3s/parse#format-specification) for details.
Using format specifiers, you can parse names that are not possible otherwise.

### Example

```python
from filefinder import FileFinder

paths = ["a1_abc", "ab200_abcdef",]

ff = FileFinder("", "{letters:l}{num:d}_{beg:2}{end}", test_paths=paths)

fc = ff.find_files()

fc
```

which results in the following:

```python
<FileContainer>
       filename letters  num beg   end
0        a1_abc       a    1  ab     c
1  ab200_abcdef      ab  200  ab  cdef
```

Note that `fc.df.num` has now a data type of `int` while without the `:d` it would be an
string (or more precisely an object as pandas uses this dtype to represent strings).


## Filters

Filters can postprocess the found paths in `<FileContainer>`. Currently only a `priority_filter`
is implemented.

### Example

Assuming you have data for several models with different time resolution, e.g., 1 hourly
(`"1h"`), 6 hourly (`"6h"`), and daily (`"1d"`), but not all models have all time resolutions:

```
/root/a/a_1h
/root/a/a_6h
/root/a/a_1d

/root/b/b_1h
/root/b/b_6h

/root/c/c_1h
```

You now want to get the `"1d"` data if available, and then the `"6h"` etc.. This can be achieved with the `priority filter`. Let's first parse the file names:

```python
ff = FileFinder("/root/{model}", "{model}_{time_res}")

files = ff.find_files()
files
```

which yields:

```
<FileContainer>
       filename model time_res
0  /root/a/a_1d     a       1d
1  /root/a/a_1h     a       1h
2  /root/a/a_6h     a       6h
3  /root/b/b_1h     b       1h
4  /root/b/b_6h     b       6h
5  /root/c/c_1h     c       1h
```

We can now apply a `priority_filter` as follows:

```python
from filefinder.filters import priority_filter

files = priority_filter(files, "time_res", ["1d", "6h", "1h"])
files
```

Resulting in the desired selection:

```
       filename model time_res
0  /root/a/a_1d     a       1d
1  /root/b/b_6h     b       6h
2  /root/c/c_1h     c       1h
```
