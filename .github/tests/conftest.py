"""Shared fixtures and helpers for the .github contract tests.

These tests assert the conventions documented in
`.github/workflows/README.md` and `.github/actions/README.md`, plus the
`$/` self-repository rules introduced by the rec #1 migration.

Everything here parses the YAML rather than grepping it. A raw-text scan
produces false positives: `uses:` appears inside multi-line `run:` heredocs
frequently enough that a regex over the file finds phantom references.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
ACTIONS_DIR = REPO_ROOT / ".github" / "actions"

#: Every scope name GitHub accepts in a `permissions:` block.
PERMISSION_SCOPES = frozenset(
    {
        "actions",
        "attestations",
        "checks",
        "contents",
        "deployments",
        "discussions",
        "id-token",
        "issues",
        "models",
        "packages",
        "pages",
        "pull-requests",
        "repository-projects",
        "security-events",
        "statuses",
    }
)

#: `owner/repo/path@<40-hex-sha>` -- the repo's only accepted third-party form.
HASH_PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def load_yaml(path: Path):
    """Parse one YAML file, failing the test with the path if it is broken."""
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:  # pragma: no cover - only on a broken file
        pytest.fail(f"{path.relative_to(REPO_ROOT)} is not valid YAML: {exc}")


def trigger_block(doc: dict) -> dict:
    """Return the `on:` block.

    PyYAML resolves an unquoted `on` key to the boolean True (YAML 1.1), so a
    workflow written as `on: workflow_call` arrives here as `{True: ...}`.
    """
    for key in ("on", True, "on "):
        if key in doc:
            value = doc[key]
            return value if isinstance(value, dict) else {"__list__": value}
    return {}


def iter_uses(doc: dict):
    """Yield `(owner_path, key, value)` for every `uses:` in a parsed document.

    Walks the structure rather than the text, so `uses:` inside a `run:`
    script body is never mistaken for a real reference. Handles both the
    step form (`steps[].uses`) and the reusable-workflow job form
    (`jobs.<id>.uses`).
    """
    if not isinstance(doc, dict):
        return

    for key, value in doc.items():
        if key == "uses" and isinstance(value, str):
            yield "", key, value
        elif isinstance(value, dict):
            for found in iter_uses(value):
                yield found
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for found in iter_uses(item):
                        yield found


def classify_reference(ref: str) -> str:
    """Bucket a `uses:` value so tests can assert per kind.

    Returns one of: ``dollar-slash``, ``workspace-relative``,
    ``self-qualified``, ``docker``, ``hash-pinned``, or ``unpinned``.
    """
    ref = ref.strip().strip("'\"")
    if ref.startswith("$/"):
        return "dollar-slash"
    if ref.startswith("./"):
        return "workspace-relative"
    if ref.startswith("docker://"):
        return "docker"
    if re.match(rf"^{REPO_OWNER}/{REPO_NAME}/", ref):
        return "self-qualified"
    if HASH_PINNED.match(ref):
        return "hash-pinned"
    return "unpinned"


REPO_OWNER = "NerdIT-Tech"
REPO_NAME = ".github"


def normalise_permissions(value) -> set[str]:
    """Expand a `permissions:` value into a set of scope names.

    Handles the three legal shapes: a mapping, the `read-all`/`write-all`
    strings, and null (which means "inherit the caller's grant").
    """
    if value is None:
        return set()
    if value == "write-all":
        return set(PERMISSION_SCOPES)
    if value == "read-all":
        return set(PERMISSION_SCOPES)
    if isinstance(value, dict):
        return set(value)
    return set()


def declared_permissions(doc: dict) -> dict[str, set[str]]:
    """Map job name -> permissions that job declares, for one workflow."""
    result: dict[str, set[str]] = {}
    for name, job in (doc.get("jobs") or {}).items():
        if isinstance(job, dict):
            result[name] = normalise_permissions(job.get("permissions"))
    return result


def composite_actions() -> list[Path]:
    """Every composite action manifest in the repo."""
    return sorted(ACTIONS_DIR.glob("*/action.yml"))


def action_paths() -> list[str]:
    """`$/`-style repo-root paths for every composite action."""
    return [
        p.relative_to(REPO_ROOT).with_suffix("").as_posix() for p in composite_actions()
    ]


def workflow_paths() -> list[Path]:
    """Every workflow file, at the top level or inside a component directory.

    Reusable workflows live at `reusable-<purpose>/reusable-<purpose>.yml` so
    release-please can attribute commits to them -- its `CommitSplit` matches
    package paths by directory prefix, so a package path pointing at a file
    never matches any commit and the component can never be released. A
    non-recursive glob here would silently drop every one of them.
    """
    return sorted(WORKFLOWS_DIR.rglob("*.yml"))


def reusable_workflows() -> list[Path]:
    """Every workflow that exposes `on: workflow_call`."""
    found = []
    for path in workflow_paths():
        doc = load_yaml(path)
        if "workflow_call" in trigger_block(doc):
            found.append(path)
    return found


def is_action_manifest(path: Path) -> bool:
    return path.name == "action.yml" and path.parent.parent == ACTIONS_DIR


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def rel_path(pathlike: str) -> str:
    """Normalise a path string for messages, anchored at the repo root."""
    return os.path.normpath(pathlike).replace(os.sep, "/")
