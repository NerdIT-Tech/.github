# Reusable (composite) actions

Composite actions shared across NerdIT-Tech repos. Each action lives in its
own subdirectory with an `action.yml` at its root.

## Conventions

- **Layout**: one directory per action, e.g. `setup-go/action.yml`, `publish-release/action.yml`.
- **Versioning**: tag releases of this repo (e.g. `v1`, `v1.2.0`) and have callers pin to a tag, not `main`.
- **Referencing from another repo**:

  ```yaml
  steps:
    - uses: NerdIT-Tech/.github/.github/actions/setup-go@v1
      with:
        go-version: "1.22"
  ```

See [`../workflows/README.md`](../workflows/README.md) for reusable `workflow_call` workflows.
