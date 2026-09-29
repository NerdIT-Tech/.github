# Reusable workflows

Reusable GitHub Actions workflows (`on: workflow_call`) shared across
NerdIT-Tech repos, e.g. [`reusable-semantic-pr-title.yml`](reusable-semantic-pr-title.yml),
[`reusable-yaml-lint.yml`](reusable-yaml-lint.yml), and
[`reusable-actionlint.yml`](reusable-actionlint.yml).

## Conventions

- **Naming**: `reusable-<purpose>.yml`, e.g. `reusable-go-ci.yml`, `reusable-release.yml`.
- **Trigger**: use `on: workflow_call`, with typed `inputs`/`secrets` blocks — don't rely on repo-level context that callers might not have.
- **Versioning**: tag releases of this repo (e.g. `v1`, `v1.2.0`) and have callers pin to a tag, not `main`, so changes here don't silently break every repo at once.
- **Referencing from another repo**:

  ```yaml
  jobs:
    ci:
      uses: NerdIT-Tech/.github/.github/workflows/reusable-go-ci.yml@v1
      with:
        go-version: "1.22"
  ```
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
      uses: NerdIT-Tech/.github/.github/workflows/reusable-codeql.yml@v1
      permissions:
        actions: read         # CodeQL workflow metadata (private repo)
        contents: read        # checkout
        security-events: write  # SARIF upload
  ```

  The reusable workflows that need a caller grant are:

  | Reusable workflow | Caller must grant |
  |---|---|
  | `reusable-codeql.yml` | `contents: read`, `actions: read`, `security-events: write` |
  | `reusable-scorecard.yml` | `contents: read`, `security-events: write`, `id-token: write` |
  | `reusable-zizmor.yml` | `contents: read`; plus `security-events: write`, `actions: read` when `advanced-security: true` |
  | `reusable-test-go.yml` | `contents: read`, `pull-requests: write` |
  | `reusable-lint-pr-title.yml` | `contents: read`, `pull-requests: write` |
  | `reusable-stale-issues.yml` | `issues: write` |
  | `reusable-sync-issue-labels.yml` | `issues: write` |

See [`../actions/README.md`](../actions/README.md) for composite (reusable) actions.
