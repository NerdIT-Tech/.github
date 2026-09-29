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

- **Referencing a sibling action from within this repo**: use the
  self-repository `$/` prefix (e.g. `$/.github/actions/terraform-init`).
  It resolves to this repo at the exact commit that is running and, unlike
  `./`, ignores the caller's checkout — so it works from inside a composite
  action or a reusable workflow. Do not add a version: `$/` must have no
  `@ref`, and the running commit is the whole point. It needs runner
  `2.336.0` or newer and works on github.com only, so external callers
  still need the fully-qualified form above.

  A composite action's `./`-relative `uses:` resolves against the *caller's*
  checkout, not against `NerdIT-Tech/.github` — even when the caller is
  another composite action right next to it in this same repo (#36). `$/`
  replaces that trap; `./` is still wrong here.

See [`../workflows/README.md`](../workflows/README.md) for reusable `workflow_call` workflows.
