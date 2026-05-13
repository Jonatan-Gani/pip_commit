from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    git = shutil.which("git") or "git"
    subprocess.run([git, "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(
        [git, "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run([git, "-C", str(tmp_path), "config", "user.name", "Test User"], check=True)
    subprocess.run([git, "-C", str(tmp_path), "config", "commit.gpgsign", "false"], check=True)
    return tmp_path
