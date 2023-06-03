---
title: Deep dive into pandas Copy-on-Write mode
date: 2023-06-15
slug: cow-deep-dive
tags: pandas
---

_How it works, how to adapt your code and how to use it effectively_

## Introduction

pandas 2.0 was released in early April and brought many improvements to the new Copy-on-Write (CoW)
mode. The feature is expected to become the default in pandas 3.0, which as of now is scheduled for
April 2024. There won't be a legacy or non-CoW mode.

This post will explain how Copy-on-Write works internally to help users understand what's going on
and afterward show how to use it effectively. This will include examples on how to leverage the
mechanism to get the most efficient performance and also show a couple of anti-patterns that will
result in unnecessary bottlenecks.

I am part of the pandas core team and was heavily involved in implementing and improving CoW so far. 
I've recently joined [Coiled](https://www.coiled.io) where I am working on Dask, including improving
the pandas integration and ensuring that Dask is compliant with CoW.

# How Copy-on-Write changes pandas behavior

Many of you are probably familiar with the following caveats in pandas:

```python
import pandas as pd

df = pd.DataFrame({"student_id": [1, 2, 3], "grade": ["A", "C", "D"]})
```

Let's select the grade-column and overwrite the first row with ``"E"``.

```python
grades = df["grade"]
grades.iloc[0] = "E"
df

   student_id grade
0           1     E
1           2     C
2           3     D
```

Unfortunately, this also updated ``df`` and not only ``grades``, which has the potential to 
introduce hard to find bugs. CoW will disallow this behavior and ensures that only ``df`` is
updated. We also see a false-positive ``SettingWithCopyWarning`` that doesn't help us here.

Let's look at a ``ChainedIndexing`` example that does nothing as well:

```python
df[df["student_id"] > 2]["grades"] = "F"
df

   student_id grade
0           1     A
1           2     C
2           3     D
```

We again get a ``SettingWithCopyWarning`` but nothing happens to ``df`` in this example. All these
gotchas come down to Copy and View rules in NumPy, which is what pandas uses under the hood. pandas
users have to be aware of these rules and how they apply to pandas DataFrames to understand why
similar code-patterns produce different results. 

CoW cleans up all these inconsistencies. Users can only update one object at a time when CoW is
enabled, e.g. ``df`` would be unchanged in our first example since only ``grades`` is updated at
that time and the second example raises a ``ChainedAssignmentError`` instead of doing nothing.
Generally, it won't be possible to update two objects at once, e.g., every object behaves as it
created a deep copy of the previous object.

There are many more of these cases, but going through all of them is not in scope here.

# How it works

We will now look into how Copy-on-Write works and highlight some details that are valuable to 
users. This is the main part of this post and is fairly technical.

Copy-on-Write promises that __any DataFrame or Series derived from another in__ 
__any way always behaves as a copy__. This means that it is not possible to modify more than one
object with a single operation, e.g. our first example above would only modify ``grades``. 

> Let's look at how a DataFrame is constructed. We assume that our DataFrame is backed by NumPy arrays,
> but the concept translates to DataFrames backed by PyArrow arrays. Every column of a DataFrame is
> backed by a NumPy array. One NumPy array with multiple columns can back multiple columns in a
> DataFrame. The arrays are wrapped by an object that is called ``Block``, but this is an 
> implementation detail and not relevant for CoW.
> 
> ![](../images/deep_dive_cow/df_representation.png)
> 
> Our DataFrame has 3 columns, 2 of them have ``int64`` dtype and are stored in a single NumPy
> array while the third one has ``float64`` dtype and is a separate NumPy array. Columns that have the
> exact same dtype, e.g. can be stored in a NumPy array, are generally represented as a single array.
> 
> A pandas object is called a view, when an operation creates a new __pandas__ object that 
> references the same underlying NumPy arrays. Modifying said new object without CoW will generally
> also modify the previous object since the NumPy arrays are updated inplace.

We could guarantee the CoW promise through copying the underlying NumPy arrays in every operation,
which would avoid views in pandas altogether. This would guarantee CoW semantics but also incur a
huge performance penalty, so this wasn't an option for us. 

We will now dive into the mechanism that ensures that no two objects are updated with a single
operation, but also that no unnecessary copies are made. 







# How to adapt your code

TODO

# How to get the most out of CoW

TODO
