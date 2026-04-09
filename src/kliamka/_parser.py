"""Internal argparse population from KliamkaArgClass definitions."""

from __future__ import annotations

import argparse
from enum import Enum
from typing import TYPE_CHECKING, Any, Type

from ._converters import _resolve_type_converter
from ._helpers import (
    _get_list_element_type,
    _is_bool_annotation,
    _is_list_type,
    _unwrap_optional,
)

if TYPE_CHECKING:
    from ._core import KliamkaArg, KliamkaArgClass


def _build_positional_kwargs(
    field_info: Any, field_value: "KliamkaArg"
) -> dict[str, Any]:
    """Build argparse kwargs for a positional argument."""
    help_text = field_value.help_text
    if field_value.env:
        help_text += f" [env: {field_value.env}]"

    kwargs: dict[str, Any] = {"help": help_text}
    annotation = field_info.annotation
    annotation, is_optional = _unwrap_optional(annotation)

    resolved = _resolve_type_converter(annotation, field_value)

    if _is_list_type(annotation):
        element_type = _get_list_element_type(annotation)
        kwargs["nargs"] = "*"
        kwargs["default"] = (
            field_value.default if field_value.default is not None else []
        )
        if resolved is not None:
            kwargs["type"] = resolved
        else:
            kwargs["type"] = element_type if element_type is not None else str
    else:
        if is_optional or field_value.default is not None:
            kwargs["nargs"] = "?"
            kwargs["default"] = field_value.default

        if (
            annotation is not None
            and isinstance(annotation, type)
            and issubclass(annotation, Enum)
        ):
            # Enum metavar must be set even though the resolver already
            # returned the enum parser as the type=.
            kwargs["type"] = resolved
            choices = [f"{m.name}({m.value})" for m in annotation]
            kwargs["metavar"] = "{" + ",".join(choices) + "}"
        elif resolved is not None:
            kwargs["type"] = resolved
        else:
            kwargs["type"] = annotation if annotation is not None else str

    return kwargs


def _build_optional_kwargs(
    field_info: Any, field_value: "KliamkaArg"
) -> dict[str, Any]:
    """Build argparse kwargs for an optional (flag) argument."""
    help_text = field_value.help_text
    if field_value.env:
        help_text += f" [env: {field_value.env}]"

    kwargs: dict[str, Any] = {
        "help": help_text,
        "default": field_value.default,
    }

    if _is_bool_annotation(field_info.annotation):
        kwargs["action"] = "store_true"
        kwargs["default"] = (
            field_value.default if field_value.default is not None else False
        )
    else:
        annotation, _ = _unwrap_optional(field_info.annotation)
        resolved = _resolve_type_converter(annotation, field_value)

        if _is_list_type(annotation):
            element_type = _get_list_element_type(annotation)
            kwargs["nargs"] = "*"
            kwargs["default"] = (
                field_value.default if field_value.default is not None else []
            )
            if resolved is not None:
                kwargs["type"] = resolved
            else:
                kwargs["type"] = element_type if element_type is not None else str
        elif (
            annotation is not None
            and isinstance(annotation, type)
            and issubclass(annotation, Enum)
        ):
            kwargs["type"] = resolved
            choices = [f"{m.name}({m.value})" for m in annotation]
            kwargs["metavar"] = "{" + ",".join(choices) + "}"
        elif resolved is not None:
            kwargs["type"] = resolved
        else:
            kwargs["type"] = annotation if annotation is not None else str

    return kwargs


def _get_flag_names(field_value: "KliamkaArg") -> list[str]:
    """Get all flag names (long + short) for an argument."""
    flags = [field_value.flag]
    if field_value.short:
        flags.insert(0, field_value.short)
    return flags


def _populate_parser(
    parser: argparse.ArgumentParser,
    arg_class: Type["KliamkaArgClass"],
) -> None:
    """Populate an ArgumentParser with arguments from a KliamkaArgClass."""
    from ._core import KliamkaArg  # local import breaks the _core<->_parser cycle

    positional_args: list[tuple[str, Any, "KliamkaArg"]] = []
    optional_args: list[tuple[str, Any, "KliamkaArg"]] = []
    exclusive_groups: dict[str, list[tuple[str, Any, "KliamkaArg"]]] = {}

    for field_name, field_info in arg_class.model_fields.items():
        if not isinstance(field_info.default, KliamkaArg):
            continue
        field_value = field_info.default
        is_positional = field_value.positional or not field_value.flag.startswith("-")

        if field_value.mutually_exclusive:
            group_name = field_value.mutually_exclusive
            if group_name not in exclusive_groups:
                exclusive_groups[group_name] = []
            exclusive_groups[group_name].append((field_name, field_info, field_value))
        elif is_positional:
            positional_args.append((field_name, field_info, field_value))
        else:
            optional_args.append((field_name, field_info, field_value))

    for _field_name, field_info, field_value in positional_args:
        kwargs = _build_positional_kwargs(field_info, field_value)
        parser.add_argument(field_value.flag, **kwargs)

    for _field_name, field_info, field_value in optional_args:
        kwargs = _build_optional_kwargs(field_info, field_value)
        flags = _get_flag_names(field_value)
        parser.add_argument(*flags, **kwargs)

    for _group_name, members in exclusive_groups.items():
        group = parser.add_mutually_exclusive_group()
        for _field_name, field_info, field_value in members:
            kwargs = _build_optional_kwargs(field_info, field_value)
            flags = _get_flag_names(field_value)
            group.add_argument(*flags, **kwargs)
