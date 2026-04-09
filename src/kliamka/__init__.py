"""Kliamka - Small Python CLI library."""

from ._converters import register_converter, unregister_converter
from ._core import KliamkaArg, KliamkaArgClass, KliamkaError, ParserMeta
from ._decorators import kliamka_cli, kliamka_subcommands

__all__ = [
    "KliamkaArg",
    "KliamkaArgClass",
    "KliamkaError",
    "ParserMeta",
    "kliamka_cli",
    "kliamka_subcommands",
    "register_converter",
    "unregister_converter",
    "__version__",
    "__author__",
    "__email__",
]

__version__ = "0.5.0"
__author__ = "Volodymyr Hotsyk"
__email__ = "git@hotsyk.com"
