# Reusable workflows

Reusable GitHub Actions workflows (`on: workflow_call`) shared across
NerdIT-Tech repos, e.g. [`reusable-semantic-pr-title.yml`](reusable-semantic-pr-title.yml),
[`reusable-yaml-lint.yml`](reusable-yaml-lint.yml), and
[`reusable-actionlint.yml`](reusable-actionlint.yml).

## Conventions

- **Naming**: `reusable-<purpose>.yml`, e.g. `reusable-build-go.yml`, `reusable-lint-go.yml`, `reusable-test-go.yml`.
- **Trigger**: use `on: workflow_call`, with typed `inputs`/`secrets` blocks — don't rely on repo-level context that callers might not have.
- **Versioning**: release-please publishes one tag stream per component, named `<component>/v<major>`, and have callers pin to that floating tag rather than `main`, so changes here don't silently break every repo at once. Callers never pin to a repo-level `v1`: no such tag exists, so `uses: .../reusable-build-go.yml@v1` fails to resolve. Pin to the component's own tag instead, e.g. `reusable-build-go.yml@reusable-build-go/v0`.
- **Referencing from another repo**:

  ```yaml
  jobs:
    build:
      uses: NerdIT-Tech/.github/.github/workflows/reusable-build-go.yml@reusable-build-go/v0
      with:
        go-version: "1.22"
  ```

  Most components are still on `0.x`, so their floating tag is `v0` — `reusable-build-go`, for instance, is released as `reusable-build-go/v0` alongside `reusable-build-go/v0.1.1`. Only components that have reached `1.x` float on `v1`, e.g. `terraform-plan.yml@terraform-plan/v1`. Check `git tag --list '<component>/v*'` before pinning, and note that release-please does not create a floating tag for a component until its first release.
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
      uses: NerdIT-Tech/.github/.github/workflows/reusable-codeql.yml@reusable-codeql/v0
      permissions:
        actions: read         # CodeQL workflow metadata (private repo)
        contents: read        # checkout
        security-events: write  # SARIF upload
  ```

  The reusable workflows that need a caller grant are:

  | Reusable workflow | Caller must grant |
  |---|---|
  | `reusable-actionlint.yml` | `contents: read` |
  | `reusable-build-go.yml` | `contents: read` |
  | `reusable-check-go-deps.yml` | `contents: read` |
  | `reusable-check-license.yml` | `contents: read` |
  | `reusable-check-snippets.yml` | `contents: read` |
  | `reusable-codeql.yml` | `contents: read`, `actions: read`, `security-events: write` |
  | `reusable-docs-build.yml` | `contents: read` |
  | `reusable-docs-gate.yml` | `contents: read` |
  | `reusable-e2e-go.yml` | `contents: read` |
  | `reusable-govulncheck.yml` | `contents: read` |
  | `reusable-lint-go.yml` | `contents: read` |
  | `reusable-scorecard.yml` | `contents: read`, `security-events: write`, `id-token: write` |
  | `reusable-semantic-pr-title.yml` | `contents: read`, `pull-requests: write` |
  | `reusable-stale-issues.yml` | `issues: write` |
  | `reusable-sync-issue-labels.yml` | `issues: write` |
  | `reusable-test-go.yml` | `contents: read`, `pull-requests: write` |
  | `reusable-vale-lint.yml` | `contents: read` |
  | `reusable-workflow-tests.yml` | `contents: read` |
  | `reusable-yaml-lint.yml` | `contents: read` |
  | `reusable-zizmor.yml` | `contents: read`; plus `security-events: write`, `actions: read` when `advanced-security: true` |

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
[`reusable-workflow-tests.yml`](reusable-workflow-tests.yml).
