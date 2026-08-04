# semantic-pull-request

Checks that a pull request title follows the [Conventional
Commits](https://www.conventionalcommits.org/en/v1.0.0/) format, and posts a
sticky comment on the PR explaining what's wrong when it doesn't.

## Getting started

```yaml
on:
  pull_request:
    types: [opened, edited, synchronize]

permissions:
  pull-requests: write

jobs:
  lint-pr-title:
    runs-on: ubuntu-latest
    steps:
      - uses: NerdIT-Tech/.github/.github/actions/semantic-pull-request@semantic-pull-request-v1
```

`permissions: pull-requests: write` is required so the action can post/delete
its lint-error comment.

## Inputs

| Name                 | Required | Default                              | Description |
| -------------------- | -------- | ------------------------------------- | ----------- |
| `types`              | No       | `feat, fix, docs, style, refactor, perf, test, chore, build, ci` | List of allowed commit types. |
| `requireScope`       | No       | `true`                                | Require a scope in the PR title. |
| `scopes`             | No       | `""` (any scope allowed)              | List of allowed scopes. |
| `subjectPattern`     | No       | `^#[0-9]+.*$`                         | Regex the PR title's subject must match. |
| `no-comment`         | No       | `false`                               | Skip posting the lint result as a PR comment. |
| `exampleCommitTitle` | No       | `feat(ci): #1234 add new feature`     | Example title shown in the error message. |

## Outputs

None.
