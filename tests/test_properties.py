"""Property-based tests for freeze formatting and exclusion filtering.

We don't try to spec what `pip freeze` emits exactly. We assert the *invariants*
our code must preserve no matter what input it sees.
"""

from __future__ import annotations

import re
from importlib.metadata import Distribution
from typing import cast

from hypothesis import given, settings
from hypothesis import strategies as st

from pip_commit.freeze import filter_freeze, freeze_installed

# Plausible PEP 503-ish package names: alnum, dot, dash, underscore.
_first = st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_rest = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._",
    max_size=20,
)
package_names = st.builds(lambda h, t: h + t, _first, _rest)

versions = st.builds(
    "{}.{}.{}".format,
    st.integers(0, 99),
    st.integers(0, 99),
    st.integers(0, 99),
)

freeze_lines = st.builds(lambda n, v: f"{n}=={v}", package_names, versions)


def _name_of(line: str) -> str | None:
    m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line)
    return m.group(1).lower() if m else None


@given(st.lists(freeze_lines, max_size=30), st.lists(package_names, max_size=5))
def test_filter_freeze_never_emits_excluded(lines: list[str], exclude: list[str]) -> None:
    drop = {x.lower() for x in exclude}
    out = filter_freeze("\n".join(lines), exclude)
    for line in out.splitlines():
        name = _name_of(line)
        if name is not None:
            assert name not in drop


@given(st.lists(freeze_lines, max_size=30))
def test_filter_freeze_empty_exclude_preserves_all_names(lines: list[str]) -> None:
    out = filter_freeze("\n".join(lines), [])
    for line in lines:
        name = _name_of(line)
        if name is None:
            continue
        # Every input package name must still appear in the output.
        assert any(_name_of(o) == name for o in out.splitlines())


@given(st.lists(freeze_lines, min_size=1, max_size=30))
def test_filter_freeze_excluding_every_name_yields_empty(lines: list[str]) -> None:
    names = [n for n in (_name_of(ln) for ln in lines) if n is not None]
    out = filter_freeze("\n".join(lines), names)
    assert out == ""


@given(st.lists(freeze_lines, max_size=30), st.lists(package_names, max_size=5))
def test_filter_freeze_idempotent(lines: list[str], exclude: list[str]) -> None:
    once = filter_freeze("\n".join(lines), exclude)
    twice = filter_freeze(once, exclude)
    assert once == twice


@given(st.lists(freeze_lines, max_size=30))
def test_filter_freeze_output_ends_with_newline_or_is_empty(lines: list[str]) -> None:
    out = filter_freeze("\n".join(lines), [])
    assert out == "" or out.endswith("\n")


# --- freeze_installed properties --------------------------------------------


class _FakeDist:
    def __init__(self, name: str, version: str) -> None:
        self.metadata = {"Name": name}
        self.version = version

    def read_text(self, _name: str) -> str | None:
        return None


@given(
    st.lists(
        st.tuples(package_names, versions),
        max_size=30,
        unique_by=lambda t: t[0].lower(),
    )
)
@settings(max_examples=50)
def test_freeze_installed_is_sorted_case_insensitive(items: list[tuple[str, str]]) -> None:
    dists = [cast(Distribution, _FakeDist(n, v)) for n, v in items]
    out = freeze_installed(dists)
    names = [_name_of(line) for line in out.splitlines()]
    names_no_none = [n for n in names if n is not None]
    assert names_no_none == sorted(names_no_none)


@given(
    st.lists(
        st.tuples(package_names, versions),
        min_size=1,
        max_size=30,
        unique_by=lambda t: t[0].lower(),
    )
)
@settings(max_examples=50)
def test_freeze_installed_emits_one_line_per_dist(items: list[tuple[str, str]]) -> None:
    dists = [cast(Distribution, _FakeDist(n, v)) for n, v in items]
    out = freeze_installed(dists)
    assert len(out.splitlines()) == len(items)
    assert out.endswith("\n")
