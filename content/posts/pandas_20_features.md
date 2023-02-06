---
title: How to utilize new features in pandas
date: xxx
slug: pandas-20
tags: pandas
---


## Introduction

There are many new features in pandas 2.0, including significantly improved extension array
support, pyarrow support for DataFrames and non-nanosecond datetime resolution. Before we get
to the ways on how to improve your workflow, we take a look at all the deprecations that were
enforced.

## API changes

The 2.0 release was a major release, hence all deprecations added in the 1.x series were enforced.
There were around 150 warnings in the latest 1.5.3 release. We will just have a quick look at some
subtle or more noticeable deprecations before jumping into the new features.

### Index now supports arbitrary NumPy dtypes

Before the 2.0 release, an Index only supported ``int64``, ``float64`` and ``uint64`` which resulted
in an ``Int64Index``, ``Float64Index`` or ``UInt64Index``. These classes where removed. All numeric
indexes are now represented as ``Index`` with an associated dtype, e.g.:

````python
In [4]: pd.Index([1, 2, 3], dtype="int64")
Out[4]: Index([1, 2, 3], dtype='int64')
pd.Index([1, 2, 3], dtype="int32")
Out[5]: Index([1, 2, 3], dtype='int32')
````

This mirrors the behavior for extension arrays. You could store arbitrary masked dtypes in an
Index since pandas 1.4.0. You can check the 
[release notes](https://pandas.pydata.org/docs/dev/whatsnew/v2.0.0.html#index-can-now-hold-numpy-numeric-dtypes) 
for further information.

### Behavior change in ``numeric_only`` for aggregation functions

In previous versions you could call aggregation functions on a DataFrame with mixed-dtypes and
got mixed results. Sometimes the aggregation worked and excluded non-numeric dtypes, in some
other cases an error was raised. The ``numeric_only`` argument is now consistent and the aggregation
will raise, if you apply it on a DataFrame with non-numeric dtypes. You can set ``numeric_only``
to ``True`` or restrict your DataFrame to numeric columns, if you want to get the same behavior
as before. This will avoid accidentally dropping relevant columns from the object.

## Improved support for nullable dtypes

TODO

## Arrow-backed DataFrames

TODO

## Non-nanosecond resolution in Timestamps

TODO

## Copy on write improvements

TODO

## Conclusion

TODO

