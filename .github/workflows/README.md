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
  | `reusable-actionlint.yml` | `contents: read` |
  | `reusable-bdd-go.yml` | `contents: read` |
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
  | `reusable-lint-pr-title.yml` | `contents: read`, `pull-requests: write` |
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

## Credentials in a reusable workflow

A reusable workflow cannot read an arbitrary secret name: it references the
`secrets` context by name, so the names have to be fixed by convention.
[`reusable-bdd-go.yml`](reusable-bdd-go.yml) fixes them at `BDD_INSTANCE`,
`BDD_USERNAME`, `BDD_PASSWORD`, and `BDD_TOKEN`. Define those four in the
calling repository and pass them with `secrets: inherit`:

```yaml
jobs:
  bdd:
    uses: NerdIT-Tech/.github/.github/workflows/reusable-bdd-go.yml@v1
    permissions:
      contents: read  # checkout, build, artifact upload
    with:
      suite-command: go test -tags e2e ./... -v
    secrets: inherit
```

`BDD_TOKEN` is an alternative to `BDD_USERNAME`/`BDD_PASSWORD`; the run fails
loudly and names the missing secret if neither is set. The four are declared
`required: false` because `secrets: inherit` supplies them implicitly, and
because a secret read through the `secrets` context keeps GitHub's log
masking — a secret routed through a step output does not.

Two rules the harness holds, both enforced by
[`test_credential_scoping.py`](../tests/test_credential_scoping.py):

- **Credentials are step-scoped and injected after the build.** Checkout,
  module fetch, and compile all run third-party code that has no reason to
  hold a live credential. No job-scope or workflow-scope `env:` map may carry
  a secret, and no secret is interpolated into a `run:` block.
- **The trigger is allowlisted by a `guard` job** that fails with `exit 1` on
  anything other than `schedule` and `workflow_dispatch`. A skipped job is
  indistinguishable from a passing one in a required-check context.

Neither rule needs a GitHub Environment, so neither depends on anyone
editing repository settings before it takes effect.

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
