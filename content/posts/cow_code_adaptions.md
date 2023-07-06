---
title: Deep dive into pandas Copy-on-Write mode - part III
date: 2023-06-15
slug: cow-adaptions
tags: pandas
---

_Illustrating necessary adaptions for Copy-on-Write_


## Introduction

The introduction of Copy-on-Write (CoW) is a breaking change that will have some impact on
pandas-code. We will investigate how we can adapt our code to avoid errors when CoW will be
enabled by default. This is currently planned for the pandas 3.0 that is scheduled for April 2024.

We are planning on adding a warning mode that will warn for all operations that will change
behavior with CoW. This will be pretty noisy

## Chained assignment

Chained assignment is a technique where one object is updated through 2 subsequent operations. A
small example can be found here (TODO: Link).

```python
import pandas as pd

df = pd.DataFrame({"x": [1, 2, 3]})

df["x"][df["x"] > 1] = 100
```

The first operation selects the column ``"x"`` while the second operation restricts the number
of rows. There are many different combinations of these operations (e.g. combined with ``loc`` or
``iloc``). None of these combinations will work under CoW. Instead, they will raise a warning 
``ChainedAssignmentError`` to remove these patterns instead of silently doing nothing.

Generally, you can exchange these patterns through the usage of ``loc``:

```python
df.loc[df["x"] > 1, "x"] = 100
```

The first dimension of ``loc`` always corresponds to the ``row-indexer``. This means that you are
able to select a subset of rows. The second dimension corresponds to the ``column-indexer``, which
enables you to select a subset of columns. 

It is generally faster using ``loc`` when you want to set values into a subset of rows, so this
will clear up your code and bring a performance improvement.

This is the obvious case where CoW will have an impact. It will also impact chained inplace 
operations.

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

TODO link explained how the CoW mechanism works and how DataFrames share the underlying data. A
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
held by the initial object.

```python
df = df.reset_index()
df.iloc[0, 0] = 100
```

Summarizing, creating multiple references in the same method keeps unnecessary references alive.

Temporary references that are created when chaining different methods together are not an issue.

```python
df = df.reset_index().drop(...)
```

This will only keep one reference alive.

## Transition to NumPy arrays

TODO: read_only arrays
