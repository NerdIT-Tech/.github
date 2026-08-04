# terraform-release-lock

Best-effort removal of the S3 native-locking lock object. Run this on every
path that takes the lock (a `terraform plan` or `terraform apply` against
the S3 backend) so a killed or cancelled step doesn't leave the `.tflock`
object behind and block every later plan/apply.

Safe to run even when nothing is locked -- the underlying `aws s3 rm` failure
is swallowed, so a missing lock object is a no-op rather than a failure.

## Getting started

```yaml
steps:
  - uses: aws-actions/configure-aws-credentials@v6
    with:
      role-to-assume: arn:aws:iam::123456789012:role/terraform-ci
      aws-region: us-east-1

  # ... terraform-init-s3, terraform-plan, etc ...

  - name: Release Terraform lock
    if: always()
    uses: NerdIT-Tech/.github/.github/actions/terraform-release-lock@terraform-release-lock/v1
    with:
      state-bucket: my-terraform-state
      aws-region: us-east-1
```

Use `if: always()` so the lock is released even if an earlier step in the
job failed or was cancelled. AWS credentials must already be configured in
the job (e.g. via `aws-actions/configure-aws-credentials`, as
[terraform-init-s3](../terraform-init-s3/README.md) does internally) --
this action doesn't assume a role itself.

## Inputs

| Name           | Required | Default              | Description |
| -------------- | -------- | --------------------- | ----------- |
| `state-bucket` | Yes      | --                     | S3 bucket holding the Terraform state object. |
| `aws-region`   | Yes      | --                     | AWS region of the state bucket. |
| `state-key`    | No       | `terraform.tfstate`    | Key of the state object within the bucket (the lock object is this key plus `.tflock`). |

## Outputs

None.
