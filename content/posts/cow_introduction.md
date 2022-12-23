---
title: A solution for inconsistencies in indexing operations in pandas
date: 2022-12-23
slug: cow-introduction
tags: pandas
---

_Get rid of annoying SettingWithCopyWarning messages_

## Introduction
Indexing operations in pandas are quite flexible and thus, have many cases that can behave quite 
different and therefore produce unexpected results. Additionally, it is hard to predict when a 
``SettingWithCopyWarningis`` raised and what this means exactly. I’ll show a couple of different 
scenarios and how each operation might impact your code. Afterwards, we will look at a new feature 
called ``Copy on Write`` that helps you to get rid of the inconsistencies and of 
``SettingWithCopyWarnings``. We will also investigate how this might impact performance and other 
methods in general.

## Indexing operations

Let’s look at how indexing operations currently work in pandas. If you are already familiar with 
indexing operations, you can jump to the next section. But be aware, there are many cases with 
different forms of behavior. The exact behavor is hard to predict.

An operation in pandas produces a copy, when the underlying data of the parent DataFrame and the 
new DataFrame are not shared. A view is an object that does share data with the parent object. A 
modification to the view can potentially impact the parent object.

As of right now, some indexing operations return copies while others return views. The exact 
behavior is hard to predict, even for experienced users. This has been a big annoyance for me in 
the past.

Let’s start with a DataFrame with two columns:

```python
df = pd.DataFrame({"user_id": [1, 2, 3], "score": [10, 15, 20]})

```

A __getitem__ operation on a DataFrame or Series returns a subset of the initial object. The subset 
might consist of one or a set of columns, one or a set of rows or a mixture of both. A __setitem__ 
operation on a DataFrame or Series updates a subset of the initial object. The subset itself is 
defined by the arguments to the calls.

A regular __getitem__ operation on a DataFrame provides a view in most cases:

```python
view = df["user_id"]
```


As a consequence, the new object ``view`` still references the parent object ``df`` and its data. Hence, 
writing into the view will also modify the parent object.

```python
view.iloc[0] = 10
```

This __setitem__ operation will consequently update not only our ``view`` but also ``df``. This 
happens because the underlying data are shared between both objects.

This is only true, if the column ``user_id`` occurs only once in ``df``. As soon as ``user_id`` is 
duplicated the __getitem__ operation returns a DataFrame. This means the returned object is a copy 
instead of a view:

```python
df = pd.DataFrame(
    [[1, 10, 2], [3, 15, 4]], 
    columns=["user_id", "score", "user_id"],
)
not_a_view = df["user_id"]
not_a_view.iloc[0] = 10
```

The __setitem__ operation does not update ``df``. We also get our first ``SettingWithCopyWarning``, even 
though this is a perfectly acceptable operation. The __getitem__ operation itself has many more cases, 
like list-like keys, e.g. ``df[["user_id"]]``, MultiIndex-columns and many more. I will go into more 
detail in follow-up posts to look at different forms of performing indexing operations and their 
behavior.


Let’s have a look at another case that is a bit more complicated than a single __getitem__ operation: 
chained indexing. Chained indexing means filtering with a boolean mask followed by a __getitem__ 
operation or the other way around. This is done in one step. We do not create a new variable to 
store the result of the first operation.

We again start with a regular DataFrame:

```python
df = pd.DataFrame({"user_id": [1, 2, 3], "score": [10, 15, 20]})
```

We can update all ``user_ids`` that have a score greater than 15 through:

```python
df["user_id"][df["score"] > 15] = 5
```

We take the column ``user_id`` and apply the filter afterwards. This works perfectly fine, because 
the column selection creates a view and the __setitem__ operation updates said view. We can switch 
both operations as well:

```python
df[df["score"] > 15]["user_id"] = 5
```

This execution order produces another ``SettingWithCopyWarning``. In contrast to our earlier example, 
nothing happens. The DataFrame ``df`` is not modified. This is a silent no-operation. The boolean 
mask always creates a copy of the initial DataFrame. Hence, the initial __getitem__ operation returns 
a copy. The return value is not assigned to any variable and is only a temporary result. The 
setitem operation updates this temporary copy. As a result, the modification is lost. The fact 
that masks return copies while column selections return views is an implementation detail. 
Ideally, such implementation details should not be visible.

Another approach of doing this is as follows:

```python
new_df = df[df["score"] > 15]
new_df["user_id"] = 10
```

This operation updates ``new_df`` as intended but shows a ``SettingWithCopyWarning`` anyway, because we 
can not update ``df``. Most of us probably never want to update the initial object (e.g. ``df``) in this 
scenario, but we get the warning anyway. In my experience this leads to unnecessary copy statements 
scattered over the code base.

This is just a small sample of current inconsistencies and annoyances in indexing operations.

Since the actual behavior is hard to predict, this forces many defensive copies in other methods. 
For example,

- dropping of columns
- setting a new index
- resetting the index
- …

