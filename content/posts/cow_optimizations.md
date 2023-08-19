---
title: Deep Dive into pandas Copy-on-Write Mode - Part II
blogpost: true
date: 2023-08-17
slug: cow-deep-dive-optimizations
tags: pandas, copy-on-write, performance
---

_Explaining how Copy-on-Write optimizes performance_

## Introduction

The [first post](https://medium.com/towards-data-science/deep-dive-into-pandas-copy-on-write-mode-part-i-26982e7408c6) 
explained how the Copy-on-Write mechanism works. It highlights some ares where copies are introduced
into the workflow. This post will focus
on optimizations that ensure that this won't slow the average workflow down.

We utilize a technique that pandas internals use to avoid copying the whole DataFrame when it's not 
necessary and thus, increase performance. 

## Removal of defensive copies

Let's start with the most impactful improvement. Many pandas methods performed defensive copies
to avoid side effects to protect against inplace modifications later on.

```python
df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
df2 = df.reset_index()
df2.iloc[0, 0] = 100
```

There is no need to copy the data in ``reset_index``, but returning a view would introduce side
effects when modifying the result, e.g. ``df`` would be updated as well. Hence, a defensiv copy is
performed in ``reset_index``. 

All these defensive copies are no longer there when Copy-on-Write is enabled. This affects many
methods. A full list can be found [here](https://pandas.pydata.org/docs/user_guide/copy_on_write.html#copy-on-write-optimizations).

Additionally, selecting a columnar subset of a DataFrame will now always return a view instead of
a copy as before.

Let's look at what this means performance-wise when we combine some of these methods:

```python
import pandas as pd
import numpy as np

N = 2_000_000
int_df = pd.DataFrame(
    np.random.randint(1, 100, (N, 10)), 
    columns=[f"col_{i}" for i in range(10)],
)
float_df = pd.DataFrame(
    np.random.random((N, 10)), 
    columns=[f"col_{i}" for i in range(10, 20)],
)
str_df = pd.DataFrame(
    "a", 
    index=range(N), 
    columns=[f"col_{i}" for i in range(20, 30)],
)

df = pd.concat([int_df, float_df, str_df], axis=1)
```

This creates a DataFrame with 30 columns, 3 different dtypes and 2 million rows. Let's execute
the following method chain on this DataFrame:

```python
%%timeit
(
    df.rename(columns={"col_1": "new_index"})
    .assign(sum_val=df["col_1"] + df["col_2"])
    .drop(columns=["col_10", "col_20"])
    .astype({"col_5": "int32"})
    .reset_index()
    .set_index("new_index")
)
```

All of these methods perform a defensiv copy without CoW enabled.

**Performance without CoW:**
```
2.45 s ± 293 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
```
--

**Performance with CoW enabled:**

```
*13.7 ms ± 286 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
```

An improvement by roughly a factor of 200. I chose this example explicitly to illustrate the
potential benefits of CoW. Not every method will get that much faster.

## Optimizing copies triggered by inplace modifications

The previous section illustrated many methods where a defensiv copy is no longer necessary.
CoW guarantees that you can't modify two objects at once. This means that we have to introduce
a copy when the same data is referenced by two DataFrames. Let's look at techniques to make
these copies as efficient as possible.

The previous post showed that the following might trigger a copy:

```python
df.iloc[0, 0] = 100
```

The copy is triggered if the data that is backing ``df`` is referenced by another DataFrame.
We assume that our DataFrame has ``n`` integer columns, e.g. is backed by a single Block.

![](../images/deep_dive_cow/optimizations/cow_one_block.svg)

Our Reference tracking object is also referencing another Block, so we can not modify the DataFrame
inplace without modifying another object. A naive approach would be to copy the whole block and be
done with it.

![](../images/deep_dive_cow/optimizations/cow_one_block_naive.svg)

This would set up a new reference tracking object and create a new Block that is backed by a fresh
NumPy array. This Block doesn't have any more references, so another operation would be able to 
modify it inplace again. This approach copies ``n-1`` columns that we don't necessarily have to 
copy. We utilize a technique we call Block splitting to avoid this.

![](../images/deep_dive_cow/optimizations/cow_one_block_splitting.svg)

Internally, only the first column is copied. All other columns are taken as views on the previous 
array. The new Block does not share any references with other columns. The old Block still shares
references with other objects since it is only a view on the previous values.

There is one disadvantage to this technique. The initial array has ``n`` columns. We created a
view on columns ``2`` till ``n``, but this keeps the whole array alive. We also added a new array
with one column for the first column. This will keep a bit more memory alive than necessary. 

This system directly translates to DataFrames with different dtypes. All Blocks that are not
modified at all are returned as is and only Blocks that are modified inplace are split.

![](../images/deep_dive_cow/optimizations/cow_two_blocks.svg)

We now set a new value into column ``n+1`` the float Block to create a view on columns ``n+2``
to ``m``. The new Block will only back column ``n+1``.

```python
df.iloc[0, n+1] = 100.5
```

![](../images/deep_dive_cow/optimizations/cow_two_blocks_split.svg)

## Methods that can operate inplace

The indexing operations we looked at don't generally create a new object; they modify
the existing object inplace, inlcuding the data of said object. Another group of pandas methods does
not touch the data of the DataFrame at all. One prominent example is ``rename``. Rename only changes
the labels. These methods can utilize the lazy-copy mechanism mentioned above.

There is another third group of methods that can actually be done inplace, like ``replace`` or
``fillna``. These will always trigger a copy.

```python
df2 = df.replace(...)
```

Modifying the data inplace without triggering a copy would modify ``df`` and ``df2``, which violates
CoW rules. This is one of the reasons why we consider keeping the ``inplace`` keyword for these
methods.

```python
df.replace(..., inplace=True)
```

This would get rid of this problem. It's still an open proposal and might go into a different
direction. That said, this only pertains to columns that are actually
changed; all other columns are returned as views anyway. This means that only one column is copied
if your value is only found in one column.

## Conclusion

We investigate how CoW changes pandas internal behavior and how this will translate to improvements
in your code. Many methods will get faster with CoW, while we will see a slowdown in a couple of
indexing related operations. Previously, these operations always operated inplace, which might have
produced side effects. These side effects are gone with CoW and a modification on one DataFrame 
object will never impact another.

The next post in this series will explain how you can update your code to be compliant
with CoW. Also, we will explain which patterns to avoid in the future.

Thank you for reading. Feel free to reach out to share your thoughts and feedback 
about Copy-on-Write.
