# tflint

Runs tflint's own plugin init followed by a recursive lint pass. Doesn't
need Terraform installed at all -- tflint is a standalone binary, fully
independent of the fmt/init/validate chain.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/tflint@tflint/v1
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run.

## Inputs

| Name                | Required | Default  | Description |
| -------------------- | -------- | -------- | ----------- |
| `tflint-version`     | No       | `latest` | tflint version to install, or `"latest"`. |
| `recursive`          | No       | `true`   | Process subdirectories too (`--recursive`). |
| `working-directory`  | No       | `.`      | Terraform root to lint. |

## Outputs

None.
