---
title: pandas internals explained
date: 2023-06-15
slug: pandas-internals
tags: pandas
---

_Explaining the pandas data model and its advantages_

## Introduction

pandas enables you to choose between different types of arrays to represent the data of your
DataFrame. Historically, most DataFrames are backed by NumPy arrays. [pandas 2.0 introduced the 
option to use PyArrow arrays](https://medium.com/gitconnected/welcoming-pandas-2-0-194094e4275b) as a storage format. 
There exists an intermediate layer between these arrays and your DataFrame, Blocks and the
BlockManager. We will take a look at how this layer orchestrates the different arrays, basically
what's behind ``pd.DataFrame()``. We will try to answer all questions you might have about pandas 
internals.

The post will introduce some terminology that is necessary to understand how Copy-on-Write works,
which is something I'll write about next.

## pandas data structure

A DataFrame is usually backed by some sort of array, e.g. a NumPy array or 
pandas ExtensionArray. These arrays store the data of the DataFrame. pandas adds an intermediate 
layer, called ``Block`` and ``BlockManager`` that orchestrate these arrays to make operations as 
efficient as possible. This is one of the reasons why methods that operate on multiple columns can 
be very fast in pandas. Let's look a bit more into the details of these layers.

### Arrays

The actual data of a DataFrame can be stored in a set of NumPy arrays or pandas ExtensionArrays. 
This layer generally dispatches to the underlying implementation, e.g. it will utilize the NumPy 
API if the data is stored in NumPy arrays. pandas simply stores the data in them and calls its 
methods without enriching the interace. You can read up on pandas 
ExtensionArrays [here](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.extensions.ExtensionArray.html).

NumPy arrays are normally 2-dimensional, which offers a bunch of performance advantages that we
will take a look at later. pandas ExtensionArrays are mostly one-dimensional data structures as
of right now. This makes things a bit more predictable but has some drawbacks when looking at
performance in a specific set of operations. ExtensionArrays enable DataFrames that are backed by
PyArrow arrays among other dtypes.

### Blocks

A DataFrame normally consists of a set of columns that are represented by at least one array, 
normally you'll have a collection of arrays since one array can only store one specific dtype.
These arrays store your data but don't have any information about which columns they are
representing. Every array from your DataFrame is wrapped by one corresponding ``Block``. Blocks
add some additional information to these arrays like the column locations that are represented
by this Block. Blocks serve as a layer around the actual arrays that can be enriched with utility methods
that are necessary for pandas operations.

When an actual operation is executed on a DataFrame, the Block ensures that the method dispatches
to the underlying array, e.g. if you call ``astype``, it will make sure that this operation is
called on the array.

This layer does not have any information about the other columns in the DataFrame. It is a stand-alone
object.

### BlockManager

As the name suggests, the ``BlockManager`` orchestrates all Blocks that are connected to one 
DataFrame. It holds the Blocks itself and information about your DataFrame's axes, e.g. column names
and Index labels. Most importantly, it dispatches most operations to the actual Blocks.

```python
df.replace(...)
```

The BlockManager ensures that ``replace`` is executed on every Block.

## What is a consolidated DataFrame

We are assuming that the DataFrames is backed by NumPy dtypes, e.g. that it's data can be stored
as two-dimensional arrays.

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

Now let's add a new column to this DataFrame:

```python
df["new"] = 100
```

This will have the same dtype as our existing column ``"a"`` and ``"c"``. There are now two potential
ways of moving forward:

1. Add the new column to the existing array that holds the integer columns
2. Create a new array that only stores the new column.

The first option would require us to add a new column to the existing array. This would require copying
the data since NumPy does not support this operation without a copy. This is obviously a pretty steep
cost for simply adding one column.

The second option adds a third array to our collection of arrays. Apart from this, no additional 
operation is necessary. This is very cheap. We now have 2 Blocks that store integer data. This is
a DataFrame that is not consolidated.

These differences don't matter much as long as you are only operating on a per-column basis. It
will impact the performance of your operations as soon as they operate on multiple columns.
For example, performing any ``axis=1`` operation will transpose the data of your DataFrame. 
Transposing is generally zero-copy if performed on a DataFrame that is backed by a single NumPy
array. This is no longer true if every column is backed by a different array and hence, will incur
performance penalties.

It will also require a copy when you want to get all integer columns from your DataFrame as a 
NumPy array.

```python
df[["a", "c", "new"]].to_numpy()
```

This will create a copy since the results have to be stored in a single NumPy array. It returns
a view on a consolidated DataFrame, which makes this very cheap.

Previous versions often caused an internal consolidation for certain methods, which in turn caused 
unpredictable performance behavior. Methods like ``reset_index`` were triggering a completely
unnecessary consolidation. These were mostly removed over the last couple of releases.

Summarizing, a consolidated DataFrame is generally better than an unconsolidated one, but the 
difference depends heavily on the type of operation you want to execute.

# Conclusion

We took a brief look behind the scenes of a pandas DataFrame. We learned what ``Blocks`` and
``BlockManagers`` are and how they orchestrate your DataFrame. These terms will prove valuable
when we take a look behind the scenes of 
[Copy-on-Write](https://medium.com/towards-data-science/a-solution-for-inconsistencies-in-indexing-operations-in-pandas-b76e10719744).

Thank you for reading. Feel free to reach out to share your thoughts and feedback.
