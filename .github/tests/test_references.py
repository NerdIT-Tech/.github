"""Cross-cutting invariants over every `uses:` in the repo.

These are the rules that no single file can satisfy on its own: that a
reference points at something real, and that a caller grants the callee the
permissions it needs. The last one is the failure mode this repo has already
hit -- a reusable workflow whose job requests a permission the caller never
grants dies in `startup_failure` with zero jobs created, and the blocking
gate silently never runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import (
    REPO_ROOT,
    classify_reference,
    composite_actions,
    declared_permissions,
    iter_uses,
    load_yaml,
    normalise_permissions,
    relative,
    reusable_workflows,
    workflow_paths,
)

ALL_YAML = sorted(
    [p for p in workflow_paths()]
    + composite_actions()
    + sorted((REPO_ROOT / ".github").glob("*.yml"))
)


def every_reference():
    """Yield `(file, key, value)` for every real `uses:` in the repo."""
    for path in ALL_YAML:
        for _, key, value in iter_uses(load_yaml(path) or {}):
            yield relative(path), key, value


REFERENCES = list(every_reference())


def test_the_scan_actually_found_something():
    """If the walk breaks, every test below would pass vacuously."""
    assert len(REFERENCES) >= 60, (
        f"expected to find the repo's uses: references, found only {len(REFERENCES)}"
    )


@pytest.mark.parametrize(
    "where,key,value",
    REFERENCES,
    ids=[f"{w}:{k}" for w, k, _ in REFERENCES],
)
class TestEveryReference:
    def test_is_a_known_form(self, where, key, value):
        kind = classify_reference(value)
        assert kind in {"dollar-slash", "hash-pinned", "docker"}, (
            f"{where}: {key}: {value!r} is {kind}; expected '$/' or a 40-hex SHA"
        )

    def test_dollar_slash_carries_no_ref(self, where, key, value):
        if classify_reference(value) != "dollar-slash":
            pytest.skip("not a $/ reference")
        assert "@" not in value, (
            f"{where}: {key}: {value!r} -- '$/' resolves to the running commit, "
            "so an @ref contradicts it"
        )

    def test_target_exists(self, where, key, value):
        if classify_reference(value) != "dollar-slash":
            pytest.skip("not a $/ reference")
        target = REPO_ROOT / value.strip()[2:]
        assert target.exists(), f"{where}: {key}: {value!r} does not exist in this repo"

    def test_no_workspace_relative_references(self, where, key, value):
        assert classify_reference(value) != "workspace-relative", (
            f"{where}: {key}: {value!r} -- './' resolves against the caller's "
            "checkout, which is wrong inside a reusable workflow or composite "
            "action (#36). Use '$/'."
        )

    def test_no_fully_qualified_self_references(self, where, key, value):
        assert classify_reference(value) != "self-qualified", (
            f"{where}: {key}: {value!r} -- this repo is NerdIT-Tech/.github; "
            "reference it with '$/' so the ref cannot drift from the running commit"
        )


def _self_reference_workflow_calls():
    """Yield `(caller, job, callee_path)` for every in-repo `uses: $/` call."""
    for caller in workflow_paths():
        doc = load_yaml(caller) or {}
        for job_name, job in (doc.get("jobs") or {}).items():
            uses = job.get("uses")
            if isinstance(uses, str) and uses.startswith("$/"):
                target = REPO_ROOT / uses[2:]
                if target.is_file():
                    yield relative(caller), job_name, target


SELF_CALLS = list(_self_reference_workflow_calls())


def test_repository_actually_has_self_calls():
    assert len(SELF_CALLS) >= 5, f"expected several in-repo callers, found {len(SELF_CALLS)}"


@pytest.mark.parametrize(
    "caller,job,callee",
    SELF_CALLS,
    ids=[f"{c}::{j}" for c, j, _ in SELF_CALLS],
)
class TestCallerGrantsCalleePermissions:
    """The caller's grant must cover every scope the callee's jobs request.

    GitHub downgrades the token at every step of a call chain, so a reusable
    workflow can never widen what the caller gave it. A missing scope is not
    a partial failure: the run aborts in `startup_failure` with zero jobs
    created, so the gate the caller invoked never executes.
    """

    def test_callee_permissions_are_covered(self, caller, job, callee):
        callee_doc = load_yaml(callee) or {}
        needed = set()
        for scopes in declared_permissions(callee_doc).values():
            needed |= scopes

        caller_doc = load_yaml(REPO_ROOT / caller) or {}
        granted = normalise_permissions((caller_doc.get("jobs") or {})[job].get("permissions"))

        missing = needed - granted
        assert not missing, (
            f"{caller}::{job} calls {relative(callee)} but does not grant {sorted(missing)}; "
            f"the callee needs {sorted(needed)}. A missing grant aborts the run in "
            "startup_failure before any job runs."
        )

    def test_caller_grants_nothing_extra(self, caller, job, callee):
        """A caller should grant what the callee needs, not more.

        The caller is the only place the token can be widened, so an unused
        grant is a grant that need not have been made.
        """
        callee_doc = load_yaml(callee) or {}
        needed = set()
        for scopes in declared_permissions(callee_doc).values():
            needed |= scopes

        caller_doc = load_yaml(REPO_ROOT / caller) or {}
        granted = normalise_permissions((caller_doc.get("jobs") or {})[job].get("permissions"))

        excess = granted - needed
        assert not excess, (
            f"{caller}::{job} grants {sorted(excess)} to {relative(callee)} but no "
            f"job there requests it; the callee needs {sorted(needed)}"
        )


README_TABLE = re.compile(r"^\|\s*`(?P<name>[\w.-]+)`\s*\|\s*(?P<perms>.+?)\s*\|$")


def _documented_caller_grants():
    """Parse the 'Caller must grant' table out of the workflows README."""
    readme = REPO_ROOT / ".github" / "workflows" / "README.md"
    rows = {}
    for line in readme.read_text(encoding="utf-8").splitlines():
        match = README_TABLE.match(line.strip())
        if not match:
            continue
        scopes = set(re.findall(r"`?([a-z-]+):\s*(?:read|write)`?", match.group("perms")))
        if scopes:
            rows[match.group("name")] = scopes
    return rows


DOCUMENTED = _documented_caller_grants()


def test_readme_documents_some_callers():
    assert DOCUMENTED, "the caller-permissions table in the README could not be parsed"


@pytest.mark.parametrize("name,scopes", sorted(DOCUMENTED.items()))
def test_documented_caller_grants_match_the_workflow(name, scopes):
    """The README's table is the published contract; keep it honest.

    A table row that has drifted from the workflow is worse than no table,
    because a caller reads it and grants the wrong thing.
    """
    path = REPO_ROOT / ".github" / "workflows" / name
    assert path.is_file(), f"README documents {name}, which does not exist"

    doc = load_yaml(path) or {}
    declared = set()
    for job_scopes in declared_permissions(doc).values():
        declared |= job_scopes

    undocumented = declared - scopes
    assert not undocumented, (
        f"workflows/README.md lists {sorted(scopes)} for {name}, but the workflow "
        f"also needs {sorted(undocumented)}"
    )


def test_every_reusable_needing_a_grant_is_documented():
    """Conversely: a reusable that needs caller permissions must say so."""
    for path in reusable_workflows():
        doc = load_yaml(path) or {}
        declared = set()
        for job_scopes in declared_permissions(doc).values():
            declared |= job_scopes
        if not declared:
            continue
        assert path.name in DOCUMENTED, (
            f"{relative(path)} needs caller permissions {sorted(declared)} but is "
            "absent from the 'Caller must grant' table in workflows/README.md"
        )
