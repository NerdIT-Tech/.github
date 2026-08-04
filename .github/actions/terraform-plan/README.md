# terraform-plan

Runs `terraform plan -no-color -input=false -out=<file>` and posts the plan
output as a sticky comment on the PR.

## Getting started

```yaml
permissions:
  pull-requests: write

steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/terraform-init-s3@terraform-init-s3/v1
    with:
      terraform-version: "1.9.0"
      role-to-assume: arn:aws:iam::123456789012:role/terraform-ci
      aws-region: us-east-1
      state-bucket: my-terraform-state

  - uses: NerdIT-Tech/.github/.github/actions/terraform-plan@terraform-plan/v1
    timeout-minutes: 15
```

This action assumes Terraform is already installed and initialized against
the root it's planning -- run
[terraform-init](../terraform-init/README.md) or
[terraform-init-s3](../terraform-init-s3/README.md) first.

To bound a hung plan, set `timeout-minutes:` on the calling `uses:` step
itself -- composite action steps don't support that key, so it can't be an
input here.

To let a failed plan continue past this step instead of failing the job
immediately (e.g. to post the failed plan somewhere before failing), set
`continue-on-error: "true"` and check the `outcome` output -- **not** the
step's own outcome/conclusion, which `continue-on-error` always reports as
`"success"` regardless of whether the plan actually failed.

## Inputs

| Name                | Required | Default  | Description |
| -------------------- | -------- | -------- | ----------- |
| `out-file`           | No       | `tfplan` | Path to write the plan file to. |
| `no-comment`         | No       | `false`  | Don't post the plan output as a PR comment. |
| `continue-on-error`  | No       | `false`  | Don't fail this step (or the job) if `terraform plan` fails -- check the `outcome` output instead. |
| `args`               | No       | `""`     | Additional arguments to pass to `terraform plan`. |
| `working-directory`  | No       | `.`      | Terraform root to plan. |

## Outputs

| Name       | Description |
| ---------- | ----------- |
| `outcome`  | `"success"` or `"failure"` of the underlying `terraform plan` run, regardless of `continue-on-error`. |
| `stdout`   | Captured stdout of `terraform plan` (via setup-terraform's wrapper script). |
| `out-file` | Path the plan file was written to. |
