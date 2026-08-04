# terraform-init

Installs Terraform and runs `terraform init`. Purely a Terraform-CLI wrapper
-- no AWS awareness. Callers that need the S3 backend must configure
credentials themselves first and pass `-backend-config=` flags through
`args` (see [terraform-init-s3](../terraform-init-s3/README.md) for the S3
case already wired up), or set `no-backend: true` for local validation that
needs no backend or credentials at all.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/terraform-init@v1
    with:
      terraform-version: "1.9.0"
      no-backend: "true"
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run, so it can't check out the
repo itself as its first step.

## Inputs

| Name                | Required | Default | Description |
| ------------------- | -------- | ------- | ----------- |
| `terraform-version` | Yes      | --      | Terraform version to install (`hashicorp/setup-terraform`). |
| `no-backend`        | No       | `false` | Run `terraform init -backend=false` instead of using `args` for backend config. |
| `args`              | No       | `""`    | Additional arguments to pass to `terraform init` (e.g. `-backend-config=` flags). |
| `working-directory` | No       | `.`     | Terraform root to initialize. |

## Outputs

None.
