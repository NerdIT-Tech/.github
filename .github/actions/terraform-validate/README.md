# terraform-validate

Runs `terraform validate` against the current working directory.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/terraform-init@terraform-init/v1
    with:
      terraform-version: "1.9.0"
      no-backend: "true"

  - uses: NerdIT-Tech/.github/.github/actions/terraform-validate@terraform-validate/v1
    with:
      terraform-version: "1.9.0"
```

Precondition: some prior step in this job must have already run
`terraform init` (e.g. [terraform-init](../terraform-init/README.md) with
`no-backend: "true"`) -- validate reads the `.terraform/` directory that
init populates and doesn't create it itself. `actions/checkout` must also
run before this action, since it has to be resolvable on disk before it can
run.

## Inputs

| Name                | Required | Default | Description |
| -------------------- | -------- | ------- | ----------- |
| `terraform-version` | Yes      | --      | Terraform version to install (`hashicorp/setup-terraform`). |
| `working-directory`  | No       | `.`     | Terraform root to validate. |

## Outputs

None.
