# Reusable (composite) actions

Composite actions shared across NerdIT-Tech repos. Each action lives in its
own subdirectory with an `action.yml` at its root.

## Conventions

- **Layout**: one directory per action, e.g. `setup-go/action.yml`, `publish-release/action.yml`.
- **Versioning**: each action is released independently via release-please, scoped to commits that touch its directory. Tags look like `<action>/v1.2.0`, with a floating `<action>/v1` major tag that callers should pin to instead of `main`.
- **Referencing from another repo**:

  ```yaml
  steps:
    - uses: NerdIT-Tech/.github/.github/actions/setup-go@setup-go/v1
      with:
        go-version: "1.22"
  ```

- **Referencing a sibling action from within this repo**: a composite
  action's `./`-relative `uses:` resolves against the *caller's* checkout,
  not against `NerdIT-Tech/.github` — even when the caller is another
  composite action that lives right next to it in this same repo. Reference
  siblings the same fully-qualified way an external caller would (e.g.
  `NerdIT-Tech/.github/.github/actions/terraform-init@terraform-init/v1`),
  not `./.github/actions/terraform-init`.

See [`../workflows/README.md`](../workflows/README.md) for reusable `workflow_call` workflows.
