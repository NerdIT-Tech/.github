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

See [`../actions/README.md`](../actions/README.md) for composite (reusable) actions.
