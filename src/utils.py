from typing import Any


ListExactlyOne = object()  # singleton sentinel
ListExactlyOneChildDictKey = object()  # singleton sentinel


def get_nested_item(data: Any, *paths: str | object) -> Any:
    """
    Traverse nested data (dicts/lists) using paths.
    - Strings are dict keys.
    - ListExactlyOne selects exactly one element from a list; raises if not exactly one.
    """
    n = 0
    while n < len(paths):
        path = paths[n]
        n += 1
        if isinstance(path, str):
            if not isinstance(data, dict):
                raise TypeError("Cannot use str path on non-dict")
            data = data[path]
        elif path is ListExactlyOne:
            if not isinstance(data, list):
                raise TypeError("Cannot use ListExactlyOne on non-list")
            if len(data) != 1:  # pyright: ignore[reportUnknownArgumentType]
                raise ValueError(f"Expected exactly one item in list, got {len(data)}")  # pyright: ignore[reportUnknownArgumentType]
            data = data[0]  # pyright: ignore[reportUnknownVariableType]
        elif path is ListExactlyOneChildDictKey:
            if not isinstance(data, list):
                raise TypeError("Cannot use ListExactlyOneChildDictKey on non-list")
            if n >= len(paths):
                raise ValueError("Unexpected End of list")
            path = paths[n]
            n += 1
            result: Any = None
            found: bool = False
            for item in data:  # pyright: ignore[reportUnknownVariableType]
                if not isinstance(item, dict):
                    raise TypeError(
                        "Cannot use ListExactlyOneChildDictKey on list having non dict entry"
                    )
                try:
                    result = item[path]  # pyright: ignore[reportUnknownVariableType]
                    if found:
                        found = False
                        break
                    found = True
                except KeyError:
                    continue
            if not found:
                raise ValueError(
                    f"Expected exactly one item having the key: {path!r} in list"
                )
            data = result  # pyright: ignore[reportUnknownVariableType]
        else:
            raise ValueError(f"Invalid path element: {path!r}")

    return data  # pyright: ignore[reportUnknownVariableType]
