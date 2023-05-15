---
title: Leverage PyArrow in pandas and Dask
date: 2023-04-25
slug: pyarrow-pandas-dask
tags: pandas
---

_Get the most out of PyArrow support in pandas and Dask right now_

## Introduction

Support for PyArrow dtypes in pandas, and by extension Dask, is still relatively fresh. I would 
still recommend caution when option into the PyArrow dtype backend, since not every part of the 
pandas API is optimized yet. You should be able to get a big improvement with a bit of awareness 
though. I will go through a bunch of examples where switching to PyArrow is highly recommended. I 
am part of the pandas core team and was heavily involved in implementing and improving PyArrow 
support in pandas. I've recently joined [Coiled](https://www.coiled.io) where I am working on Dask.

## Dataset

We will use the taxi dataset from New York City that provides all Uber and Lyft rides, including
some interesting attributes like price, tips, driver pay and many more. The dataset can be found
[here](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) and is stored as parquet
files. When analyzing Dask queries, we will use a publicly available S3 bucket to simplify our
queries: ``s3://coiled-datasets/uber-lyft-tlc/``. We will use the datasets of the final quarter of 
2022 for our pandas queries, since this is the maximum that fits comfortably into memory on my 
machine (24GB of RAM). Stressing our RAM usage might introduce side effects when analyzing 
performance otherwise.

## Dask cluster

There is a multitude of different options to set up a Dask cluster, see the 
[Dask documentation](https://docs.dask.org/en/stable/deploying.html) for
a non-exhaustive list of deployment options. I will use 
[Coiled](https://docs.coiled.io/user_guide/index.html) to create a cluster on AWS with
30 machines through:

```python
import coiled

cluster = coiled.Cluster(
    n_workers=30,
    name="dask-performance-comparisons",
    region="us-east-2",  # this is the region of our dataset
)
```

Coiled is connected to my AWS account. It creates the cluster within my account and manages the
resources for me. 30 machines are enough to comfortably operate on our dataset. We will investigate
how we can reduce the required amount of workers to 15 instead of 30 through small modifications.

## pandas StringDtype with PyArrow backing

TODO

## engine keyword in I/O methods

We start by taking a look at I/O functions in pandas. Some functions have custom implementations, 
like ``read_csv``, while others dispatch to another library, like ``read_excel`` does to 
``openpyxl``. Some functions gained a new ``engine`` keyword that enables users to dispatch to 
``PyArrow``. The PyArrow parsers are multithreaded by default and hence, can provide a significant 
performance improvement.

TODO example

The engines were added to provide users a faster way of reading data. The improved speed is only
one of the advantages. The Arrow readers return the data as a 
[PyArrow Table](https://arrow.apache.org/docs/python/generated/pyarrow.Table.html). A PyArrow Table
provides built-in functionality to convert to a pandas ``DataFrame``. Depending on the data, this
might require a copy while casting to NumPy (string, integers with missing values, ...), which
brings an unnecessary slowdown. This is where the PyArrow ``dtype_backend`` from pandas comes in.
It is implemented as an ``ArrowExtensionArray`` class in pandas, which is backed by a 
[PyArrow ChunkedArray](https://arrow.apache.org/docs/python/generated/pyarrow.ChunkedArray.html).
As a direct consequence, the conversion from a PyArrow Table to pandas is extremely cheap, since it
does not require any copies. 

TODO example

We've seen that the Arrow-engines provide significant speedups over the custom C implementations.
They don't support all features of the custom implementations yet, but if your use-case is 
compatible with the supported options, you should get a significant speedup more or less for free.

The case with the PyArrow ``dtype_backend`` is a bit more complicated. Not all areas of the API are
optimized yet. If you spend a lot of time processing your data within pandas, then this might not 
give you what you need. It will speed up your processing though, if your workflow is I/O heavy,
e.g. if most of your time is spent reading the data.

## dtype_backend in PyArrow native I/O readers

TODO

