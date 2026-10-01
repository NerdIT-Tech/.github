# Reusable workflows

Reusable GitHub Actions workflows (`on: workflow_call`) shared across
NerdIT-Tech repos, e.g. [`reusable-semantic-pr-title.yml`](reusable-semantic-pr-title/reusable-semantic-pr-title.yml),
[`reusable-yaml-lint.yml`](reusable-yaml-lint/reusable-yaml-lint.yml), and
[`reusable-actionlint.yml`](reusable-actionlint/reusable-actionlint.yml).

## Conventions

- **Naming**: `reusable-<purpose>/reusable-<purpose>.yml`, e.g. `reusable-build-go/reusable-build-go.yml`. The directory is load-bearing, not cosmetic — see **Versioning**.
- **Trigger**: use `on: workflow_call`, with typed `inputs`/`secrets` blocks — don't rely on repo-level context that callers might not have.
- **Versioning**: release-please publishes one tag stream per component, named `<component>/v<major>`, and callers pin to that floating tag rather than `main`, so changes here don't silently break every repo at once. Callers never pin to a repo-level `v1`: no such tag exists, so `uses: .../reusable-build-go/reusable-build-go.yml@v1` fails to resolve. Pin to the component's own tag instead, e.g. `reusable-build-go/reusable-build-go.yml@reusable-build-go/v1`.

  Each workflow lives in its own directory because that is the only shape
  release-please can attribute commits to. Its `CommitSplit` matches a package
  path with `file.indexOf(packagePath + "/") === 0`, so a package path naming a
  *file* matches nothing, ever — the component silently collects no commits and
  is never released. That is why the 16 workflow components that predated this
  layout shipped with no `CHANGELOG.md`: release-please never produced a single
  one of their releases.
- **Referencing from another repo**:

  ```yaml
  jobs:
    build:
      uses: NerdIT-Tech/.github/.github/workflows/reusable-build-go/reusable-build-go.yml@reusable-build-go/v1
      with:
        go-version: "1.22"
  ```

  All 20 workflow components released as `1.0.0` when they moved into
  directories, so their floating tag is `v1`. That is a breaking major bump on
  a component that was previously on `0.x`, and the old floating tags
  (`reusable-build-go/v0` and friends) are frozen at their last pre-move commit
  rather than re-pointed — so a caller still pinned to `@reusable-build-go/v0`
  keeps resolving against the old flat path and is unaffected by this migration.
  Move to the nested path and `@v1` when convenient. Check
  `git tag --list '<component>/v*'` before pinning, and note that
  release-please does not create a floating tag for a component until its
  first release.
- **Permissions**: set `permissions: {}` at the workflow level, then grant the
  specific permissions each job needs. GitHub downgrades a caller's token at
  every step of a call chain, so a reusable workflow can't grant itself
  permissions the caller didn't provide. A missing grant fails inside the called
  workflow, not at the call site, so grant exactly what the table below lists.

  The caller is the only place that can widen the token, so keep the grant
  narrow and annotated:

  ```yaml
  jobs:
    codeql:
      uses: NerdIT-Tech/.github/.github/workflows/reusable-codeql/reusable-codeql.yml@reusable-codeql/v1
      permissions:
        actions: read         # CodeQL workflow metadata (private repo)
        contents: read        # checkout
        security-events: write  # SARIF upload
  ```

  The reusable workflows that need a caller grant are:

  | Reusable workflow | Caller must grant |
  |---|---|
  | `reusable-actionlint/reusable-actionlint.yml` | `contents: read` |
  | `reusable-build-go/reusable-build-go.yml` | `contents: read` |
  | `reusable-check-go-deps/reusable-check-go-deps.yml` | `contents: read` |
  | `reusable-check-license/reusable-check-license.yml` | `contents: read` |
  | `reusable-check-snippets/reusable-check-snippets.yml` | `contents: read` |
  | `reusable-codeql/reusable-codeql.yml` | `contents: read`, `actions: read`, `security-events: write` |
  | `reusable-docs-build/reusable-docs-build.yml` | `contents: read` |
  | `reusable-docs-gate/reusable-docs-gate.yml` | `contents: read` |
  | `reusable-e2e-go/reusable-e2e-go.yml` | `contents: read` |
  | `reusable-govulncheck/reusable-govulncheck.yml` | `contents: read` |
  | `reusable-lint-go/reusable-lint-go.yml` | `contents: read` |
  | `reusable-scorecard/reusable-scorecard.yml` | `contents: read`, `security-events: write`, `id-token: write` |
  | `reusable-semantic-pr-title/reusable-semantic-pr-title.yml` | `contents: read`, `pull-requests: write` |
  | `reusable-stale-issues/reusable-stale-issues.yml` | `issues: write` |
  | `reusable-sync-issue-labels/reusable-sync-issue-labels.yml` | `issues: write` |
  | `reusable-test-go/reusable-test-go.yml` | `contents: read`, `pull-requests: write` |
  | `reusable-vale-lint/reusable-vale-lint.yml` | `contents: read` |
  | `reusable-workflow-tests/reusable-workflow-tests.yml` | `contents: read` |
  | `reusable-yaml-lint/reusable-yaml-lint.yml` | `contents: read` |
  | `reusable-zizmor/reusable-zizmor.yml` | `contents: read`; plus `security-events: write`, `actions: read` when `advanced-security: true` |

  This table is enforced, not aspirational: `test_references.py` parses it
  and fails if a workflow requests a scope the table omits, or if the table
  names a workflow that no longer needs a grant. Regenerate a row from the
  job's own `permissions:` rather than hand-editing.

See [`../actions/README.md`](../actions/README.md) for composite (reusable) actions.

## Tests

`.github/tests/` holds the contract tests for every reusable workflow and
composite action in this repo. They parse the YAML rather than grepping it
and cover the conventions above: the `$/` reference rules, hash pinning,
least-privilege permissions, composite `shell:` requirements, the
caller-grants-callee contract, and this table.

```sh
pip install pytest pyyaml
python -m pytest .github/tests
```

They run in CI via [`workflow-tests.yml`](workflow-tests.yml), which calls
[`reusable-workflow-tests.yml`](reusable-workflow-tests/reusable-workflow-tests.yml).
