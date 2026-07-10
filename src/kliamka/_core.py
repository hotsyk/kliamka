"""Core descriptors, base class, and validation error formatting."""

from __future__ import annotations

import argparse
import os
from functools import cache
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, ValidationError

from ._converters import _resolve_type_converter
from ._helpers import (
    _UNSET,
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


def _format_validation_error(
    error: ValidationError,
    env_sources: Optional[dict[str, str]] = None,
) -> str:
    """Format a Pydantic validation error for cleaner CLI output.

    Args:
        error: The Pydantic validation error to format.
        env_sources: Mapping of model field names to environment variables that
            supplied their values.
    """
    sources = env_sources or {}
    messages: list[str] = []
    for item in error.errors(include_url=False):
        location_parts = tuple(item.get("loc", ()))
        location = ".".join(str(part) for part in location_parts)
        message = _strip_pydantic_prefix(item.get("msg", "Invalid value"))

        field_name = str(location_parts[0]) if location_parts else ""
        env_name = sources.get(field_name)
        if env_name:
            label = f"environment variable {env_name}"
            if location:
                label += f" ({location})"
        elif not location and sources:
            env_names = ", ".join(sorted(set(sources.values())))
            label = f"environment variable(s) {env_names}"
        else:
            label = location

        messages.append(f"{label}: {message}" if label else message)
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

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        from ._parser import _clear_parser_plan_cache

        _clear_parser_plan_cache()

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
    @cache
    def _get_cli_field_names(cls) -> tuple[str, ...]:
        """Return validated CLI-backed field names for the model."""
        names = []
        for field_name, field_info in cls.model_fields.items():
            if not isinstance(field_info.default, KliamkaArg):
                continue
            try:
                _unwrap_optional(field_info.annotation)
            except ValueError as exc:
                raise KliamkaError(f"{field_name}: {exc}") from exc
            names.append(field_name)
        return tuple(names)

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

        Each field resolves in priority order: CLI value > environment
        variable > declared default. Parsers built by :meth:`create_parser`
        register the ``_UNSET`` sentinel as the argparse default, so an
        argument explicitly given on the command line always wins — even
        when its value equals the declared default.

        Raises:
            KliamkaError: If Pydantic validation fails or an environment
                variable value cannot be converted to the field type. The
                message is simplified for CLI display.
        """
        namespace_values = vars(args)
        cli_field_names = cls._get_cli_field_names()
        if cli_field_names:
            for name in cli_field_names:
                if namespace_values.get(name, _UNSET) is _UNSET:
                    break
            else:
                if cls.model_config.get("extra") in (None, "ignore"):
                    model_values = namespace_values
                else:
                    model_values = {
                        name: namespace_values[name]
                        for name in cls.model_fields
                        if name in namespace_values
                    }
                try:
                    return cls.__pydantic_validator__.validate_python(model_values)
                except ValidationError as exc:
                    raise KliamkaError(_format_validation_error(exc)) from exc

        kwargs: dict[str, Any] = {}
        env_sources: dict[str, str] = {}
        for field_name, field_info in cls.model_fields.items():
            if not isinstance(field_info.default, KliamkaArg):
                kwargs[field_name] = getattr(args, field_name, field_info.default)
                continue

            field_value = field_info.default
            annotation = field_info.annotation
            try:
                _unwrap_optional(annotation)
            except ValueError as exc:
                raise KliamkaError(f"{field_name}: {exc}") from exc

            cli_value = getattr(args, field_name, _UNSET)

            if cli_value is not _UNSET:
                kwargs[field_name] = cli_value
            elif field_value.env and field_value.env in os.environ:
                env_name = field_value.env
                env_sources[field_name] = env_name
                try:
                    kwargs[field_name] = _parse_env_value(
                        os.environ[env_name], annotation, field_value
                    )
                except (argparse.ArgumentTypeError, TypeError, ValueError) as exc:
                    raise KliamkaError(
                        f"environment variable {env_name}: {exc}"
                    ) from exc
            else:
                kwargs[field_name] = _fallback_default(annotation, field_value)

        try:
            return cls(**kwargs)
        except ValidationError as exc:
            raise KliamkaError(_format_validation_error(exc, env_sources)) from exc


def _fallback_default(annotation: Any, field_value: KliamkaArg) -> Any:
    """Resolve the value for an argument absent from both CLI and env."""
    if field_value.default is not None:
        return field_value.default
    if _is_bool_annotation(annotation):
        return False
    unwrapped, _ = _unwrap_optional(annotation)
    if _is_list_type(unwrapped):
        return []
    return None


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

    # Env-var booleans accept common case-insensitive spellings while
    # rejecting typos instead of silently treating them as false.
    if unwrapped is bool:
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off"):
            return False
        raise ValueError(
            f"invalid boolean value {value!r}; expected one of "
            "true, 1, yes, on, false, 0, no, off"
        )

    # Lists: split first, then convert each element using the resolver.
    # field_value is threaded through so an explicit per-field converter
    # applies to each element, matching argparse's per-token behavior.
    if _is_list_type(unwrapped):
        if not value:
            return []
        element_type = _get_list_element_type(unwrapped)
        values = [v.strip() for v in value.split(",")]
        return [_parse_env_value(v, element_type, field_value) for v in values]

    converter = _resolve_type_converter(unwrapped, field_value)
    if converter is not None:
        return converter(value)

    # Resolver returned None — mirror argparse's convention of using the
    # annotation itself as the converter (e.g. ``int("42")``, ``float("1.5")``).
    # Conversion failures intentionally propagate so ``from_args`` can attach
    # the environment variable name to the user-facing error.
    if callable(unwrapped) and unwrapped is not str:
        return unwrapped(value)

    return value
