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

## Improvements and new features

Let's look at some general improvements and newly introduced features. 

### Improved support for nullable dtypes and extension arrays

The 2.0 release brings a vast improvement for nullable dtypes and extension arrays in general.
Internally, many operations now use nullable semantics instead of casting to object when
using nullable dtypes like ``Int64``, ``boolean`` or ``Float64``. This is visible through
either vast performance improvements:

TODO: Add unique example

Additionally, many operations now properly operate on the nullable arrays which maintains the
appropriate dtype when returning the result. All groupby algorithms now use nullable semantics,
which results in better accuracy (previously the input was cast to float which might have let
to loss of precision) and performance improvement.

Most I/O methods like ``read_csv`` gained a new keyword ``use_nullable_dtypes`` which returns
a ``DataFrame`` completely backed by nullable dtypes. These keywords can be set to ``True`` through
the global option ``nullable_dtypes``. This simplifies opting into nullable dtypes
globally.

The ``Index`` and ``MultiIndex`` classes are now better integrated with Extension
Arrays in general. General Extension Array support was introduced in 1.4. The implementation is now
mostly complete with 2.0, this includes:

- Efficient Indexing operations on nullable and pyarrow dtypes
- No materialization of MultiIndexes to improve performance and maintain dtypes

The Extension Array interface is continuously improved to avoid materializing NumPy arrays and
rely more on the provided Extension Arrays. Some areas are still under development, including 
GroupBy aggregations.

### Pyarrow-backed DataFrames

Version 1.5.0 brought a new Extension Array to pandas that allowed users to create ``DataFrames``
backed by pyarrow arrays. We expect these Extension Arrays to provide a vast improvement when
operating on string-columns, since the NumPy object representation is not performant. This is not
that different from the dtype ``string[pyarrow]`` that has been around for quite some time. The
pyarrow-specific Extension Array supports all other pyarrow dtypes on top of it. Users can now
create columns with any pyarrow dtypen and use pyarrow nullable semantics. Those
come out of the box when using pyarrow dtypes. A pyarrow-backed column can be requested 
specifically by casting or specifying a column's dtype as ``f"{dtype}[pyarrow]"``, e.g. 
``"int64[pyarrow]"`` for an integer column. Alternatively, an pyarrow dtype can be created through:

```python
import pandas as pd
import pyarrow as pa

dtype = pd.ArrowDtype(pa.int64)
```

The API in 1.5.0 was pretty raw and experimental and fell back to NumPy quite often. With pandas 2.0 and an 
increased minimum version of pyarrow (7.0 for pandas 2.0), we can now utilize the corresponding pyarrow compute 
functions in many more methods. This improves performance significantly and gets rid of many
``PerformanceWarnings`` that were raised before when falling back to NumPy. Similarly to the
nullable dtypes, most I/O methods can return pyarrow-backed DataFrames through the keyword
``use_nullable_dtypes`` and setting the global option ``dtype_backend`` to pyarrow:

```python
import pandas as pd

pd.options.mode.dtype_backend = "pyarrow"
```

Future versions of pandas will bring many more improvements in this area!

Some I/O methods have specific pyarrow engines, like ``read_csv`` and ``read_json``, which bring
a significant performance improvement. They don't support all options that the original 
implementations support yet. TODO: Add link to Marcs blog

Marc is also working on a post to illustrate how to use pyarrow-backed DataFrames to interoperate
with other DataFrame libraries that utilize the arrow-standard.

### Non-nanosecond resolution in Timestamps

TODO

### Copy-on-Write improvements

Copy-on-Write was originally introduced in pandas 1.5.0. See TODO: link to my post for a detailed
description what Copy-on-Write means for pandas. 

> __Short summary:__
> 
> __Any DataFrame or Series derived from another in__ 
> __any way always behaves as a copy__. As a consequence, we can only change the values of an object 
> through modifying the object itself. CoW disallows updating a DataFrame or a Series that shares 
> data with another DataFrame or Series object inplace.

Version 1.5 provided the general mechanism but not much apart from that. A couple of bugs were
discovered and fixed since then where Copy-on-Write was not respected and hence two objects could 
get modified with one operation.

More importantly, nearly all methods now utilize a _lazy copy_ mechanism to avoid copying the
underlying data as long as possible. Up until now, most methods performed defensive copies to avoid
side effects when an object would get modified later on. This resulted in high memory usage and
relatively slow performance. Copy-on-Write enables us to remove all defensive copies and defer
the actual copies till the data of an object are modified.

Copy-on-Write provides a cleaner and easier to work with API and should give your code a
performance boost on top of it. If your code does not rely on updating more than one object at
once and does not utilize chained assignment, then there isn't a big risk in turning Copy-on-Write 
on. I've tested it on some code-bases and saw promising performance improvements, so I'd recommend
trying it out to see how it impacts your code. Copy-on-Write will probably be
made the default in pandas 3.0. I'd recommend developing new features with Copy-on-Write enabled
to avoid having to migrate later on.

A PDEP (pandas developmen enhancement proposal) was submitted to deprecate and remove the
``inplace`` and ``copy`` keyword in most methods. These would become obsolete with Copy-on-Write
enabled and would only add confusion for user. You can follow this discussion 
[here](https://github.com/pandas-dev/pandas/pull/51466).

## Conclusion

pandas 2.0 brings many new and exiting features. We've seen a couple of them and looked at how
to utilize them. There is currently an ongoing d
