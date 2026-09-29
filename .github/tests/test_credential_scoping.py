"""Contract tests for credential scoping in reusable workflows.

AUDIT.md rec #2 found a job-scope `env:` map in `reusable-e2e-go.yml`, which
put three production credentials in the environment of every step in the
job -- including the step that compiled and ran code from the checked-out
tree. Fixing that instance is one edit; keeping it fixed is these tests.

A passing suite proves nothing on its own, so each rule here was
mutation-tested: inject the defect it exists to catch, confirm a named test
goes red, revert. A rule that no mutation turned red was not worth writing.
"""

from __future__ import annotations

import re

import pytest

from conftest import (
    load_yaml,
    relative,
    reusable_workflows,
    trigger_block,
)

#: A value that reads a secret. The `secrets` context is the only place a
#: credential enters a workflow, so this is the whole of the attack surface
#: for "which steps hold a credential".
SECRET_REF = re.compile(r"secrets\.")


def steps_of(job: dict) -> list[dict]:
    return [s for s in (job.get("steps") or []) if isinstance(s, dict)]


def step_name(step: dict, index: int) -> str:
    return str(step.get("name") or step.get("uses") or f"#{index}")


def env_holding_a_secret(container: dict) -> dict[str, str]:
    """The entries in an `env:` map whose value reads the secrets context."""
    env = container.get("env") or {}
    if not isinstance(env, dict):
        return {}
    return {k: str(v) for k, v in env.items() if SECRET_REF.search(str(v))}


def secret_bearing_steps(job: dict) -> list[tuple[int, dict]]:
    return [(i, s) for i, s in enumerate(steps_of(job)) if env_holding_a_secret(s)]


def declared_secrets(doc: dict) -> list[str]:
    block = trigger_block(doc).get("workflow_call") or {}
    return list((block.get("secrets") or {}))


#: Commands and actions that run code from the tree or from the network on
#: its behalf. `go test` is deliberately absent: a test step is a legitimate
#: consumer of a credential, which is the whole point of the harness. What
#: must never happen is a credential present while the *toolchain* is set up
#: or the code is compiled, because those steps run third-party code and
#: need no credential to do it.
DEPENDENCY_CODE = re.compile(r"\bgo (build|mod download|generate)\b")


def is_dependency_code_step(step: dict) -> bool:
    uses = str(step.get("uses") or "")
    return (
        "checkout" in uses
        or "setup-go" in uses
        or bool(DEPENDENCY_CODE.search(str(step.get("run") or "")))
    )


@pytest.mark.parametrize("path", reusable_workflows(), ids=relative)
class TestSecretsAreStepScoped:
    """No job-scope or workflow-scope `env:` map may hold a secret."""

    @pytest.fixture(autouse=True)
    def _doc(self, path):
        self.path = path
        self.doc = load_yaml(path) or {}
        self.rel = relative(path)
        self.credentialed = bool(declared_secrets(self.doc))

    def test_workflow_level_env_holds_no_secret(self):
        """A top-level `env:` map is in scope for every job in the run."""
        leaked = env_holding_a_secret(self.doc)
        assert not leaked, (
            f"{self.rel}: workflow-level env holds {sorted(leaked)}; a top-level "
            "env map is inherited by every job in the run"
        )

    def test_no_job_scope_env_holds_a_secret(self):
        """The rec #2 defect, as a rule.

        A job-level `env:` map applies to every step in the job, so a
        credential placed there is inherited by checkout, module fetch,
        build, and every `run:` script -- none of which need it.
        """
        for name, job in (self.doc.get("jobs") or {}).items():
            leaked = env_holding_a_secret(job)
            assert not leaked, (
                f"{self.rel}: job {name!r} sets {sorted(leaked)} at job scope, so "
                "every step in the job inherits the credential. Move it to the "
                "env: block of the single step that needs it."
            )

    def test_no_secret_is_interpolated_into_a_run_block(self):
        """Pass secrets through a step `env:`, never inside the script.

        Actions expands `${{ }}` before the runner writes the script to disk,
        so an inline secret is written to a file in plaintext, appears in the
        step's command log, and is a template-injection sink.
        """
        for job_name, job in (self.doc.get("jobs") or {}).items():
            for i, step in enumerate(steps_of(job)):
                script = step.get("run")
                if not isinstance(script, str):
                    continue
                for expr in re.findall(r"\$\{\{[^}]*\}\}", script):
                    assert not SECRET_REF.search(expr), (
                        f"{self.rel}: job {job_name!r} step "
                        f"{step_name(step, i)!r} interpolates {expr!r} into a "
                        "run: block; pass it through the step's env: instead"
                    )

    def test_credential_is_injected_after_checkout_and_build(self, ):
        """Ordering is the security property, so assert the ordering.

        Checkout, module fetch, and compile all run third-party code --
        module downloads, `go generate` directives, cgo toolchain
        invocations -- that has no reason to hold a live credential. The
        first step that introduces one must therefore come after every step
        that sets the toolchain up or compiles the tree.
        """
        for job_name, job in (self.doc.get("jobs") or {}).items():
            steps = steps_of(job)
            secret_indexes = [i for i, _ in secret_bearing_steps(job)]
            if not secret_indexes:
                continue
            first_secret = min(secret_indexes)
            late = [
                (i, step)
                for i, step in enumerate(steps)
                if i > first_secret and is_dependency_code_step(step)
            ]
            assert not late, (
                f"{self.rel}: job {job_name!r} runs "
                f"{[step_name(s, i) for i, s in late]} after the first "
                f"credential-bearing step "
                f"({step_name(steps[first_secret], first_secret)!r}); a step that "
                "checks out or compiles runs third-party code, and it must do so "
                "before any credential is in scope"
            )


