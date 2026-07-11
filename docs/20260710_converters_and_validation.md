# Converters and validation

Conversion turns one raw token into a Python value. Validation checks the resulting model against application rules. Kliamka supports both stages without replacing `argparse` or Pydantic conventions.

## Per-field converters

Use `converter=` for behavior local to one argument:

```python
from pathlib import Path

from kliamka import KliamkaArg, KliamkaArgClass


def existing_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.exists():
        raise ValueError("path does not exist")
    return path


class Args(KliamkaArgClass):
    config: Path = KliamkaArg(
        "--config",
        "Existing configuration file",
        converter=existing_path,
    )
```

A converter accepts one string and returns the field value. It may raise `ValueError` or `TypeError`; Kliamka converts these into clean argument errors.

## Global converters

Register reusable conversion by annotation type:

```python
from datetime import datetime

from kliamka import KliamkaArg, KliamkaArgClass, register_converter


register_converter(datetime, datetime.fromisoformat)


class Args(KliamkaArgClass):
    since: datetime = KliamkaArg("--since", "ISO-8601 start time")
```

Registration applies to parsers created afterward and invalidates Kliamka's cached parser plans. Register converters during application startup, before invoking decorated entry points.

Remove a registration when it is no longer needed:

```python
from kliamka import unregister_converter

unregister_converter(datetime)
```

Removing an unknown type is a no-op. Tests that mutate the global registry should clean up after themselves to avoid order-dependent behavior.

## Converter resolution

The first applicable strategy wins:

1. the field's explicit `converter`;
2. a converter registered for the unwrapped annotation;
3. Kliamka's enum parser;
4. list element resolution;
5. the raw annotation used as an `argparse` type callable.

Optional annotations are unwrapped first. For `list[T]`, conversion runs per element. A converter explicitly attached to a list field is also applied per CLI token or environment-list item.

## Pydantic field validation

Use Pydantic constraints and validators after parsing:

```python
from pydantic import Field, field_validator

from kliamka import KliamkaArg, KliamkaArgClass


class Args(KliamkaArgClass):
    port: int = Field(
        default=KliamkaArg("--port", "TCP port", default=8080),
        ge=1,
        le=65535,
    )
    host: str = KliamkaArg("--host", "Bind host", default="127.0.0.1")

    @field_validator("host")
    @classmethod
    def host_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("host must not be blank")
        return value
```

Kliamka detects a field as CLI-backed when its Pydantic default is a `KliamkaArg`. If using `Field`, preserve the descriptor as shown in `default=`.

## Cross-field validation

```python
from typing import Self

from pydantic import model_validator


class Args(KliamkaArgClass):
    minimum: int = KliamkaArg("--minimum", "Lower bound", default=0)
    maximum: int = KliamkaArg("--maximum", "Upper bound", default=100)

    @model_validator(mode="after")
    def bounds_are_ordered(self) -> Self:
        if self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self
```

## Error behavior

`KliamkaArgClass.from_args()` raises `KliamkaError` for:

- unsupported unions discovered while building or resolving fields;
- environment conversion failures;
- Pydantic field or model validation failures.

Validation messages are simplified and joined for programmatic callers. Environment-backed validation identifies the source variable where possible.

Decorators catch `KliamkaError` and pass the message to the relevant parser's `error()` method. The CLI therefore prints usage, an `error:` line, and exits with the standard `argparse` status instead of exposing a traceback.

## Conversion or validation?

Use a **converter** when syntax determines the Python object: parsing a timestamp, path, UUID, or domain identifier.

Use **Pydantic validation** when a parsed value must satisfy business rules: ranges, allowed combinations, non-empty content, or filesystem policy that should also apply to programmatically constructed models.

Keeping those responsibilities separate improves reuse and produces clearer tests.
