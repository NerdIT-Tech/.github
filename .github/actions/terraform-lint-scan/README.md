# terraform-lint-scan

Backend-less static analysis bundle for a Terraform root: fmt check,
validate, tflint, and a Trivy IaC scan. Composes the
[terraform-fmt](../terraform-fmt/README.md),
[terraform-init](../terraform-init/README.md),
[terraform-validate](../terraform-validate/README.md), and
[tflint](../tflint/README.md) actions in this same directory rather than
duplicating their steps. Pull in just one of those instead of this whole
bundle if a project only wants (say) tflint. The Trivy step calls
[aquasecurity/trivy-action](https://github.com/aquasecurity/trivy-action)
directly rather than through a local wrapper, since a wrapper wasn't
adding anything over the upstream action.

No AWS credentials or state access required, so this is safe to run on
untrusted PR branches.

Every check in the bundle -- fmt, validate, tflint, and Trivy -- posts its
findings as GitHub annotations (`::error`/`::warning file=,line=,col=::`)
on failure, so issues show up inline on the PR's "Files changed" tab, the
same way `yaml-lint` and `actionlint` do in this repo.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/terraform-lint-scan@terraform-lint-scan/v1
    with:
      terraform-version: "1.9.0"
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run, so it can't check out the
repo itself as its first step. It also references the fmt/init/validate/
tflint actions by relative path, so all of them need to live at the same
ref of this repo.

## Inputs

| Name                 | Required | Default        | Description |
| --------------------- | -------- | -------------- | ----------- |
| `terraform-version`   | Yes      | --              | Terraform version to install (`hashicorp/setup-terraform`). |
| `tflint-version`      | No       | `latest`        | tflint version to install, or `"latest"`. |
| `trivy-severity`      | No       | `CRITICAL,HIGH` | Comma-separated severities that fail the Trivy scan. |
| `trivy-version`       | No       | `v0.72.0`       | `aquasecurity/trivy-action` version. |
| `working-directory`   | No       | `.`             | Terraform root to lint/scan. |

## Outputs

None.