@pytest.mark.parametrize("path", reusable_workflows(), ids=relative)
class TestTrustGuard:
    """A reusable workflow cannot choose its own trigger, so it must police it.

    These apply to any workflow that declares a `guard` job, so the
    convention survives being extended to a second credentialed harness.
    """

    @pytest.fixture(autouse=True)
    def _doc(self, path):
        self.path = path
        self.doc = load_yaml(path) or {}
        self.rel = relative(path)
        self.guard = (self.doc.get("jobs") or {}).get("guard")
        if not self.guard:
            pytest.skip("workflow has no 'guard' job")

    def test_guard_allowlists_only_trusted_events(self):
        """The allowlist is the primary control, so pin what it permits.

        `pull_request` is the event that must never be here: it runs the
        workflow from the pull request's merge commit, so the branch author
        controls both the YAML and the code that would receive the secret.
        """
        script = "\n".join(
            str(s.get("run") or "") for s in steps_of(self.guard) if s.get("run")
        )
        match = re.search(r"case\s+\"\$EVENT_NAME\"\s+in\s*(.*?)(?:esac|\Z)", script, re.S)
        assert match, (
            f"{self.rel}: the guard job does not switch on github.event_name, so "
            "it is not enforcing anything"
        )
        arms = [
            m.group(1)
            for m in (
                re.fullmatch(r"\s*([\w_|-]+)\)\s*", arm)
                for arm in match.group(1).splitlines()
            )
            if m
        ]
        allowed = {event for arm in arms for event in arm.split("|")}
        assert allowed == {"schedule", "workflow_dispatch"}, (
            f"{self.rel}: guard allows {sorted(allowed)}; expected exactly "
            "schedule and workflow_dispatch"
        )

    def test_guard_fails_loudly_rather_than_skipping(self):
        """A skipped job looks identical to a passing one in a required check.

        That is the same defect class as the credential leak: a control that
        cannot be seen to have fired is not a control. So the guard must have
        no `if:` of its own, and its script must exit non-zero and emit an
        annotation naming the offending event.
        """
        assert "if" not in self.guard, (
            f"{self.rel}: the guard job has an 'if:'; a job-level if would skip "
            "it, and a skipped job is indistinguishable from a passing one"
        )
        script = "\n".join(
            str(s.get("run") or "") for s in steps_of(self.guard) if s.get("run")
        )
        assert "::error::" in script, (
            f"{self.rel}: the guard emits no ::error:: annotation, so a caller "
            "sees only a red job with no reason"
        )
        assert re.search(r"^\s*exit 1\s*$", script, re.M), (
            f"{self.rel}: the guard script never calls 'exit 1'"
        )
        assert "${EVENT_NAME}" in script, (
            f"{self.rel}: the guard's error message does not name the offending "
            "event, so the caller cannot tell which trigger to change"
        )

    def test_guard_exposes_its_verdict_as_an_output(self):
        outputs = self.guard.get("outputs") or {}
        assert "allowed" in outputs, (
            f"{self.rel}: the guard declares no 'allowed' output, so downstream "
            "jobs cannot re-check the verdict"
        )

    def test_dependent_jobs_need_the_guard_and_recheck_it(self):
        """`needs:` alone orders the jobs; it does not gate them.

        Both halves are required. If the guard is ever relaxed into a skip,
        the `if:` re-check is what still holds the line.
        """
        checked = 0
        for name, job in (self.doc.get("jobs") or {}).items():
            if name == "guard":
                continue
            needs = job.get("needs")
            needs = [needs] if isinstance(needs, str) else list(needs or [])
            if "guard" not in needs:
                continue
            checked += 1
            condition = str(job.get("if") or "")
            assert "needs.guard.outputs.allowed" in condition, (
                f"{self.rel}: job {name!r} needs the guard but does not re-check "
                f"needs.guard.outputs.allowed; its 'if:' is {condition!r}"
            )
        assert checked, f"{self.rel}: no job depends on the guard"


