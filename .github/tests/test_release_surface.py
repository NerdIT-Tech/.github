"""Contract tests for the repo's release surface.

`.github/workflows/README.md` tells consumers to pin a tag rather than `main`,
and gives `@v1` as the example. That only works if release-please has actually
created a floating major tag for the thing being called, and it only creates
one for paths listed in `packages` in `.release-please-config.json`.

The two failure modes covered here are both invisible in review. An
unregistered path means the first release PR for it never opens, so the tag
the README tells consumers to pin is never pushed -- and a consumer who
follows the documentation gets a resolution failure on a workflow that exists
in the repo. A missing floating tag means the exact-version tags are there but
`@v1` is not, which is what makes a tag move in `release-please.yml` necessary
rather than optional.

`.release-please-manifest.json` is written by release-please, not by hand, so
it only ever names what has actually been released. The config is the file that
declares what is releasable; these tests read both and never edit either.
"""

from __future__ import annotations

import subprocess

import pytest

from conftest import (
    REPO_ROOT,
    WORKFLOWS_DIR,
    composite_actions,
    load_yaml,
    relative,
)

CONFIG_FILE = ".release-please-config.json"
MANIFEST_FILE = ".release-please-manifest.json"

#: JSON is valid YAML, so the shared parser covers both release-please files
#: and keeps this suite on the repo's parse-don't-grep rule.
PACKAGES = (load_yaml(REPO_ROOT / CONFIG_FILE) or {}).get("packages") or {}
MANIFEST = load_yaml(REPO_ROOT / MANIFEST_FILE) or {}


def releasable_units() -> list[tuple[str, str]]:
    """`(path, package_key)` for every unit that ships to consumers.

    The file is what the consumer calls; the key is what release-please is
    keyed on. For a workflow they are the same string. For a composite action
    they are not: release-please tracks `.github/actions/<name>`, the
    directory, while the consumer calls `<name>/action.yml` -- and the action
    directory is what carries the release notes, so keying on the file would
    make every action in this repo look unregistered.

    `reusable-*.yml` rather than a `workflow_call` check: the glob is what the
    publishing decision is keyed on, so a workflow that accidentally loses its
    trigger still fails here instead of silently keeping a stale entry.

    The key is the component *directory*, not the workflow file. release-please
    attributes commits with `file.indexOf(packagePath + "/") === 0`, so a
    package path naming a file can never match a commit and the component is
    never released -- which is why all 16 workflow components that predate this
    layout shipped without a CHANGELOG.md.
    """
    units = [
        (relative(path), relative(path.parent))
        for path in WORKFLOWS_DIR.rglob("reusable-*.yml")
    ]
    units += [(relative(path), relative(path.parent)) for path in composite_actions()]
    return sorted(units)


UNITS = releasable_units()


def component_of(package_key: str) -> str:
    """Derive the release-please component name from a package key.

    Both key shapes end in the component: an action directory is
    `.github/actions/<component>` and a workflow is
    `.github/workflows/<component>`. Neither is a file path -- see
    `releasable_units` for why that matters.
    """
    name = package_key.rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".yml") else name


#: Components allowed to be missing a floating major tag.
#:
#: Empty, and it should stay that way. `resolve-pr` held the only entry until
#: 2026-09-30, when it released at 1.0.0 before `release-please.yml` grew the
#: "Move floating major version tags" step and so never got a `v1` tag. A chore
#: commit since then produced no bump, so release-please had no release to run
#: the step for, and the tag was pushed by hand instead:
#: `git tag resolve-pr/v1 resolve-pr/v1.0.0 && git push origin resolve-pr/v1`.
#:
#: The next missing floating tag is a release bug, not a historical one. Add a
#: tag rather than an entry here.
FLOATING_TAG_EXEMPTIONS: frozenset[str] = frozenset()


