# This is an example docstring, written in MyST.

It has a code fence:

```python
a = "hallo"
```

and a table:

| foo | bar |
| --- | --- |
| baz | bim |

and, using the `fieldlist` extension, a field list:

:param a: the first parameter
:param b: the second parameter
:return: the return value


# Welcome to learn-autodoc's documentation!

```{autodoc2-docstring} src.test._example
---
literal:
literal-linenos:
literal-lexer: markdown
---
```

:::{autodoc2-object} src.test._example
    no_index = true
:::


