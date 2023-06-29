---
title: Deep dive into pandas Copy-on-Write mode - part II
date: 2023-06-15
slug: cow-deep-dive
tags: pandas
---

_Showing some internal performance optimizations_

My previous post (TODO: Link) explained how the Copy-on-Write mechanism works. We will now focus
on some optimizations that make it faster and more efficient.

We will look at a technique that pandas internals use to avoid copying the whole DataFrame and
thus, increase performance. 

## Optimizing copies triggered by inplace modifications

The previous post showed that the following might trigger a copy:

```python
df.iloc[0, 0] = 100
```

The copy is triggered if the data that are backing ``df`` are referenced by another DataFrame.
We assume that our DataFrame has ``n`` integer columns, e.g. is backed by a single Block.

![](../images/deep_dive_cow/optimizations/cow_one_block.svg)

Our Reference tracking object is also referencing another Block, so we can not update the DataFrame
inplace without modifying another object. A naive approach would be to copy the whole block and be
done with it.

![](../images/deep_dive_cow/optimizations/cow_one_block_naive.svg)

This would set up a new reference tracking object and create a new Block that is backed by a fresh
NumPy array. This Block doesn't have any more references, so another operation would be able to 
modify it inplace again. This approach copies ``n-1`` columns that we don't necessarily have to 
copy. We utilize a technique we call Block splitting to improve performance.

![](../images/deep_dive_cow/optimizations/cow_one_block_splitting.svg)

Internally, only the first column is copied. All other columns are taken as views on the previous 
array. The new Block does not share any references with other columns. The old Block still shares
references with other objects since it is only a view on the previous values.

There is one disadvantage to this technique. The initial array has ``n`` columns. We created a
view on columns ``2`` till ``n``, but this keeps the whole array alive. We also added a new array
with one column for the first column. This will keep a bit more memory alive than necessary. 