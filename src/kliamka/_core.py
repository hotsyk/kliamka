"""Core descriptors, base class, and validation error formatting."""

from __future__ import annotations

import argparse
import os
from typing import Any, Callable, Optional, Type, Union

from pydantic import BaseModel, ValidationError

from ._converters import _resolve_type_converter
from ._helpers import (
    _get_list_element_type,
    _is_bool_annotation,
    _is_list_type,
    _unwrap_optional,
)
from ._parser import _populate_parser

_PYDANTIC_MSG_PREFIXES = (
    "Value error, ",
    "Assertion failed, ",
    "Type error, ",
)


class KliamkaError(Exception):
    """Base exception for kliamka library."""

    pass


def _strip_pydantic_prefix(message: str) -> str:
    """Strip known Pydantic message prefixes (e.g. ``Value error, ``)."""
    for prefix in _PYDANTIC_MSG_PREFIXES:
        if message.startswith(prefix):
            return message[len(prefix) :]
    return message


def _format_validation_error(error: ValidationError) -> str:
    """Format a Pydantic validation error for cleaner CLI output."""
    messages: list[str] = []
    for item in error.errors(include_url=False):
        location = ".".join(
            str(part) for part in item.get("loc", ()) if part != "__root__"
        )
        message = _strip_pydantic_prefix(item.get("msg", "Invalid value"))
        messages.append(f"{location}: {message}" if location else message)
    return "\n".join(messages) or str(error)


