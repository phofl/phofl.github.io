---
title: What's new in pandas 2.1
date: 2023-09-07
slug: pandas-whatsnew-21
tags: pandas
---

_The most interesting things about the new release_

pandas 2.1 was released on August 30th 2023. Let’s take a look at the things this release introduces 
and how it will help us improving our pandas workloads. It includes a bunch of improvements and also a set of new deprecations.

pandas 2.1 builds heavily on the PyArrow integration that became available with pandas 2.0. We focused a lot on building out the support for new features that are expected to become the default with pandas 3.0. Let’s dig into what this means for you. We will look at the most important improvements in detail.

I am part of the pandas core team. I am an open source engineer for [Coiled](https://www.coiled.io) where I work on Dask, including improving the pandas integration.

## Avoiding NumPy object-dtype for string columns

One major pain point in pandas is the inefficient string representation. This is a topic that we worked on for quite some time. The first PyArrow backed string dtype became available in pandas 1.3. It has the potential to reduce memory usage by around 70% and improve the performance. I’ve explored this topic in more depth in [One of my previous posts](https://medium.com/towards-data-science/utilizing-pyarrow-to-improve-pandas-and-dask-workflows-2891d3d96d2b) , which includes memory comparisons and performance measurements (tldr: it’s impressive).

We’ve decided to introduce a new configuration option that will store all string columns in a PyArrow array. You don’t have to worry about casting string columns anymore, this will just work.

You can turn this option on with:

```python
pd.options.future.infer_string = True
```

This behavior will become the default in pandas 3.0, which means that string-columns would always be backed by PyArrow. You have to install PyArrow to use this option.

PyArrow has different behavior than NumPy object dtype, which can make a pain to figure out in detail. We implemented the string dtype that is used for this option to be compatible with NumPy sematics. It will behave exactly the same as NumPy object columns would. I encourage everyone to try this out!

## Improved PyArrow support

We have introduced PyArrow backed DataFrame in pandas 2.0. One major goal for us was to improve the integration within pandas over the last few months. We were aiming to make the switch from NumPy backed DataFrames as easy as possible. One area that we focused on was fixing performance bottlenecks, since this caused unexpected slowdowns before.

Let’s look at an example:

```python
import pandas as pd
import numpy as np

df = pd.DataFrame(
    {
        "foo": np.random.randint(1, 10, (1_000_000, )),
        "bar": np.random.randint(1, 100, (1_000_000,)),
    }, dtype="int64[pyarrow]"
)
grouped = df.groupby("foo")
```

Our DataFrame has 1 million rows and 10 groups. Let’s look at the performance on pandas 2.0.3 compared to pandas 2.1:

```python
# pandas 2.0.3
10.6 ms ± 72.7 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)

# pandas 2.1.0
1.91 ms ± 3.16 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)
```

This particular example is 5 times faster on the new version. ``merge`` is another commonly used function that will be faster now. We are hopeful that the experience with PyArrow backed DataFrames is much better now.

## Copy-on-Write

Copy-on-Write was initially introduced in pandas 1.5.0 and is expected to become the default behavior
in pandas 3.0. The new version adds the remaining performance improvements that didn't make it into 
2.1. The mode is now 
ready for use. I'd encourage everyone to try it out and to enable it by default in their workflows.
I wrote a series of blog posts explaining 
[what Copy-on-Write is](https://towardsdatascience.com/a-solution-for-inconsistencies-in-indexing-operations-in-pandas-b76e10719744) 
and [how it works](https://towardsdatascience.com/deep-dive-into-pandas-copy-on-write-mode-part-i-26982e7408c6).

We’ve seen that Copy-on-Write can improve the performance of real-world workflows by over 50%.

## Deprecating silent upcasting in setitem-like operations

Historically, pandas would silently change the dtype of one of your columns if you set an incompatible value into it. Let’s look at an example:

```python
ser = pd.Series([1, 2, 3])

0    1
1    2
2    3
dtype: int64
```

We have a Series with integers, which will result in integer dtype. Let's set the letter ``"a"``
into the second row:

```python
ser.iloc[1] = "a"

0    1
1    a
2    3
dtype: object
```

This changes the dtype of your Series to object. Object is the only dtype that can hold integers and strings. This is a major pain for a lot of user. Object columns take up a lot of memory, calculations won’t work anymore, performance degrades and many other things. It also added a lot of special casing internally to accomodate these things. Silent dtype changes in my DataFrame were a major annoyance for me in the past. This behavior is now deprecated and will raise a FutureWarning:

```python
FutureWarning: Setting an item of incompatible dtype is deprecated and will raise in a future 
error of pandas. Value 'a' has dtype incompatible with int64, please explicitly cast to a 
compatible dtype first.
  ser.iloc[1] = "a"
```

Operations like our example will raise an error in pandas 3.0. The dtypes of a DataFrames columns will stay consistent across different operations. You will have to be explicit when you want to change your dtype, which adds a bit of code but makes it easier to follow for future developers.

This change affects all dtypes, e.g. setting a float value into an integer column will also raise.

## Upgrading to the new version

You can install the new pandas version with:

```pyth+
pip install -U pandas
```

Or:

```pyth+
mamba install -c conda-forge pandas=2.1
```

This will give you the new release in your environment.

## Conclusion

We’ve looked at a couple of improvements that will help you write more efficient code. This includes performance improvements, easier opt-in into PyArrow backed string columns and further improvements for Copy-on-Write. We’ve also seen a deprecation that will make the behavior of pandas easier to predict in the next major release.

Thank you for reading. Feel free to reach out to share your thoughts and feedback.
