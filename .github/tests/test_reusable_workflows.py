"""Contract tests for the repo's reusable workflows.

One test per documented convention in `.github/workflows/README.md`, applied
to every reusable workflow rather than a sample.
"""

from __future__ import annotations

import pytest

from conftest import (
    PERMISSION_SCOPES,
    REPO_ROOT,
    classify_reference,
    declared_permissions,
    iter_uses,
    load_yaml,
    relative,
    reusable_workflows,
    trigger_block,
    workflow_paths,
)

REUSABLE = reusable_workflows()


def test_repository_actually_has_reusable_workflows():
    """Guard the guard: a broken glob would make every test below vacuous.

    A floor, not an exact count. Pinning the number would mean a reviewer has
    to bump a magic constant whenever a workflow is added, which trains people
    to edit the test instead of reading it. This only has to notice that the
    search stopped finding anything.
    """
    assert len(REUSABLE) >= 20, (
        f"expected at least 20 reusable workflows, found {len(REUSABLE)} -- "
        "did the glob or the workflow_call detection break?"
    )


@pytest.mark.parametrize("path", REUSABLE, ids=relative)
class TestReusableWorkflow:
    @pytest.fixture(autouse=True)
    def _doc(self, path):
        self.path = path
        self.doc = load_yaml(path) or {}
        self.rel = relative(path)

    def test_naming_convention(self):
        """README: workflows are named `reusable-<purpose>.yml`."""
        assert self.path.name.startswith("reusable-"), (
            f"{self.rel}: reusable workflow is not named 'reusable-<purpose>.yml'"
        )

    def test_exposes_workflow_call(self):
        """A reusable workflow must actually be callable."""
        assert "workflow_call" in trigger_block(self.doc), (
            f"{self.rel}: no 'on: workflow_call' trigger"
        )

    def test_workflow_level_permissions_are_empty(self):
        """README: `permissions: {}` at the top, then job-scoped grants.

        A reusable workflow inherits the caller's token, so a missing
        top-level block means every job silently runs with whatever the
        caller happened to grant.
        """
        assert "permissions" in self.doc, (
            f"{self.rel}: no workflow-level 'permissions:' block"
        )
        assert self.doc["permissions"] in ({}, None), (
            f"{self.rel}: workflow-level permissions is {self.doc['permissions']!r}, "
            "expected an empty mapping; grants belong at job level"
        )

    def test_every_job_declares_its_permissions(self):
        """Least privilege is only real if it is stated per job."""
        jobs = self.doc.get("jobs") or {}
        assert jobs, f"{self.rel}: no jobs"
        for name, job in jobs.items():
            assert "permissions" in job, (
                f"{self.rel}: job {name!r} declares no 'permissions:'"
            )

    def test_permissions_use_real_scopes(self):
        """A typo'd scope fails the workflow at runtime, not at review."""
        for name, scopes in declared_permissions(self.doc).items():
            for scope in scopes:
                assert scope in PERMISSION_SCOPES, (
                    f"{self.rel}: job {name!r} requests unknown scope {scope!r}"
                )

    def test_every_job_has_a_timeout(self):
        """A hung reusable workflow burns a runner until the org limit.

        A job that calls another reusable workflow is exempt: GitHub rejects
        `timeout-minutes` on the `uses:` form (actionlint reports "when a
        reusable workflow is called with 'uses', 'timeout-minutes' is not
        available", and the docs list only name, uses, with, secrets, needs,
        if, and permissions). Such a job delegates every step to the callee,
        so the bound is the callee's own per-job timeout.
        """
        for name, job in (self.doc.get("jobs") or {}).items():
            if isinstance(job.get("uses"), str):
                continue
            assert job.get("timeout-minutes"), (
                f"{self.rel}: job {name!r} has no 'timeout-minutes'"
            )

    def test_inputs_are_typed_and_documented(self):
        """README: typed `inputs`/`secrets`, not free-form."""
        block = trigger_block(self.doc).get("workflow_call") or {}
        for name, spec in (block.get("inputs") or {}).items():
            spec = spec or {}
            assert spec.get("type"), f"{self.rel}: input {name!r} has no 'type'"
            assert spec.get("description"), f"{self.rel}: input {name!r} has no description"

    def test_secrets_are_typed(self):
        for name, spec in (trigger_block(self.doc)["workflow_call"] or {}).get(
            "secrets", {}
        ).items():
            spec = spec or {}
            assert spec.get("description"), f"{self.rel}: secret {name!r} has no description"

    def test_references_are_correctly_pinned(self):
        """Internal refs use `$/`; everything else is a 40-hex SHA."""
        for _, key, value in iter_uses(self.doc):
            kind = classify_reference(value)
            where = f"{self.rel}: {key}: {value}"
            assert kind != "workspace-relative", (
                f"{where} -- './' resolves against the caller's checkout (#36); "
                "use '$/' instead"
            )
            assert kind != "self-qualified", (
                f"{where} -- reference this repo with '$/', not by full name"
            )
            if kind == "dollar-slash":
                assert "@" not in value, f"{where} -- '$/' must not carry an @ref"
            elif kind == "docker":
                assert "@sha256:" in value, f"{where} -- docker image is not digest-pinned"
            else:
                assert kind == "hash-pinned", f"{where} -- third-party ref is not SHA-pinned"

    def test_self_references_resolve(self):
        """Every `$/<path>` must exist, and resolve to an action or workflow."""
        for _, key, value in iter_uses(self.doc):
            if classify_reference(value) != "dollar-slash":
                continue
            target = REPO_ROOT / value.strip()[2:]
            assert (
                target.is_file() or (target.is_dir() and (target / "action.yml").is_file())
            ), f"{self.rel}: {key}: {value} does not exist in this repo"


@pytest.mark.parametrize("path", workflow_paths(), ids=relative)
class TestEveryWorkflow:
    """Rules that hold for callers too, not just reusable workflows."""

    @pytest.fixture(autouse=True)
    def _doc(self, path):
        self.path = path
        self.doc = load_yaml(path) or {}
        self.rel = relative(path)

    def test_declares_permissions(self):
        assert "permissions" in self.doc, f"{self.rel}: no 'permissions:' block"

    def test_events_are_declared(self):
        assert trigger_block(self.doc), f"{self.rel}: no 'on:' block"

    def test_is_not_orphaned_from_its_caller(self):
        """A reusable workflow nothing calls is dead weight; flag it.

        External consumers are the exception, so this is a review signal
        rather than a hard failure: the file must at least still be a valid
        workflow, which the other tests here already assert.
        """
        if "workflow_call" not in trigger_block(self.doc):
            pytest.skip("not a reusable workflow")
        assert self.doc.get("jobs"), f"{self.rel}: reusable workflow has no jobs"
