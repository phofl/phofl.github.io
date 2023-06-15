---
title: pandas internals: Lets talk about Blocks
date: 2023-06-15
slug: pandas-internals
tags: pandas
---

## Introduction

This post will show how a pandas DataFrame is constructed. We will take a look at what is behind
``pd.DataFrame()`` and try to answer all questions you might have about pandas internals.

pandas internals might show unexpected behavior in some cases, this is something we try to clarify.

## pandas data structure

The data that back a DataFrame are usually stored as some sort of array, e.g. a NumPy array or 
pandas ExtensionArray. pandas adds an intermediate layer, called ``Block`` and the ``BlockManager`` 
that orchestrate these arrays.

### Arrays

The actual data of a DataFrame can be stored in a set of NumPy arrays or pandas ExtensionArrays. 
This layer is not very interesting since it just holds your data. You can read up on pandas 
ExtensionArrays [here](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.extensions.ExtensionArray.html).

NumPy arrays are normally 2-dimensional, which offers a bunch of performance advantages that we
will take a look at later. pandas ExtensionArrays are mostly one-dimensional data structures as
of right now. This makes things a bit more predictable but has some drawbacks when looking at
performance.

### Blocks


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