All copy the underlying data. These copies are not necessary from an implementation perspective. 
The methods could return views pretty easily, but returning views would lead to unpredictable 
behavior later on. Theoretically, one __setitem__ operation could propagate through the whole 
call-chain, updating many DataFrames at once.

## Copy on Write

Let’s look at how a new feature called “Copy on Write” (CoW) helps us to get rid of these 
inconsistencies in our code base. CoW means that __any DataFrame or Series derived from another in__ 
__any way always behaves as a copy__. As a consequence, we can only change the values of an object 
through modifying the object itself. CoW disallows updating a DataFrame or a Series that shares 
data with another DataFrame or Series object inplace. With this information, we can again look at 
our initial example:

```python
df = pd.DataFrame({"user_id": [1, 2, 3], "score": [10, 15, 20]})
view = df["user_id"]
view.iloc[0] = 10
```

The __getitem__ operation provides a view onto ``df`` and it’s data. The __setitem__ operation triggers a copy 
of the underlying data before ``10`` is written into the first row. Hence, the operation won't modify 
``df``. An advantage of this behavior is, that we don’t have to worry about ``user_id`` being potentially
duplicated or using ``df[["user_id"]]`` instead of ``df["user_id"]``. All these cases behave exactly the 
same and no annoying warning is shown.

Triggering a copy before updating the values of the object has performance implications. This 
will most certainly cause a small slowdown for some operations. On the other side, a lot of other 
operations can __avoid__ defensive copies and thus improve performance tremendously. The following 
operations can all return views with CoW:

- dropping columns
- setting a new index
- resetting the index
- and many more.

Let’s consider the following DataFrame:

```python
na = np.array(np.random.rand(1_000_000, 100))
cols = [f"col_{i}" for i in range(100)]
df = pd.DataFrame(na, columns=cols)
```

Using ``add_prefix`` adds the given string (e.g. ``test``) to the beginning of every column name:

```python
df.add_prefix("test")
```

Without CoW, this will copy the data internally. This is not necessary when looking solely at the 
operation. But since returning a view can have side effects, the method returns a copy. As a 
consequence, the operation itself is pretty slow:

```python
482 ms ± 3.43 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
```

This takes quite long. We practically only modify 100 string literals without touching the data at 
all. Returning a view provides a significant speedup in this scenario:

```python
46.4 µs ± 1.04 µs per loop (mean ± std. dev. of 7 runs, 10,000 loops each)
```

The same operation runs multiple orders of magnitude faster. More importantly, the running time of 
``add_prefix`` is __constant__ when using CoW and does not depend on the size of your DataFrame. This 
operation was run on the main branch of pandas.

The copy is only necessary, if two different objects share the same underlying data. In the 
example above, ``view`` and ``df`` both reference the same data. If the data is exclusive to one ``DataFrame`` 
object, no copy is needed, we can continue to modify the data inplace:

```python
df = pd.DataFrame({"user_id": [1, 2, 3], "score": [10, 15, 20]})
df.iloc[0] = 10
```

In this case the __setitem__ operation will continue to operate inplace without triggering a copy.

As a consequence, all the different scenarios that we have seen initially have exactly the same 
behavior now. We don’t have to worry about subtle inconsistencies anymore.

Another case that currently has strange and hard to predict behavior is chained indexing. Chained 
indexing under CoW will __never__ work. This is a direct consequence of the CoW mechanism. The initial 
selection of columns might return a view, but a copy is triggered when we perform the subsequent 
setitem operation. Fortunately, we can easily modify our code to avoid chained indexing:

```python
df["user_id"][df["score"] > 15] = 10
```

We can use ``loc`` to do both operations at once:

```python
df.loc[df["score"] > 15, "user_id"] = 10
```

Summarizing, every object that we create behaves like a copy of the parent object. We can not 
accidentally update an object other than the one we are currently working with.

## How to try it out

You can try the CoW feature since pandas 1.5.0. Development is still ongoing, but the general 
mechanism works already.

You can either set the CoW flag globally through on of the following statements:

```python
pd.set_option("mode.copy_on_write", True)
pd.options.mode.copy_on_write = True
```

Alternatively, you can enable CoW locally with:

```python
with pd.option_context("mode.copy_on_write", True):
    ...
```

## Conclusion

We have seen that indexing operations in pandas have many edge cases and subtle differences in 
behavior that are hard to predict. CoW is a new feature aimed at addressing those differences. 
It can potentially impact performance positively or negatively based on what we are trying to do 
with our data. The full proposal for CoW can be found 
[here](https://docs.google.com/document/d/1ZCQ9mx3LBMy-nhwRl33_jgcvWo9IWdEfxDNQ2thyTb0/edit#heading=h.iexejdstiz8u).

Thank you for reading. Feel free to reach out to share your thoughts and feedback 
on indexing and Copy on Write. I will write follow.up posts focused on this topic and pandas in 
general.