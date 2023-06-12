---
title: Benchmarking pandas against polars from a pandas PoV
date: 2023-06-13
slug: pandas-benchmarks
tags: pandas
---

_Or: How writing efficient pandas code matters_

## Introduction

I've regularly seen benchmarks that show how much faster Polars is compared to pandas. The fact
that Polars is faster than pandas is not too surprising since it is multithreaded while pandas is
mostly single-core. The big difference surprises me though. That's why I decided to take a look at
the pandas queries that were used for the benchmarks. We will look at the ``tpch`` benchmarks from
the [Polars repository](https://github.com/pola-rs/tpch) with ``scale_1`` including I/O time. 
The results are quite interesting.

Initially, I tried to do this 2 months ago, but all the Polars queries were broken back then because
of API changes. They have been fixed since then. We will use the pandas nightly builds, because some 
optimizations for Copy-on-Write and the Pyarrow ``dtype_backend`` were added after 2.0 was released.
The next pandas release is scheduled for August. I use Polars in version 0.17.15.

I came away with 2 main takeaways:

- The pandas code that was used to create the benchmarks is bad.
- Writing efficient pandas code __matters a lot__.

I have a MacBook Air with M2 processors and 24GB of RAM.

## Baseline

I ran the benchmarks as is as a first step to get the status-quo.

![](../images/pandas_benchmark/baseline.png)

It's relatively easy to see that Polars is between 4-10 times faster than pandas. After getting 
these results I decided to look at the queries that were used for pandas.

Side note: Number 8 is broken, so no result here.

## Initial refactoring

All data were read from the parquet files is one thing that stood out even though
most queries only needed a small subset. Some queries also did some operations on
the whole dataset and dropped the columns later on. There was no obvious reason for doing
 this. A filtering operation is slowed down quite a bit, e.g.:

```python
new_df = df[mask]
```

So I pushed the column selection into ``read_parquet``, since this is an easy fix
through the ``columns`` keyword. I am assuming that query optimization in Polars is doing something
similar. 

```python
df = pd.read_parquet(...)
df = df[df.a > 100]
df[["a", "b"]]
```

This was rewritten into:

```python
df = pd.read_parquet(..., columns=["a", "b"])
df = df[df.a > 100]
```


I've also turned Copy-on-Write on. It's now in a state
that it shouldn't have many performance problems anymore while it will most likely
give a speedup. That said, the difference here is not too big, since ``GroupBy`` and
``merge`` arent really influenced by CoW. These steps took me around 30 minutes for all queries.
Most queries restricted the DataFrame later on anyway, so it was mostly a copy-paste exercise.

Let's look at the results:

![](../images/pandas_benchmark/first_optimization.png)

The pandas queries got a lot faster through a couple of small modifications. The difference is still
bigger than I'd like, but this was a good start.

## Further optimizations - leveraging Arrow

A quick profiling showed that the filter operations were a bottleneck in a couple of queries. 
Fortunately, there is an easy fix. ``read_parquet`` passes potential keywords through to PyArrow and
Arrow offers the option to filter the table while reading the parquet file. Moving these filters up 
gives a nice additional improvement. I've also cleaned up some of the queries, because they were 
using weird patterns that didn't make much sense.

```python
df = pd.read_parquet(..., columns=["a", "b"])
df = df[df.a > 100]
```

This is now written as:

```python
import pyarrow.compute as pc


df = pd.read_parquet(..., columns=["a", "b"], filters=pc.field("a") > 100)
```

Let's look at what this means performance-wise.

![](../images/pandas_benchmark/second_optimization.png)

This looks quite good now. We were able to bring a bunch of queries a lot closer
to Polars performance. There is one relatively straightforward
optimization left without rewriting the queries completely.

## Improving ``merge`` performance

This technique is a bit tricky. I stumbled upon this a couple of years ago when I had a performance
issue at my previous job. In these scenarios, ``merge`` is basically used as a filter that restricts
one of both DataFrames quite heavily. This is relatively slow when using merge, because pandas
isn't aware that you want to use the ``merge`` operation as a filter. We can apply a filter
with isin before performing the actual merge to speed up our queries.

```python
import pandas as pd

left = pd.DataFrame({"left_a": [1, 2, 3], "left_b": [4, 5, 6]})
right = pd.DataFrame({"right_a": [1], "right_c": [4]})

left = left[left["left_a"].isin(right["right_a"])]  # restrict the df beforehand
result = left.merge(right, left_on="left_a", right_on="right_a")
```

This version brings us another performance boost compared to our previous results.

![](../images/pandas_benchmark/final_optimization.png)

## Summary

All in all these optimizations took me around 1.5-2 hours. A relatively small time investment where most
of the time was spent on reorganizing the initial queries. You can find the PR that modifies the 
benchmarks [here](TODO: Add PR link)

Writing efficient pandas code can bring you quite close to Polars' performance without factoring in
any improvements on the pandas side. We identified a couple of bottlenecks while looking into these
queries that we plan to address in the future. 

The ``scale_10`` queries are also drastically faster compared to the previous
version.
