# Kliamka product requirements

- **Status:** Current baseline for Kliamka 0.8.x
- **Originally created:** 2026-04-08
- **Last updated:** 2026-07-10

## Product summary

Kliamka is a focused Python CLI library that turns Pydantic models into `argparse` command-line interfaces. It serves developers building small and medium command-line applications who want declarative type conversion and validation without adopting a separate command framework.

## Goals

1. Make a typed Pydantic model the authoritative representation of parsed CLI input.
2. Preserve familiar `argparse` help, usage, errors, and process behavior.
3. Support common CLI configuration sources with deterministic CLI → environment → default precedence.
4. Keep the public API small, explicit, documented, and stable within normal semantic-versioning expectations.
5. Return fresh parsers and models while keeping parser construction efficient.
6. Remain straightforward to test with explicit argument sequences and direct parser access.

## Non-goals

- Replacing every `argparse.add_argument()` feature.
- Inferring ambiguous union parsing.
- Providing terminal rendering, prompts, shell completion, or an application runtime.
- Managing configuration files or secrets.
- Automatically generating negative boolean flags such as `--no-feature` in the current release.
- Providing nested subcommand trees beyond the current main-plus-command model.

## Target users

### Library author

Builds a reusable Python command or package entry point and wants typed inputs, predictable errors, and PEP 561 compatibility.

### Application developer

Builds an internal tool with options, environment configuration, domain validation, and several Git-style commands.

### Maintainer and tester

Needs deterministic parser construction, explicit `argv`, clean failure messages, and compatibility across supported Python versions.

## Functional requirements

### Declarative argument models

- Applications define models by subclassing `KliamkaArgClass`.
- CLI-backed fields use `KliamkaArg` as their Pydantic default.
- Model class docstrings provide parser descriptions.
- Constructed values are ordinary Pydantic models and support Pydantic validators.

### Arguments and annotations

Kliamka must support:

- options and positional arguments;
- long options and optional short aliases;
- `str`, `int`, `float`, and presence-style `bool` values;
- string- and integer-valued `Enum` subclasses;
- `list[T]` values;
- `Optional[T]` and `T | None` for one supported type;
- optional positional values and declared defaults;
- named mutually exclusive option groups.

Ambiguous wider unions must fail cleanly with `KliamkaError` instead of producing a traceback or silently selecting a type.

### Value precedence

Each CLI-backed field must resolve independently in this order:

1. an explicitly supplied CLI value;
2. a configured environment variable;
3. the descriptor default;
4. a type fallback of `False` for booleans, `[]` for lists, or `None` otherwise.

Explicit CLI values must win even when equal to the declared default. An existing environment variable must count as supplied even when its value is empty.

### Environment conversion

- Scalar environment values use the same converter resolution as CLI tokens.
- Boolean values accept documented strict, case-insensitive true/false spellings.
- Lists use comma-separated items with whitespace trimming.
- Invalid values raise `KliamkaError` and identify the source environment variable.
- Environment variable names appear as hints in generated argument help.

### Custom converters

- A field may define a local converter accepting one string.
- Applications may register and unregister a converter by annotation type.
- Local converters take precedence over registered converters.
- Enum and list conversion remain built in.
- Converter registry changes invalidate cached parser plans.
- `ValueError` and `TypeError` become clean user-facing conversion errors.

### Validation and errors

- Pydantic field and model validators run after source resolution.
- Direct `from_args()` calls raise simplified `KliamkaError` messages.
- Decorated CLIs render those messages through the relevant `argparse` parser.
- User input failures must not expose internal tracebacks during normal decorated execution.
- Subcommand field failures use the selected command parser's usage and metadata.

### Single-command decorator

`@kliamka_cli` must:

- accept an argument model and optional explicit `argv` sequence;
- create a fresh parser and validated model per invocation;
- inject the model before caller-supplied arguments;
- preserve wrapped function metadata.

### Subcommands

`@kliamka_subcommands` must:

- accept a main model, a command-name-to-model mapping, and optional `argv`;
- require command selection;
- inject the main model, command name, and selected command model;
- support parser metadata on the main and each command model;
- reject destinations that would silently overwrite main values;
- reserve `_command` for internal command selection;
- allow separate commands to reuse field names.

### Parser customization and embedding

- `ParserMeta` supports program name, usage, epilog, and optional `--version` output.
- `KliamkaArgClass.create_parser()` provides direct parser access.
- `KliamkaArgClass.from_args()` converts an intermediate namespace into a validated model.
- Public behavior must not require applications to depend on private parser internals.

## Public API requirements

The supported root-package API consists of:

- `KliamkaArg`;
- `KliamkaArgClass`;
- `KliamkaError`;
- `ParserMeta`;
- `kliamka_cli`;
- `kliamka_subcommands`;
- `register_converter`;
- `unregister_converter`;
- package version and author metadata.

New public symbols require documentation, type hints, tests, and a changelog entry.

## Compatibility and packaging

- Support CPython 3.11, 3.12, 3.13, and 3.14.
- Support Pydantic 2.x.
- Ship a `py.typed` marker for PEP 561 consumers.
- Produce installable wheel and source distributions.
- Verify both distribution formats in isolated smoke tests.
- Keep the root import surface independent of internal module organization.

## Quality requirements

- Unit tests cover parsing, precedence, validation, errors, converters, and regressions.
- CI runs tests across all supported Python versions.
- Mypy, Ruff lint, and Ruff format checks remain clean.
- Public examples run as documented.
- Parser/model caching must preserve fresh-object and help isolation semantics.
- Performance changes must not alter benchmark workloads or user-visible behavior.
- Workflow actions are pinned to immutable revisions and use least privilege.

## Documentation requirements

- Markdown documentation covers installation, arguments, environment variables, subcommands, converters, validation, customization, the public API, examples, troubleshooting, and development.
- `make docs` performs a clean strict MkDocs build locally.
- Documentation deploys through GitHub Pages after a successful build on pushes/merges to a primary branch.
- Broken internal links and MkDocs warnings fail the build.
- `docs/TODO.md` remains the central development log.

## Roadmap candidates

The following are candidates, not current commitments:

- explicit required optional flags;
- generated negative boolean flags;
- a convenience `MyArgs.parse()` class method;
- deriving flag names from model fields;
- first-class `choices=` and counting flags;
- richer or nested command dispatch;
- broader documented parser extension points.

Roadmap work must preserve current precedence, error rendering, compatibility, and parser-isolation contracts.
