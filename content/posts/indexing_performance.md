---
title: A guide to efficient data selection in pandas
date: 2023-02-10
slug: indexing-copy-view
tags: pandas
---

_Improve performance when selecting data from a pandas object_

## Introduction

There exist different ways of selecting a subset of data from a pandas object. Depending
on the specific operation, the result will either be a view pointing to the original
data or a copy of the original data. This ties directly to the efficiency of the operation. 
The copy and view rules are partially derived from the 
[NumPy advanced indexing rules](https://numpy.org/doc/stable/user/basics.indexing.html).
We will look at different operations and how to improve performance and efficiency as much as 
possible. [I am](https://github.com/phofl) a member of the pandas core team.

We will also investigate how 
[Copy on Write](https://medium.com/towards-data-science/a-solution-for-inconsistencies-in-indexing-operations-in-pandas-b76e10719744) 
will change the behavior for some operations to improve performance and avoid copies as much as 
possible.

## Dataset

We will use a dataset that contains all players from FIFA 2021. You can download the
dataset [here](https://www.kaggle.com/datasets/stefanoleone992/fifa-21-complete-player-dataset).

```python
import pandas as pd

df = pd.read_csv("players_21.csv", index_col="team_position").sort_index()
```

We set each player's position as index and sort the ``DataFrame`` by it.
This will allow faster and easier access to the players by position and will help us to
illustrate a few examples.

## Selecting a subset of rows

We start by selecting players by position from our dataset. There are a couple of ways to achieve
this. The most common might be selecting by a boolean mask. We can calculate the boolean mask 
to select all players with position ``"LS"`` through:

```python
mask = df.index == "LS"
```

Afterwards, we can extract the rows from our DataFrame by:

```python
result1 = df[mask]
result2 = df.loc[mask]
```

Both operations achieve the same result in this case. We will investigate the differences
when looking at modifying our DataFrame.

Selecting rows by a boolean mask __always__ creates a copy of the data. Depending on the
size of your dataset, this might cause a significant slowdown. Alternatively, we can select the
data by slicing the object:

```python
result = df.loc["LS"]
```

Slicing the object creates a view on the underlying data, which thus makes your operation
significantly faster. You can also select every second/n-th row by:

```python
result = df.iloc[slice(1, len(df), 2)]
```

This will also create a view pointing to the original object. Getting a view is generally preferable, because
it improves performance and reduces memory usage. On the other hand side, you could also
create a list of integers corresponding with our slice:

```python
result = df.iloc[list(range(1, len(df), 2))]
```

Selecting rows by a list of integers will create a copy, even though the operation look similar and
returns exactly the same data. This is again derived from NumPy's indexing rules.

Slicing has many applications, for example
by integer position, with a DatetimeIndex or slicing an Index with strings. Selecting data by 
slice, if possible, is significantly faster than with a list of integers or boolean masks.

Summarizing, depending on your use case, you may be able to significantly improve performance
when selecting rows. Setting an appropriate index might make your operations easier to
read and more efficient. 

## Selecting a subset of columns

There are generally two cases to consider when selecting columns from your DataFrame:

- selecting a single column
- selecting multiple columns

Selecting a single column is relatively straightforward, you can either use a regular __getitem__
or ``loc`` for this. There is no substantial difference for a single column when selecting data, 
only when we want to update said data.

```python
result = df["long_name"]
result = df.loc[:, "long_name"]
```

As soon as an iterable is passed to one of both calls, or if the selected column is duplicated,
we get a DataFrame back, but a copy of the underlying data is made, e.g.:

```python
result = df.loc[:, ["short_name", "long_name"]]
```

Selecting more than one column generally makes a copy right now. All these operations will return
views when ``Copy-on-Write`` is enabled. This will improve performance significantly for lager 
objects.

## Assigning data to a subset of the DataFrame

Let's look at how to update a subset of your DataFame efficiently. There are two general 
possibilities: A regular __setitem__ or using ``loc`` / ``iloc``.

When adding a new column to a DataFrame, I would suggest using a regular __setitem__ operation.
It is shorter and a bit easier to read. There is no substantial difference in both operations, e.g.:

```python
df["new_column"] = 100
```

There is a substantial difference when updating a DataFrame though. Assume we want to set the
name for all players with position ``"LS"`` in our object. A regular __setitem__ operation 
__never__ writes into the underlying array. The data of this column are copied before the update 
happens. Also, there is no way of updating a subset of a specific row in one operation. You'd have
to use chained assignment, which has its own pitfalls. We will investigate them later. 

```python
long_name = df[["long_name"]]
long_name[long_name.index == "LS"] = "Testname"
```

We are copying the whole column before updating all rows that have index ``"LS"`` inplace. This
is significantly slower that using ``loc`` / ``iloc``. Both methods update the underlying array
inplace if possible. Additionally, we don't have to use a boolean mask to achieve this.

```python
df.loc["LS", "long_name"] = "Testname"
```

In general, ``iloc`` is more efficient than ``loc``. The downside is, that you already have to
know the positions where you want to insert your new values. But if you want to update a specific
set of rows, using ``iloc`` is more efficient than ``loc``.

Setting values inplace without making a copy only works, if the dtype of the value/values to
set is compatible with the dtype of the underlying array. For example, setting integer values into
a float or object dtype column generally operates inplace. Setting a float value into an integer dtype
column has to copy the data as well. An integer column can't hold a float value, and hence the
data have to be cast into a dtype that can hold both values. As a side-note: There is an ongoing 
[discussion](https://github.com/pandas-dev/pandas/pull/50424)
about deprecating this behavior and raise an error, if an incompatible value is set into a column. It
would require casting the column explicitly to float before setting the values. Feedback on this
proposal is welcome!

There is one specific exception: When overwriting a whole column, using a regular __setitem__
is generally faster than using ``loc``.

```python
df["long_name"] = "Testname"
```

The reason for this is pretty simple: ``loc`` writes into the underlying array, which means that
you have to update every row for this column. The above operation simply swaps out the old column 
and adds the new column to the object without copying anything.

## Chained assignment

Chained assignment describes doing two indexing operations with one statement and then assigning
data to the selected subset, e.g.:

```python
df["long_name"][df.index == "LS"] = "Testname"
```

This operation updates the DataFrame accordingly. In general, chained assignment shouldn't be
used, because it is the frequent culprit behind the ``SettingWithCopyWarning``. Additionally,
chained assignment will raise an error with copy on write enabled globally or as soon as 
copy on write becomes the default.

## Performance comparison

Let's look at what this means performance-wise. This is just meant as a quick example to
show how to improve the efficiency of your data selections through avoiding copies. You'll have to 
tailor this to your application. ``loc`` and ``iloc`` are really flexible, so use-cases
will vary a lot. 

We need larger DataFrames
to avoid noise in our operations. We instantiate a DataFrame with random numbers:

```python
import numpy as np

df = pd.DataFrame(
    np.random.randint(1, 100, (1_000_000, 30)), 
    columns=[f"col_{i}" for i in range(30)],
)
```

Let's look what slicing vs. selecting a list of integers means performance-wise:

```python
%timeit df.loc[slice(10_000, 900_000)]
9.61 µs ± 493 ns per loop (mean ± std. dev. of 7 runs, 100,000 loops each)
%timeit df.loc[list(range(10_000, 900_000))]
68.2 ms ± 465 µs per loop (mean ± std. dev. of 7 runs, 10 loops each)
```

This is a pretty significant difference for a small change to your code.
Using ``iloc`` shows the same difference.

## Conclusion

You can speed up your data selection and data modification methods through choosing the
best method for your operation. Generally, using a slice to select rows from a DataFrame is
significantly faster than using a boolean mask or a list of integers. When setting values, you
have to be careful to use compatible values. Additionally, we can improve performance by using
``loc`` or ``iloc``, if we don't have a problem with modifying the underlying array.
