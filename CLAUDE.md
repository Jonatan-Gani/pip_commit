# pip_commit

## Macro
A global Git pre-commit hook that keeps a repository's `requirements.txt` in sync
with the active Python environment on every commit. The intent is hands-off
dependency tracking: install or update a `core.hooksPath` hook once, and every
commit in every repo regenerates and stages a fresh `requirements.txt`, with an
opt-out filter for packages that should never be pinned (e.g. local/vendor
libraries like `ibapi`). The project is the hook itself plus setup documentation;
there is no application runtime.

## Project tree
```
pip_commit/
├── pre-commit      # the hook script
└── README.md       # setup and usage documentation
```

## Root files

### pre-commit
POSIX shell script intended for use as a Git `pre-commit` hook (typically via a
global `core.hooksPath`). Inputs: the active Python environment reachable through
`pip` and an invocation from within a Git work tree. Side effects: resolves the
repo root with `git rev-parse --show-toplevel`, writes `requirements.txt` there
from `pip freeze`, strips lines matching the `REMOVE_DEP` package name (default
`ibapi`) via case-insensitive grep, and stages the file with `git add`. Output:
exit `0` on success with progress lines on stdout; exits `1` with an `ERROR:`
stdout line if `requirements.txt` was not created. Staging failures emit a
`WARNING:` line but do not abort the commit.

### README.md
Setup and usage documentation: how to create a global hooks directory, point
`core.hooksPath` at it, install the hook, mark it executable, and test it.
Inputs/outputs: none (prose only). Note: README describes an interactive
confirmation prompt that the current `pre-commit` script does not implement.

## Subdirectories
None.

## Conventions
- Write correctly-typed, efficient code.
- Prefer vectors and matrices over loops.
- Input/output sections describe data, never code.
- Keep the hook POSIX `sh`-compatible and Unix (LF) line endings for cross-platform Git Bash use.

## Recommended skills
- context-map-builder — used to generate this context map. No other skill usage detected.

## References
- Task list: TASKS.md
- Preserved human notes: projectNotes.md (per directory)
