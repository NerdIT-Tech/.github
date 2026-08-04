# terraform-init-s3

Convenience wrapper for the common case across every repo here: state lives
in the S3 native-locking backend, reached by assuming an AWS role over OIDC.
Composes `aws-actions/configure-aws-credentials` (assumes the role) and the
[terraform-init](../terraform-init/README.md) action (builds the
`-backend-config=` flags and runs `terraform init`) so callers don't have to
wire both by hand.

Use `terraform-init` directly instead of this for the no-backend /
local-validation case, or if a project ever needs a non-S3 backend.

## Getting started

```yaml
permissions:
  id-token: write   # required for OIDC role assumption
  contents: read

steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/terraform-init-s3@terraform-init-s3/v1
    with:
      terraform-version: "1.9.0"
      role-to-assume: arn:aws:iam::123456789012:role/terraform-ci
      aws-region: us-east-1
      state-bucket: my-terraform-state
      state-key: my-project/terraform.tfstate
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run. It also references the
`terraform-init` action by relative path, so both actions need to live at
the same ref of this repo.

## Inputs

| Name                 | Required | Default              | Description |
| --------------------- | -------- | -------------------- | ----------- |
| `terraform-version`   | Yes      | --                    | Terraform version to install (`hashicorp/setup-terraform`). |
| `role-to-assume`      | Yes      | --                    | ARN of the AWS role to assume over OIDC. |
| `aws-region`          | Yes      | --                    | AWS region for both the STS assume-role call and the S3 backend. |
| `state-bucket`        | Yes      | --                    | S3 bucket holding the Terraform state object. |
| `state-key`           | No       | `terraform.tfstate`   | Key of the state object within the bucket. |
| `use-lockfile`        | No       | `true`                | Use the S3 backend's native locking (`use_lockfile`). |
| `working-directory`   | No       | `.`                   | Terraform root to initialize. |

## Outputs

None.
