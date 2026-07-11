# Troubleshooting

## A union annotation is rejected

**Symptom:** parser creation raises an error mentioning an unsupported union.

Kliamka supports `Optional[T]` and `T | None`, but not ambiguous unions such as `int | str`.

```python
# Supported
value: int | None = KliamkaArg("--value")

# Not supported
value: int | str = KliamkaArg("--value")
```

Choose one CLI syntax and convert it explicitly, or parse a string and use a Pydantic validator for domain interpretation.

## An optional value becomes `None`

An annotation does not itself provide an application default. Supply `default=` when a concrete fallback is required:

```python
count: int | None = KliamkaArg("--count", default=3)
```

Absent booleans and lists have special fallbacks (`False` and `[]`); other absent values fall back to `None` when no descriptor default exists.

## `--flag true` fails

CLI boolean fields are presence flags. Use `--flag` to set `True` and omit it otherwise. String boolean spellings are supported only for environment fallbacks.

## A list consumes unexpected tokens

List options consume zero or more values until another recognized option or the end of input:

```bash
app --files a.txt b.txt --verbose
```

If a following token begins with `-`, consider option ordering and standard `argparse` escaping rules. Environment lists use commas instead of spaces.

## An environment value is ignored

Check all of the following:

1. `env="NAME"` exactly matches the environment variable name;
2. the command line did not explicitly supply the field;
3. you converted the parser namespace with `ArgClass.from_args()`;
4. the process actually inherited the variable.

CLI values intentionally take precedence, including values equal to the default.

## An empty environment value does not use the default

This is intentional. Presence, not truthiness, decides whether an environment fallback is selected. Validate non-empty input with Pydantic or remove the variable from the environment.

## A converter crashes parsing

Converters should raise `ValueError` or `TypeError` for invalid user input. Kliamka wraps those exception types into clean parser errors. Avoid leaking secrets or internal state in exception messages.

Register global converters before creating parsers. Clean up global registrations in tests with `unregister_converter()`.

## Main and subcommand fields conflict

Subcommands share an intermediate namespace with the main parser. Rename one model field or make both destinations distinct. `_command` is reserved and cannot be used as a CLI destination.

The same field name may be reused by different command models because only one subcommand parses per invocation.

## Validation exits instead of raising `KliamkaError`

Direct `ArgClass.from_args()` calls raise `KliamkaError`. Decorators catch that exception and call `ArgumentParser.error()`, which prints usage and exits with standard `argparse` behavior.

Use direct parser/model calls when a host application needs programmatic error handling.

## Parsed namespaces show `<kliamka.UNSET>`

The raw namespace is intermediate state. Kliamka uses a falsy sentinel to distinguish an omitted CLI field from an explicit value. Always call `from_args()` before reading application values.

## Help does not show `--version`

Set `version` in a model's `ParserMeta`:

```python
parser_meta = ParserMeta(version="myapp 1.2.3")
```

Kliamka does not infer an application version automatically.

## Documentation build fails

Install development dependencies and use the strict target:

```bash
make init-dev
make docs
```

`make docs` treats broken internal links, invalid navigation, and other MkDocs warnings as build failures. See [Development and deployment](20260710_development.md).

## Still stuck?

Search existing [GitHub issues](https://github.com/hotsyk/kliamka/issues), then open a minimal reproducible example including:

- Python, Kliamka, and Pydantic versions;
- the smallest argument model that fails;
- the exact command or explicit `argv`;
- relevant non-secret environment values;
- complete error output.
