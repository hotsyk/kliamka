# Development and deployment

This page covers repository setup, quality checks, local documentation builds, and the GitHub Pages deployment path.

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for the repository bootstrap command
- GNU Make or a compatible `make`
- Docker only for the optional multi-version local matrix

## Set up a checkout

```bash
git clone https://github.com/hotsyk/kliamka.git
cd kliamka
make init-dev
make install
```

`make init-dev` creates `.venv` and installs package, test, lint, and documentation dependencies. `make install` refreshes the editable package and core development tools in an existing environment.

## Common commands

| Command | Purpose |
| --- | --- |
| `make run` | Print the installed Kliamka version |
| `make test` | Run unit tests excluding packaging smoke tests |
| `make test-package` | Build and smoke-install wheel and sdist artifacts |
| `make test-all` | Run the complete pytest suite |
| `make lint` | Run mypy, Ruff lint, and Ruff format checks |
| `make format` | Format Python source and tests |
| `make docs` | Build documentation strictly into `site/` |
| `make docs-serve` | Serve documentation locally with live reload |
| `make test-docker VERSION=3.12` | Test one supported Python in Docker |
| `make test-docker-all` | Test Python 3.11–3.14 in Docker |
| `make clean` | Remove generated Python and documentation artifacts |

## Build documentation locally

Install the optional documentation dependency group and run the same strict build used by CI:

```bash
.venv/bin/python -m pip install -e '.[docs]'
make docs
```

The generated site is written to `site/`, which is ignored by Git. `--strict` turns MkDocs warnings into failures so broken internal links and invalid configuration cannot deploy silently.

Preview with live reload:

```bash
make docs-serve
```

Open the URL printed by MkDocs, normally `http://127.0.0.1:8000/`. Stop the server with <kbd>Ctrl</kbd>+<kbd>C</kbd>.

## Documentation conventions

- Write documentation in Markdown under `docs/`.
- Topical files use a date prefix and lowercase snake case.
- Keep `mkdocs.yml` navigation synchronized with public pages.
- Use relative links between documentation pages.
- Use repository URLs for source files outside `docs/`; MkDocs cannot validate links outside its documentation tree.
- Run `make docs` before opening or merging a pull request.
- Update `docs/TODO.md` when documentation architecture or deployment behavior changes.

## GitHub Pages workflow

`.github/workflows/pages.yml` builds and deploys the site on pushes to `main` or `master`, including merge commits, and supports manual dispatch.

The workflow:

1. checks out the exact commit without persisting credentials;
2. installs Python and the `docs` optional dependency group;
3. configures GitHub Pages;
4. runs the strict MkDocs build;
5. uploads `site/` as a Pages artifact;
6. deploys from a separate job with environment protection and only the required Pages/OIDC permissions.

All third-party workflow actions are pinned to immutable commit SHAs. The build job has read-only repository permission; only the deployment job receives `pages: write` and `id-token: write`.

!!! important "Repository setting"
    In **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source. The workflow does not write generated files to a `gh-pages` branch.

## Branch behavior

The repository's current default branch is `main`, while some integrations may still refer to `master`. The workflow listens to both names so merges to either protected primary branch deploy documentation. Remove the unused name after all repository settings and integrations agree on one branch.

## Release and CI relationship

The Pages workflow is independent of package publication. A documentation deployment does not create a tag, GitHub Release, or PyPI distribution. Existing CI remains responsible for supported Python tests, linting, packaging smoke tests, benchmarks, and workflow security analysis.

## Pre-merge checklist

```bash
make lint
make test
make docs
```

For packaging or release-related changes, also run:

```bash
make test-package
```

Confirm `git status` contains only intentional source documentation and configuration changes; do not commit the generated `site/` directory.
