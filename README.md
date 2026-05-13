# pip-commit

Keep `requirements.txt` in sync with your active Python environment, automatically, on every `git commit`.

[![CI](https://github.com/jonatan-gani/pip_commit/actions/workflows/ci.yml/badge.svg)](https://github.com/jonatan-gani/pip_commit/actions/workflows/ci.yml)

## What it does

On `git commit`, `pip-commit`:

1. Confirms you're inside a Python project and a virtualenv (refuses to capture system-wide packages by default).
2. Optionally asks `regenerate requirements.txt? [Y/n]` — one keystroke.
3. Runs `pip freeze --exclude-editable`, applies your exclude list.
4. Writes `requirements.txt` **only if it actually changed**, then `git add`s it.

Idempotent, no-op on non-Python repos, and safe to run in IDE/GUI commit clients (auto-yes when stdin isn't a TTY).

## Install

### Recommended: via the [pre-commit](https://pre-commit.com) framework

In your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/jonatan-gani/pip_commit
    rev: v0.1.0
    hooks:
      - id: pip-commit
```

Then once:

```sh
pip install pre-commit
pre-commit install
```

That's it. Every commit will refresh `requirements.txt`.

### As a CLI tool

```sh
pip install pip-commit
pip-commit --yes
```

### As a global git hook (legacy shell version)

For users who want one hook across **all** their repos without per-repo `.pre-commit-config.yaml`:

```sh
mkdir -p ~/.global-git-hooks
curl -L https://raw.githubusercontent.com/jonatan-gani/pip_commit/main/pre-commit \
  -o ~/.global-git-hooks/pre-commit
chmod +x ~/.global-git-hooks/pre-commit
git config --global core.hooksPath ~/.global-git-hooks
```

The shell version has feature parity for the basics and skips silently on non-Python repos.

## Configuration

Add a `[tool.pip-commit]` section to your `pyproject.toml`:

```toml
[tool.pip-commit]
output = "requirements.txt"   # where to write
exclude = ["ibapi", "my-private-pkg"]  # distributions to drop (case-insensitive)
require_venv = true           # refuse to run against system Python
prompt = true                 # ask y/n before freezing
```

Or drop a standalone `.pip-commit.toml` at repo root with the same keys (no `[tool.pip-commit]` header). Standalone wins over pyproject.

### CLI flags

| Flag | Effect |
| --- | --- |
| `-o, --output PATH` | Override output path |
| `-e, --exclude NAME` | Drop a distribution (repeatable) |
| `-y, --yes` / `--no-prompt` | Skip the y/n prompt |
| `--allow-system` | Allow running outside a venv |
| `--no-stage` | Don't `git add` the result |
| `--version` | Print version |

### Environment variables (shell hook)

The legacy shell hook reads these instead:

- `PIP_COMMIT_OUTPUT` — output path
- `PIP_COMMIT_EXCLUDE` — comma-separated names
- `PIP_COMMIT_YES` — skip prompt
- `PIP_COMMIT_ALLOW_SYSTEM` — allow non-venv
- `PIP_COMMIT_SKIP` — turn the hook off entirely

## Why not just `pip freeze > requirements.txt`?

You can. `pip-commit` adds the parts that turn "a snippet" into "a workflow":

- Only writes when contents actually change → clean diffs.
- Refuses to freeze a system interpreter → no leaked `pip`/`setuptools`/`wheel`/whatever your distro installed.
- Skips silently on non-Python repos → safe as a global hook.
- One excluded-package list, lives next to your project config.
- Tested across Python 3.9–3.13 on Linux/macOS/Windows.

## Development

```sh
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT — see [LICENSE](LICENSE).
