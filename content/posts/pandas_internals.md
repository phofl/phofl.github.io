---
title: pandas internals: Lets talk about Blocks
date: 2023-06-15
slug: pandas-internals
tags: pandas
---

## Introduction

This post will show how a pandas DataFrame is constructed internally. We will take a look at what 
is behind ``pd.DataFrame()`` and try to answer all questions you might have about pandas internals.

We will go into some terminology that is necessary to understand how Copy-on-Write works.

## pandas data structure

The data that back a DataFrame are usually stored as some sort of array, e.g. a NumPy array or 
pandas ExtensionArray. pandas adds an intermediate layer, called ``Block`` and the ``BlockManager`` 
that orchestrate these arrays to make operations efficient. This is one of the reasons why stuff
that operates on multiple columns can be very fast in pandas.

### Arrays

The actual data of a DataFrame can be stored in a set of NumPy arrays or pandas ExtensionArrays. 
This layer is not very interesting since it just holds your data. You can read up on pandas 
ExtensionArrays [here](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.extensions.ExtensionArray.html).

NumPy arrays are normally 2-dimensional, which offers a bunch of performance advantages that we
will take a look at later. pandas ExtensionArrays are mostly one-dimensional data structures as
of right now. This makes things a bit more predictable but has some drawbacks when looking at
performance in a specific set of operations.

### Blocks

A DataFrame normally consists of at least one array, normally you a collection of arrays since one
array stores only one specific dtype.
These arrays just store your data but don't have any information about which column they are
representing. One ``Block`` wraps one of these arrays and has some additional information about it.
Most importantly, it stores which columns it represents. This information is stored as a positional
index. This serves as a layer around the actual arrays that can be enriched with utility methods
that are necessary for pandas operations.

When an actual operation is executed on a DataFrame, the Block ensures that the method is excuted
on the underlying array, e.g. if you call ``astype``, it will make sure that this operation is
executed on the array.

This layer does not have any information about the other columns in the DataFrame. It is a stand-alone
object.

### BlockManager

As the name suggests, the ``BlockManager`` orchestrates all blocks that are connected to one 
DataFrame. It holds the Blocks itself and information about your DataFrame axes, e.g. column names
and Index labels. Most importantly, it dispatches most operations to the actual blocks, e.g.:
you do 

```python
df.replace(...)
```

The BlockManager ensures that ``replace`` is executed on every Block.

# What is a consolidated DataFrame

We are assuming that the DataFrames is backed by NumPy dtypes, e.g. that that data can be stored
in two dimensional arrays.

When a DataFrame is constructed, pandas mostly ensures that there is only one Block per dtype.

```python
df = pd.DataFrame(
    {
        "a": [1, 2, 3],
        "b": [1.5, 2.5, 3.5],
        "c": [10, 11, 12],
        "d": [10.5, 11.5, 12.5],
    }
)
```

This DataFrame has 4 columns which are represented by 2 arrays, one of the arrays stores the integer
dtypes while the other stores the float dtypes. This is a _consolidated_ DataFrame.

Now lets add a new column to this DataFrame:

```python
df["new"] = 100
```

This will have the same dtype as our existing column ``"a"`` and ``"c"``. There are now two potential
ways of moving forward:

1. Add the new column to the existing array that holds the integer columns
2. Create a new array that only stores the new column.

The first option would require us to add a new column to the existing array, which requires copying
the data since NumPy does not support this operation without a copy. This is obviously a pretty steep
cost for simply adding one column.

The second option adds a third array to our collection of arrays. Apart from this, no additional 
operation is necessary. This is very cheap. We now have 2 Blocks that store integer data. This is
a DataFrame that is not consolidated.

These differences don't matter much as long as you are only operating on a per-column basis. This is
a bit different as soon as you want to perform operations on multiple columns.

This layout requires a copy when you want to get all integer columns from you DataFrame.

```python
df[["a", "c", "new"]].to_numpy()
```

This will create a copy since the results have to be stored in a single NumPy array, this operation
returns only a view if the DataFrame is consolidated and thus is very cheap.

Previous versions often caused an internal consolidation for certain methods which caused 
unpredictable performance behavior. Methods like ``reset_index`` were triggering a completely
unnecessary consolidation. We got rid of these over the last couple of releases!

Summarizing, a consolidated DataFrame is generally better than an unconsolidated one, but this is only
triggered if a copy is necessary under the hood. 

# Conclusion


