"""Contract tests for the repo's composite (reusable) actions.

One test per documented convention in `.github/actions/README.md`, applied
to every action rather than a sample, so adding an action cannot skip the
rules.
"""

from __future__ import annotations

import pytest

from conftest import (
    REPO_ROOT,
    classify_reference,
    composite_actions,
    iter_uses,
    load_yaml,
    relative,
    trigger_block,
)

ACTIONS = composite_actions()


def test_repository_actually_has_actions():
    """Guard the guard: a broken glob would make every test below vacuous.

    A floor, not an exact count -- see the note in test_reusable_workflows.py.
    """
    assert len(ACTIONS) >= 20, (
        f"expected at least 20 composite actions, found {len(ACTIONS)} -- "
        "did the glob break?"
    )


@pytest.mark.parametrize("path", ACTIONS, ids=relative)
class TestCompositeAction:
    @pytest.fixture(autouse=True)
    def _doc(self, path):
        self.path = path
        self.doc = load_yaml(path) or {}
        self.rel = relative(path)

    def test_has_name_and_description(self):
        """Actions are listed in a catalogue; a missing description hides them."""
        assert self.doc.get("name"), f"{self.rel}: missing 'name'"
        assert self.doc.get("description"), f"{self.rel}: missing 'description'"

    def test_uses_composite_runtime(self):
        """Every action here is a composite action, per the README layout rule."""
        runs = self.doc.get("runs") or {}
        assert runs.get("using") == "composite", (
            f"{self.rel}: runs.using is {runs.get('using')!r}, expected 'composite'"
        )

    def test_every_input_is_documented(self):
        """An undocumented input is unusable by a caller reading only the action."""
        for name, spec in (self.doc.get("inputs") or {}).items():
            spec = spec or {}
            assert spec.get("description"), (
                f"{self.rel}: input {name!r} has no description"
            )
            assert "required" in spec, (
                f"{self.rel}: input {name!r} does not declare 'required'"
            )

    def test_run_steps_declare_a_shell(self):
        """GitHub rejects a composite `run:` step with no `shell:`.

        This is the single most common composite-action bug, and the failure
        only appears at run time on the caller's runner.
        """
        for index, step in enumerate((self.doc["runs"] or {}).get("steps") or []):
            if "run" in step:
                assert step.get("shell"), (
                    f"{self.rel}: steps[{index}] runs a script with no 'shell:'"
                )

    def test_every_step_is_usable(self):
        """A composite step must do something; a bare `-` is a silent no-op."""
        for index, step in enumerate((self.doc["runs"] or {}).get("steps") or []):
            assert step.get("uses") or step.get("run"), (
                f"{self.rel}: steps[{index}] has neither 'uses' nor 'run'"
            )
            if step.get("run"):
                assert str(step["run"]).strip(), (
                    f"{self.rel}: steps[{index}] has an empty 'run:'"
                )

    def test_references_are_correctly_pinned(self):
        """Internal refs use `$/`; everything else is a 40-hex SHA.

        `./` resolves against the caller's checkout, not this repo, so it is
        wrong inside a composite action (issue #36). A fully-qualified
        NerdIT-Tech ref is version-consistent only by luck.
        """
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
                assert "@" not in value, (
                    f"{where} -- '$/' must not carry an @ref"
                )
            elif kind == "docker":
                assert "@sha256:" in value, f"{where} -- docker image is not digest-pinned"
            else:
                assert kind == "hash-pinned", f"{where} -- third-party ref is not SHA-pinned"

    def test_self_references_resolve(self):
        """Every `$/<path>` this action uses must exist in the repo."""
        for _, key, value in iter_uses(self.doc):
            if not classify_reference(value) == "dollar-slash":
                continue
            target = REPO_ROOT / value.strip()[2:]
            exists = target.is_dir() and (target / "action.yml").is_file()
            assert exists, f"{self.rel}: {key}: {value} does not exist in this repo"


def test_no_action_uses_its_own_trigger_block():
    """`on:` is meaningless in an action; catch a copy-pasted workflow."""
    for path in ACTIONS:
        assert not trigger_block(load_yaml(path) or {}), (
            f"{relative(path)}: an action.yml must not declare an 'on:' block"
        )