class KliamkaArg:
    """Descriptor for CLI arguments.

    Args:
        flag: The flag name (e.g. "--verbose" or "filename").
        help_text: Help text for the argument.
        default: Default value when not provided.
        positional: Whether this is a positional argument.
        env: Environment variable name for fallback.
        short: Short flag alias (e.g. "-v").
        mutually_exclusive: Group name for mutual exclusion.
        converter: Optional callable that converts a raw CLI string into the
            target type. Overrides any registered global converter for the
            same annotation.
    """

    def __init__(
        self,
        flag: str,
        help_text: str = "",
        default: Any = None,
        positional: bool = False,
        env: Optional[str] = None,
        short: Optional[str] = None,
        mutually_exclusive: Optional[str] = None,
        converter: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.flag = flag
        self.help_text = help_text
        self.default = default
        self.positional = positional
        self.env = env
        self.short = short
        self.mutually_exclusive = mutually_exclusive
        self.converter = converter
        self.name = ""

    def __set_name__(self, owner: Type, name: str) -> None:
        self.name = name


class ParserMeta:
    """Container for parser customization options.

    Attributes:
        prog: Program name for help text.
        usage: Custom usage string.
        epilog: Text after the help message.
        version: Version string for --version flag.
    """

    def __init__(
        self,
        prog: Optional[str] = None,
        usage: Optional[str] = None,
        epilog: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        self.prog = prog
        self.usage = usage
        self.epilog = epilog
        self.version = version


class KliamkaArgClass(BaseModel):
    """Base class for CLI argument definitions.

    Subclass this with KliamkaArg fields to define your CLI.
    Supports Pydantic validators via @model_validator.

    Set ``parser_meta`` class variable for customization::

        class MyArgs(KliamkaArgClass):
            parser_meta = ParserMeta(
                prog="myapp",
                version="myapp 1.0",
                epilog="See docs for more info.",
            )
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "ignored_types": (ParserMeta,),
    }

    @classmethod
    def _get_parser_meta(cls) -> ParserMeta:
        """Get parser meta from class hierarchy."""
        for klass in cls.__mro__:
            if "parser_meta" in klass.__dict__:
                meta = klass.__dict__["parser_meta"]
                if isinstance(meta, ParserMeta):
                    return meta
        return ParserMeta()

    @classmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """Create an ArgumentParser from the class definition."""
        meta = cls._get_parser_meta()
        parser_kwargs: dict[str, Any] = {
            "description": cls.__doc__ or "",
        }

        if meta.prog is not None:
            parser_kwargs["prog"] = meta.prog
        if meta.usage is not None:
            parser_kwargs["usage"] = meta.usage
        if meta.epilog is not None:
            parser_kwargs["epilog"] = meta.epilog

        parser = argparse.ArgumentParser(**parser_kwargs)

        if meta.version is not None:
            parser.add_argument(
                "--version",
                action="version",
                version=meta.version,
            )

        _populate_parser(parser, cls)
        return parser

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "KliamkaArgClass":
        """Create instance from parsed arguments.

        Raises:
            KliamkaError: If Pydantic validation fails. The error message is
                simplified (Pydantic prefixes and URLs removed) for CLI display.
        """
        kwargs: dict[str, Any] = {}
        for field_name, field_info in cls.model_fields.items():
            if not isinstance(field_info.default, KliamkaArg):
                kwargs[field_name] = getattr(args, field_name, field_info.default)
                continue

            field_value = field_info.default
            is_positional = field_value.positional or not field_value.flag.startswith(
                "-"
            )
            if is_positional:
                arg_name = field_value.flag.replace("-", "_")
            else:
                arg_name = field_value.flag.lstrip("-").replace("-", "_")

            cli_value = getattr(args, arg_name, None)
            annotation = field_info.annotation

            cli_provided = _was_cli_provided(cli_value, annotation, field_value)

            if cli_provided:
                kwargs[field_name] = cli_value
            elif field_value.env and os.environ.get(field_value.env):
                env_val = os.environ[field_value.env]
                kwargs[field_name] = _parse_env_value(env_val, annotation, field_value)
            else:
                kwargs[field_name] = (
                    cli_value if cli_value is not None else field_value.default
                )

        try:
            return cls(**kwargs)
        except ValidationError as exc:
            raise KliamkaError(_format_validation_error(exc)) from exc


def _parse_env_value(
    value: str,
    annotation: Any,
    field_value: "KliamkaArg | None" = None,
) -> Any:
    """Parse an environment variable value to the target type.

    Type resolution is delegated to :func:`_resolve_type_converter` so that
    env-var parsing uses the same 5-step order (explicit ``field_value.converter``
    → global registry → Enum → ``List[T]`` element → fallback) as argparse.
    The only env-specific behavior kept here is the boolean short-circuit —
    argparse-style converters don't understand env spellings like ``"yes"`` /
    ``"on"`` — and the comma-splitting of list values before per-element
    conversion.
    """
    if annotation is None:
        return value

    unwrapped, _ = _unwrap_optional(annotation)

    # Env-var booleans accept more spellings than argparse converters do,
    # so keep the short-circuit here instead of routing through the resolver.
    if unwrapped is bool:
        return value.lower() in ("true", "1", "yes", "on")

    # Lists: split first, then convert each element using the resolver.
    if _is_list_type(unwrapped):
        if not value:
            return []
        element_type = _get_list_element_type(unwrapped)
        values = [v.strip() for v in value.split(",")]
        return [_parse_env_value(v, element_type) for v in values]

    converter = _resolve_type_converter(unwrapped, field_value)
    if converter is not None:
        return converter(value)

    # Resolver returned None — mirror argparse's convention of using the
    # annotation itself as the converter (e.g. ``int("42")``, ``float("1.5")``).
    if callable(unwrapped) and unwrapped is not str:
        try:
            return unwrapped(value)
        except (TypeError, ValueError):
            return value

    return value


def _was_cli_provided(cli_value: Any, annotation: Any, field_value: KliamkaArg) -> bool:
    """Determine if a CLI value was explicitly provided."""
    if _is_bool_annotation(annotation):
        return cli_value is True

    is_list = _is_list_type(annotation) or (
        annotation is not None
        and hasattr(annotation, "__origin__")
        and getattr(annotation, "__origin__", None) is Union
        and any(
            _is_list_type(a)
            for a in getattr(annotation, "__args__", ())
            if a is not type(None)
        )
    )

    if is_list:
        return bool(cli_value)

    return cli_value is not None and cli_value != field_value.default
