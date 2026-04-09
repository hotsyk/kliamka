"""Global type converter registry for kliamka CLI arguments.

This module holds the global converter registry together with a single shared
resolver, :func:`_resolve_type_converter`, which encodes the canonical 5-step
resolution order used both when building the argparse parser
(``_parser.py``) and when parsing environment variables
(``_core.py._parse_env_value``). Routing both call sites through the same
resolver guarantees that CLI and env-var parsing behave identically.

Resolution order (first match wins):

1. Explicit ``field_value.converter`` — a per-field override supplied via
   :class:`KliamkaArg`.
2. A globally registered converter (:func:`register_converter`) for the
   unwrapped annotation type.
3. An :class:`enum.Enum` subclass — handled via
   :func:`_create_enum_parser`.
4. A ``List[T]`` annotation — recurse on ``T`` and return the element
   converter (argparse applies it per item via ``nargs``).
5. Fallback: return ``None`` to let the caller use the raw annotation as
   the argparse ``type=`` callable (e.g. ``int``, ``float``, ``str``).

The registry starts empty; callers opt in explicitly via
:func:`register_converter`.
"""

from __future__ import annotations

import argparse
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

from ._helpers import (
    _create_enum_parser,
    _get_list_element_type,
    _is_list_type,
    _unwrap_optional,
)

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from ._core import KliamkaArg


# --------------------------------------------------------------------------- #
# Registry storage
# --------------------------------------------------------------------------- #

#: Module-level mapping of ``type -> converter callable``. Starts empty;
#: populated exclusively via :func:`register_converter`.
_CONVERTERS: dict[type, Callable[[str], Any]] = {}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def register_converter(tp: type, fn: Callable[[str], Any]) -> None:
    """Register a global converter for ``tp``.

    If ``tp`` is already registered, the existing entry is overwritten.
    The converter ``fn`` must accept a single ``str`` (the raw CLI token
    or environment variable value) and return the parsed value. It may
    raise :class:`ValueError` or :class:`TypeError` on bad input; the
    resolver wraps those into :class:`argparse.ArgumentTypeError`
    automatically.
    """
    _CONVERTERS[tp] = fn


def unregister_converter(tp: type) -> None:
    """Remove a global converter for ``tp`` if present.

    This is a no-op if no converter is registered for ``tp``.
    """
    _CONVERTERS.pop(tp, None)


def get_converter(tp: type) -> Optional[Callable[[str], Any]]:
    """Return the registered converter for ``tp`` or ``None``."""
    return _CONVERTERS.get(tp)


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _wrap_converter(fn: Callable[[str], Any], type_name: str) -> Callable[[str], Any]:
    """Wrap ``fn`` so ``ValueError`` / ``TypeError`` become argparse errors.

    argparse surfaces :class:`argparse.ArgumentTypeError` as a clean
    ``error: argument ...: invalid ... value: ...`` line, while bare
    ``ValueError`` / ``TypeError`` would crash with a traceback. We
    preserve the original exception as ``__cause__`` so debuggers still
    see the underlying failure.
    """

    def _inner(value: str) -> Any:
        try:
            return fn(value)
        except (ValueError, TypeError) as exc:
            raise argparse.ArgumentTypeError(
                f"invalid {type_name} value: {value!r} ({exc})"
            ) from exc

    _inner.__name__ = getattr(fn, "__name__", "converter")
    _inner.__qualname__ = _inner.__name__
    return _inner


def _resolve_type_converter(
    annotation: Any,
    field_value: "Optional[KliamkaArg]" = None,
) -> Optional[Callable[[str], Any]]:
    """Resolve a converter for ``annotation`` following the 5-step order.

    Returns a single-argument callable suitable for use as argparse's
    ``type=`` (and equally usable by ``_parse_env_value``), or ``None``
    to signal that the caller should fall back to the raw annotation.

    Per-field ``field_value.converter`` overrides, registry entries, and
    the recursive ``List[T]`` element lookup are all wrapped via
    :func:`_wrap_converter` so bad input surfaces as a clean argparse
    error. The Enum branch is *not* wrapped because
    :func:`_create_enum_parser` already raises
    :class:`argparse.ArgumentTypeError` directly with a helpful message
    listing valid choices. The raw-annotation fallback is also not
    wrapped — callers asking for e.g. ``int`` expect argparse's native
    error formatting for that built-in.
    """
    unwrapped, _ = _unwrap_optional(annotation)

    # (1) Explicit per-field override on KliamkaArg.
    if field_value is not None:
        explicit = getattr(field_value, "converter", None)
        if explicit is not None:
            type_name = getattr(unwrapped, "__name__", None) or repr(unwrapped)
            return _wrap_converter(explicit, type_name)

    # (2) Globally registered converter for the unwrapped type.
    if unwrapped is not None:
        try:
            registered = _CONVERTERS.get(unwrapped)
        except TypeError:
            # Unhashable annotation (e.g. a parameterized generic) —
            # treat as "not registered" and fall through.
            registered = None
        if registered is not None:
            type_name = getattr(unwrapped, "__name__", None) or repr(unwrapped)
            return _wrap_converter(registered, type_name)

    # (3) Enum subclass -> dedicated enum parser (already argparse-friendly).
    if (
        unwrapped is not None
        and isinstance(unwrapped, type)
        and issubclass(unwrapped, Enum)
    ):
        return _create_enum_parser(unwrapped)

    # (4) List[T] -> recurse on the element type. argparse applies the
    # returned callable to each token individually via nargs.
    if _is_list_type(unwrapped):
        element_type = _get_list_element_type(unwrapped)
        element_converter = _resolve_type_converter(element_type, None)
        if element_converter is not None:
            return element_converter
        # No specialized converter for the element — let the caller use
        # the element type directly (e.g. ``int``, ``str``).
        return element_type if element_type is not None else None

    # (5) Fallback: no specialized converter; caller uses the raw
    # annotation (or ``str`` if it is ``None``) as argparse ``type=``.
    return None
