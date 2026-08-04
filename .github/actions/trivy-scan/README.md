# trivy-scan

Runs a Trivy config/IaC scan. Fully independent of the Terraform toolchain
-- Trivy reads the `.tf` files directly, no `init` or provider resolution
needed.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - uses: NerdIT-Tech/.github/.github/actions/trivy-scan@v1
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run.

## Inputs

| Name                | Required | Default          | Description |
| -------------------- | -------- | ---------------- | ----------- |
| `severity`           | No       | `CRITICAL,HIGH`   | Comma-separated severities that fail the scan. |
| `fail-on-findings`   | No       | `true`            | Exit non-zero when matching findings are found (exit-code 1 vs 0). |
| `version`            | No       | `v0.72.0`         | `aquasecurity/trivy-action` version. Pinned above the action's own default because earlier releases don't recognize that `github_repository_vulnerability_alerts` satisfies `GIT-0003` for a linked `github_repository`. |
| `working-directory`  | No       | `.`               | Path to scan. |

## Outputs

None.
