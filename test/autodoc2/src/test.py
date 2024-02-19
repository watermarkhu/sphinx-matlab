"""This is a test"""

def _example(a: int, b: str) -> None:
    """This is an example docstring, written in MyST.

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

    """