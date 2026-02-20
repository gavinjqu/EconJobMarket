"""Auto-discovery parser registry.

Any .py file in this package that defines a BasePlacementParser subclass
with a non-empty ``university_slug`` attribute is registered automatically.
"""

import importlib
import pkgutil
import pathlib

from src.parsers.base import BasePlacementParser

PARSERS: dict[str, type[BasePlacementParser]] = {}

_pkg_dir = pathlib.Path(__file__).parent

for _finder, _name, _ispkg in pkgutil.iter_modules([str(_pkg_dir)]):
    if _name == "base":
        continue
    _module = importlib.import_module(f"src.parsers.{_name}")
    for _attr in dir(_module):
        _obj = getattr(_module, _attr)
        if (
            isinstance(_obj, type)
            and issubclass(_obj, BasePlacementParser)
            and _obj is not BasePlacementParser
            and getattr(_obj, "university_slug", "")
        ):
            PARSERS[_obj.university_slug] = _obj