@pytest.mark.parametrize("path", reusable_workflows(), ids=relative)
class TestCredentialGate:
    """Missing credentials must fail the job, not produce a confusing red test.

    `check-secret` only emits `::warning::` and always exits 0, so on its own
    it detects nothing. Something downstream has to convert the boolean into
    a hard failure.
    """

    @pytest.fixture(autouse=True)
    def _doc(self, path):
        self.path = path
        self.doc = load_yaml(path) or {}
        self.rel = relative(path)
        # Scoped to workflows that hand a *declared* secret to a script. A
        # secret passed to a third-party action's `with:` is that action's
        # business (reusable-test-go does it for Codecov), and GITHUB_TOKEN is
        # always present, so gating on either would be ceremony. A declared
        # secret in the env of a `run:` step is a credential the workflow's
        # own code executes against, and its absence has to be detected here
        # rather than surfacing as an unexplained suite failure.
        declared = set(declared_secrets(self.doc))
        self.run_step_secrets = [
            (job_name, i, step)
            for job_name, job in (self.doc.get("jobs") or {}).items()
            for i, step in enumerate(steps_of(job))
            if step.get("run") and env_holding_a_secret(step)
            and declared & set(env_holding_a_secret(step))
        ]
        if not self.run_step_secrets:
            pytest.skip("workflow hands no secret to a run: step")
        self.probes = [
            s
            for job in (self.doc.get("jobs") or {}).values()
            for s in steps_of(job)
            if "check-secret" in str(s.get("uses") or "")
        ]

    def test_a_secret_handed_to_a_script_is_gated(self):
        """Fail closed on a missing credential.

        Without the probe, a caller who has not defined `BDD_INSTANCE` gets a
        suite that authenticates as nobody and a failure that points at the
        test rather than at the missing secret.
        """
        assert self.probes, (
            f"{self.rel}: hands a secret to a run: step but never calls "
            "check-secret, so a missing credential surfaces as an opaque suite "
            "failure instead of a named error"
        )

    def test_every_secret_the_harness_reads_is_probed(self):
        """A secret that is injected but never probed is an ungated path."""
        names: set[str] = set()
        for step in self.probes:
            for listed in str(step.get("with", {}).get("secret-names", "")).split(","):
                if listed.strip():
                    names.add(listed.strip())
        for name in declared_secrets(self.doc):
            assert name in names, (
                f"{self.rel}: declares secret {name!r} but no check-secret step "
                f"lists it; it can therefore go missing undetected"
            )
        assert names, f"{self.rel}: a check-secret step lists no secret names"

    def test_probe_outputs_are_turned_into_a_hard_failure(self):
        """`check-secret` always exits 0. A downstream step must not.

        Detected by the step that *consumes* the probe output -- the
        `env:` entry carrying `outputs.has-secrets` -- rather than by the
        probe itself, so a workflow cannot pass by merely calling the action.
        """
        gates = [
            (job_name, i, step)
            for job_name, job in (self.doc.get("jobs") or {}).items()
            for i, step in enumerate(steps_of(job))
            if "outputs.has-secrets" in str((step.get("env") or {}))
        ]
        assert gates, (
            f"{self.rel}: no step consumes a check-secret 'has-secrets' output, so "
            "a missing credential is only a ::warning:: and the suite fails later, "
            "somewhere less useful"
        )
        for job_name, i, step in gates:
            script = str(step.get("run") or "")
            assert re.search(r"^\s*exit 1\s*$", script, re.M), (
                f"{self.rel}: job {job_name!r} step {step_name(step, i)!r} reads "
                "'has-secrets' but never calls 'exit 1', so the boolean has no effect"
            )
            assert "::error::" in script, (
                f"{self.rel}: job {job_name!r} step {step_name(step, i)!r} emits no "
                "::error::, so the caller is not told which secret to define"
            )

    def test_gate_follows_the_probes_it_converts(self):
        """The gate has to come after the probes, or it reads nothing.

        Step order is the property, so it gets asserted rather than trusted.
        """
        for job_name, job in (self.doc.get("jobs") or {}).items():
            steps = steps_of(job)
            probes = {
                i for i, s in enumerate(steps) if "check-secret" in str(s.get("uses") or "")
            }
            gates = {
                i
                for i, s in enumerate(steps)
                if "outputs.has-secrets" in str(s.get("env") or {})
            }
            if not probes or not gates:
                continue
            assert min(gates) > max(probes), (
                f"{self.rel}: job {job_name!r} reads the probe outputs at index "
                f"{sorted(gates)}, which is not after the probes at {sorted(probes)}; "
                "the gate would read an unset output and pass unconditionally"
            )
