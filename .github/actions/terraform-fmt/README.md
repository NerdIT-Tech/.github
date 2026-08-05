# terraform-fmt

Fails if any `.tf` file isn't canonically formatted. Standalone and
order-independent -- unlike `terraform validate`, `fmt` doesn't need
`terraform init` first.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/terraform-fmt@terraform-fmt/v1
    with:
      terraform-version: "1.9.0"
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run.

## Inputs

| Name                | Required | Default | Description |
| ------------------- | -------- | ------- | ----------- |
| `terraform-version` | Yes      | --      | Terraform version to install (`hashicorp/setup-terraform`). |
| `check`             | No       | `true`  | Fail instead of writing changes back to disk (`-check`). |
| `recursive`         | No       | `true`  | Process subdirectories too (`-recursive`). |
| `diff`              | No       | `true`  | Print a diff of changes needed (`-diff`). |
| `working-directory` | No       | `.`     | Terraform root to check. |

## Outputs

None.
