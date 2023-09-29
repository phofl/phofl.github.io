---
title: Deep dive into pandas Copy-on-Write mode - part III
date: 2023-09-29
slug: cow-adaptions
tags: pandas, copy-on-write
---

_Explaining the migration path for Copy-on-Write_


## Introduction

The introduction of Copy-on-Write (CoW) is a breaking change that will have some impact on existing
pandas-code. We will investigate how we can adapt our code to avoid errors when CoW will be
enabled by default. This is currently planned for the pandas 3.0 release, which is scheduled for April 2024.
[The first post](https://towardsdatascience.com/deep-dive-into-pandas-copy-on-write-mode-part-i-26982e7408c6) in this series explained the behavior of Copy-on-Write 
while [the second post](https://towardsdatascience.com/deep-dive-into-pandas-copy-on-write-mode-part-ii-b023432a5334) dove into performance optimizations that are related to Copy-on-Write.

We are planning on adding a warning mode that will warn for all operations that will change
behavior with CoW. The warning will be very noisy for users and thus has to be treated with some care.
This post explains common cases and how you can adapt your code to avoid changes in behavior.

## Chained assignment

Chained assignment is a technique where one object is updated through 2 subsequent operations.

```python
import pandas as pd

df = pd.DataFrame({"x": [1, 2, 3]})

df["x"][df["x"] > 1] = 100
```

The first operation selects the column ``"x"`` while the second operation restricts the number
of rows. There are many different combinations of these operations (e.g. combined with ``loc`` or
``iloc``). None of these combinations will work under CoW. Instead, they will raise a warning 
``ChainedAssignmentError`` to remove these patterns instead of silently doing nothing.

Generally, you can use ``loc`` instead:

```python
df.loc[df["x"] > 1, "x"] = 100
```

The first dimension of ``loc`` always corresponds to the ``row-indexer``. This means that you are
able to select a subset of rows. The second dimension corresponds to the ``column-indexer``, which
enables you to select a subset of columns. 

It is generally faster using ``loc`` when you want to set values into a subset of rows, so this
will clean up your code and provide a performance improvement.

This is the obvious case where CoW will have an impact. It will also impact chained inplace 
operations:

```python
df["x"].replace(1, 100)
```

The pattern is the same as above. The column selection is the first operation. The ``replace``
method tries to operate on the temporary object, which will fail to update the initial object.
You can also remove these patterns pretty easily through specifying the columns you want to
operate on.

```python
df = df.replace({"x": 1}, {"x": 100})
```

## Patterns to avoid

[My previous post](https://medium.com/towards-data-science/deep-dive-into-pandas-copy-on-write-mode-part-i-26982e7408c6) explains how the CoW mechanism works and how DataFrames share the underlying data. A
defensiv copy will be performed if two objects share the same data while you are modifying one
object inplace.

```python
df2 = df.reset_index()
df2.iloc[0, 0] = 100
```

The ``reset_index`` operation will create a view of the underlying data. The result is assigned to 
a new variable ``df2``, this means that two objects share the same data. This holds true until
``df`` is garbage collected. The ``setitem`` operation
will thus trigger a copy. This is completely unnecessary if you don't need the initial object 
``df`` anymore. Simply reassigning to the same variable will invalidate the reference that is
held by the object.

```python
df = df.reset_index()
df.iloc[0, 0] = 100
```

Summarizing, creating multiple references in the same method keeps unnecessary references alive.

Temporary references that are created when chaining different methods together are fine.

```python
df = df.reset_index().drop(...)
```

This will only keep one reference alive.

## Accessing the underlying NumPy array

pandas currently gives us access to the underlying NumPy array through ``to_numpy`` or ``.values``.
The returned array is a copy, if your DataFrame consists of different dtypes, e.g.:

```python
df = pd.DataFrame({"a": [1, 2], "b": [1.5, 2.5]})
df.to_numpy()

[[1.  1.5]
 [2.  2.5]]
```

The DataFrame is backed by two arrays which have to be combined into one. This triggers the copy.

The other case is a DataFrame that is only backed by a single NumPy array, e.g.:

```python
df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
df.to_numpy()

[[1 3]
 [2 4]]
```

We can directly access the array and get a view instead of a copy. This is much faster than copying
all data. We can now operate on the NumPy array and potentially modify it inplace, which will also
update the DataFrame and potentially all other DataFrames that share data. This becomes much more
complicated with Copy-on-Write, since we removed many defensive copies. Many more DataFrames will 
now share memory with each other.

``to_numpy`` and ``.values`` will return a read-only array because of this. This means that the
resulting array is not writeable.

```python
df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
arr = df.to_numpy()

arr[0, 0] = 1
```

This will trigger a ``ValueError``:

```python
ValueError: assignment destination is read-only
```

You can avoid this in two different ways:

- Trigger a copy manually if you want to avoid updating DataFrames that share memory with your array.
- Make the array writeable. This is a more performant solution but circumvents Copy-on-Write rules, so
  it should be used with caution.

```python
arr.flags.writeable = True
```

There are cases where this is not possible. One common occurrence is, if you are accessing a single
column which was backed by PyArrow:

```python
ser = pd.Series([1, 2], dtype="int64[pyarrow]")
arr = ser.to_numpy()
arr.flags.writeable = True
```

This returns a ``ValueError``:

```python
ValueError: cannot set WRITEABLE flag to True of this array
```

Arrow arrays are immutable, hence it is not possible to make the NumPy array writeable. The conversion
from Arrow to NumPy is zero-copy in this case.

## Conclusion

We've looked at the most invasive Copy-on-Write related changes. These changes will become the
default behavior in pandas 3.0. We've also investigated how we can adapt our code to avoid breaking
our code when Copy-on-Write is enabled. The upgrade process should be pretty smooth if you can avoid
these patterns.
