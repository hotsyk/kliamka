# Kliamka Version History

## 0.3.0 

New features:

- **Positional arguments support** - Arguments without `--` prefix
  ```python
  filename: str = KliamkaArg("filename", "Input file", positional=True)
  ```

- **List/array arguments support** - Multiple values with `List[T]` type
  ```python
  files: List[str] = KliamkaArg("--files", "Input files")
  ```

- **Environment variable fallback** - CLI > ENV > default priority
  ```python
  api_key: str = KliamkaArg("--api-key", "API key", env="API_KEY")
  ```

- **Subcommands support** - Git-style CLI with `@kliamka_subcommands`
  ```python
  @kliamka_subcommands(MainArgs, {"add": AddArgs, "remove": RemoveArgs})
  def main(args, command, cmd_args):
      ...
  ```

## 0.2.0

- Added Enum support (string and integer valued enums)
- Enum parsing by name or value
- Improved type handling

## 0.1.0

- Initial release
- Basic CLI argument parsing with Pydantic validation
- Support for string, int, bool argument types
- `@kliamka_cli` decorator for automatic argument injection
- Optional arguments with default values
