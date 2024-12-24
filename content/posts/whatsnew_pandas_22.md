---
title: What's new in pandas 2.2
date: 2024-01-26
slug: pandas-whatsnew-22
tags: pandas
---

_The most interesting things about the new release_

pandas 2.2 was released on January 22nd 2024. Let’s take a look at the things this release introduces 
and how it will help us to improve our pandas workloads. It includes a bunch of improvements that will
improve the user experience.

pandas 2.2 brought a few additional improvements that rely on the Apache Arrow ecosystem. Additionally,
we added deprecations for changes that are necessary to make Copy-on-Write the default in pandas 3.0.
Let’s dig into what this means for you. We will look at the most important changes in detail.

I am part of the pandas core team. I am an open source engineer for [Coiled](https://www.coiled.io) 
where I work on Dask, including improving the pandas integration.

## Improved PyArrow support

We have introduced PyArrow backed DataFrame in pandas 2.0 and continued to improve the integration
since then to enable a seamless integration into the pandas API. pandas has accessors for certain
dtypes that enable specialized operations, like the string accessor, that provides many string methods.
Historically, list and structs were represented as NumPy object dtype, which made working with them
quite cumbersome. The Arrow dtype backend now enables tailored accessors for lists and structs, which
makes working with these obejcts a lot easier.

Let’s look at an example:

```python
import pyarrow as pa

series = pd.Series(
    [
        {"project": "pandas", "version": "2.2.0"},
        {"project": "numpy", "version": "1.25.2"},
        {"project": "pyarrow", "version": "13.0.0"},
    ],
    dtype=pd.ArrowDtype(
        pa.struct([
            ("project", pa.string()),
            ("version", pa.string()),
        ])
    ),
)
```

This is a series that contains a dictionary in every row. Previously, this was only possible
with NumPy object dtype and accessing elements from these rows required iterating over them.
The ``struct`` accessor now enables direct access to certain attributes:

```python

series.struct.field("project")

0     pandas
1      numpy
2    pyarrow
Name: project, dtype: string[pyarrow]
```

The next release will bring a CategoricalAccessor based on Arrow types.

## Integrating the Apache ADBC Driver

Historically, pandas relied on SqlAlchemy to read data from an Sql database. This worked very reliably,
but it was very slow. Alchemy reads the data row-wise, while pandas has a columnar layout, which
makes reading and moving the data into a DataFrame slower than necessary. 

The [ADBC Driver](https://arrow.apache.org/docs/format/ADBC.html) from the Apache Arrow project enables users to read data in a columnar 
layout, which brings huge performance improvements. It reads the data and stores them into an Arrow
table, which is used to convert to a pandas DataFrame. You can make this conversion zero-copy, if you set
``dtype_backend="pyarrow"`` for ``read_sql``.

Let's look at an example:

```python
import adbc_driver_postgresql.dbapi as pg_dbapi

df = pd.DataFrame(
   [
       [1, 2, 3],
       [4, 5, 6],
   ],
   columns=['a', 'b', 'c']
)
uri = "postgresql://postgres:postgres@localhost/postgres"
with pg_dbapi.connect(uri) as conn:
   df.to_sql("pandas_table", conn, index=False)

# for round-tripping
with pg_dbapi.connect(uri) as conn:
   df2 = pd.read_sql("pandas_table", conn)
```

The ADBC Driver currently supports Postgres and Sqlite. I would recommend everyone to switch over
to this driver if you use Postgres, the driver is significantly faster and completely avoids
round-tripping through Python objects, thus preserving the database types more reliably. This is the
feature that I am personally most excited about.

## Adding case_when to the pandas API

Coming from Sql to pandas, users often miss the case-when syntax that provides an easy and clean way to
create new columns conditionally. pandas 2.2 adds a new ``case_when`` method, that is defined on a
Series. It operates similarly to what Sql does.

Let's look at an example:

```python

df = pd.DataFrame(dict(a=[1, 2, 3], b=[4, 5, 6]))

default=pd.Series('default', index=df.index)
default.case_when(
    caselist=[
        (df.a == 1, 'first'),
        (df.a.gt(1) & df.b.eq(5), 'second'),
    ],
)
```

The method takes a list of conditions that are evaluated sequentially. The new object is then
created with those values in rows where the condition evaluates to True. The method should make
it significantly easier for us to create conditional columns.

## Copy-on-Write

Copy-on-Write was initially introduced in pandas 1.5.0. The mode will become the default behavior
with 3.0, which is hopefully the next pandas release. This means that we have to get our code into
a state where it is compliant with the Copy-on-Write rules. pandas 2.2 introduced deprecation warnings
for operations that will change behavior.

```python
df = pd.DataFrame({"x": [1, 2, 3]})

df["x"][df["x"] > 1] = 100
```

This will now raise a ``FutureWarning``.

```python
FutureWarning: ChainedAssignmentError: behaviour will change in pandas 3.0!
You are setting values through chained assignment. Currently this works in certain cases, but when 
using Copy-on-Write (which will become the default behaviour in pandas 3.0) this will never work to 
update the original DataFrame or Series, because the intermediate object on which we are setting 
values will behave as a copy. A typical example is when you are setting values in a column of a 
DataFrame, like:

df["col"][row_indexer] = value

Use `df.loc[row_indexer, "col"] = values` instead, to perform the assignment in a single step and 
ensure this keeps updating the original `df`.
```

I wrote [an earlier post](https://medium.com/towards-data-science/deep-dive-into-pandas-copy-on-write-mode-part-iii-c024eaa16ed4) that goes into more details about how you can migrate your code and what
to expect. There is an additional warning mode for Copy-on-Write that will raise warnings for all
cases that change behavior:

```python

pd.options.mode.copy_on_write = "warn"
```

Most of those warnings are only noise for the majority of pandas users, which is the
reason why they are hidden behind an option. 

```python
pd.options.mode.copy_on_write = "warn"

df = pd.DataFrame({"a": [1, 2, 3]})
view = df["a"]
view.iloc[0] = 100
```

This will raise a lengthy warning explaining what will change:

```python
FutureWarning: Setting a value on a view: behaviour will change in pandas 3.0.
You are mutating a Series or DataFrame object, and currently this mutation will
also have effect on other Series or DataFrame objects that share data with this
object. In pandas 3.0 (with Copy-on-Write), updating one Series or DataFrame object
will never modify another.
```

The short summary of this is: Updating ``view`` will never update ``df``, no matter what operation
is used. This is most likely not relevant for most.

I would recommend enabling the mode and checking the warnings briefly, but not to pay too much attention
to them if you are comfortable that you are not relying on updating two different objects at once.

I would recommend checking out the [migration guide for Copy-on-Write](https://pandas.pydata.org/docs/dev/user_guide/copy_on_write.html#migrating-to-copy-on-write) that explains the necessary
changes in more detail.

## Upgrading to the new version

You can install the new pandas version with:

```python
pip install -U pandas
```

Or:

```python
mamba install -c conda-forge pandas=2.2
```
This will give you the new release in your environment.

## Conclusion

We’ve looked at a couple of improvements that will improve performance and user experience
for certain aspects of pandas. The most exciting new features will come in pandas 3.0, where
Copy-on-Write will be enabled by default.

Thank you for reading. Feel free to reach out to share your thoughts and feedback.