def git(*args: str) -> str | None:
    """Run one git command in the repo, or return None if git cannot answer.

    None means "unknown", not "empty". The tests below treat that as
    unverifiable rather than as a failure.
    """
    try:
        done = subprocess.run(
            ("git", "-C", str(REPO_ROOT), *args),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout


def floating_tags() -> frozenset[str] | None:
    """Every `<component>/v<major>` tag visible in this clone.

    Returns None when the clone cannot be trusted to hold a complete tag list,
    so the caller can skip instead of reporting a phantom violation.
    """
    shallow = git("rev-parse", "--is-shallow-repository")
    if shallow is None:
        return None
    if shallow.strip() == "true":
        return None

    listing = git("tag", "-l")
    if listing is None:
        return None
    tags = frozenset(listing.split())
    if not tags:
        return None
    return tags


TAGS = floating_tags()


def manifest_components() -> list:
    """`(package_key, version, component, expected_tag)` per released unit."""
    rows = []
    for key, version in sorted(MANIFEST.items()):
        component = component_of(key)
        rows.append((key, version, component, f"{component}/v{version.split('.')[0]}"))
    return rows


COMPONENTS = manifest_components()


def test_repository_actually_has_releasable_units():
    """Guard the guard: a broken glob would make every test below vacuous."""
    assert len(UNITS) >= 40, (
        f"expected at least 40 releasable units, found {len(UNITS)} -- did the "
        "glob break?"
    )


@pytest.mark.parametrize("where,key", UNITS, ids=[w for w, _ in UNITS])
def test_every_releasable_unit_is_registered(where, key):
    """A unit absent from `packages` is never tagged, so `@v1` never exists.

    `.github/workflows/README.md` instructs consumers to call a reusable
    workflow as `NerdIT-Tech/.github/<path>@v1`. release-please only opens a
    release PR for a path listed in `packages`, so an unregistered path leaves
    the consumer pinning `<component>/v<major>` to a tag that does not exist --
    a hard resolution failure in the consumer's workflow, pointing at a file
    that is present in this repo.
    """
    component = component_of(key)
    assert key in PACKAGES, (
        f"{where} is not registered: no packages entry for {key}, so "
        f"release-please will never tag it, and a consumer following the "
        f"README's pin instruction for {component}/v<major> resolves to a tag "
        f"that does not exist. Add {key} with component {component!r}."
    )


def test_repository_actually_has_manifest_components():
    """Guard the guard for the manifest side of the same invariant."""
    assert len(COMPONENTS) >= 20, (
        f"expected at least 20 released components, found {len(COMPONENTS)} -- "
        f"did {MANIFEST_FILE} stop parsing?"
    )


@pytest.mark.parametrize(
    "key,version,component,expected_tag",
    COMPONENTS,
    ids=[c[2] for c in COMPONENTS],
)
class TestFloatingMajorTag:
    """Each released component must have a tag a consumer can pin to.

    `release-please.yml` moves `<component>/v<major>` onto the newest release
    after every release PR merges. That move is what keeps `@v1` resolving to
    something current, and it only runs for components in `paths_released` --
    so a missing floating tag means the pinned ref a consumer uses is either
    absent or, worse, pointing at an old commit that reads as up to date.

    Tradeoff: `git tag -l` is a local view, and this suite is run by
    `reusable-workflow-tests/reusable-workflow-tests.yml`. Its checkout sets
    `fetch-depth: 0` so CI sees the same tag list a developer does -- without
    that, a shallow clone carries no tag history and this gate would fail on
    every component at once, one false failure per component, which trains
    people to ignore it. The skip below is a backstop for a clone that still
    cannot answer, not the normal CI path.
    """

    @pytest.fixture(autouse=True)
    def _tags(self):
        if TAGS is None:
            pytest.skip(
                "the local clone does not carry a complete tag list (shallow "
                "checkout, no tags fetched, or no git), so a missing floating "
                "tag here would be an artefact of the clone rather than a real "
                "violation"
            )

    def test_floating_tag_exists(self, key, version, component, expected_tag):
        assert component not in FLOATING_TAG_EXEMPTIONS, (
            f"{component} is listed in FLOATING_TAG_EXEMPTIONS, so this test "
            f"would skip instead of checking that {expected_tag} exists"
        )
        assert expected_tag in TAGS, (
            f"{key} is released at {version} but there is no {expected_tag} "
            f"tag: a consumer pinning '{expected_tag}' as the README instructs "
            "gets a tag that does not exist. release-please.yml moves this "
            "tag on the next release that touches the component."
        )


@pytest.mark.parametrize(
    "component,tag,expected_major",
    [
        ("resolve-pr", "resolve-pr/v1.2.3", "1"),
        ("reusable-build-go", "reusable-build-go/v0.1.1", "0"),
    ],
)
def test_major_is_read_two_characters_past_the_component(component, tag, expected_major):
    """Lock the slice offset used to read a version out of a floating tag.

    The tag is `<component>/v<major>.<minor>.<patch>`, so the version starts at
    `len(component) + 2` -- two, not three, characters in, because `/v` is two
    characters and the `/` alone is not the boundary. Slicing three characters
    in drops the leading digit, so every tag reads as an empty major rather
    than `1` or `0`, and every component looks broken at once. That error is
    invisible in the happy path because the expected tag here is derived from
    the manifest instead of parsed back out of a tag; this test pins the
    arithmetic so a future tag-parsing test cannot reintroduce it.
    """
    version = tag[len(component) + 2 :]
    assert version.split(".")[0] == expected_major, (
        f"{tag}: reading the version from offset {len(component) + 2} gave "
        f"{version.split('.')[0]!r}, expected {expected_major!r}"
    )
