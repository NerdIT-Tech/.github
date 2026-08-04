# resolve-pr

Finds the pull request that was merged via a given commit -- i.e. the commit
is a merge commit created by merging that PR, not a direct push. Useful in a
push-triggered workflow that needs to tell whether the push corresponds to a
PR merge and, if so, reuse that PR's artifacts instead of redoing work.

## Getting started

```yaml
steps:
  - uses: actions/checkout@v7

  - name: Resolve merged PR
    id: resolve-pr
    uses: NerdIT-Tech/.github/.github/actions/resolve-pr@v1

  - name: Use the PR number
    if: steps.resolve-pr.outputs.pr-number != ''
    run: echo "Merged via PR #${{ steps.resolve-pr.outputs.pr-number }}"
```

`actions/checkout` must run before this action -- like any local action, it
has to be resolvable on disk before it can run.

## Inputs

| Name          | Required | Default          | Description                          |
| ------------- | -------- | ----------------- | ------------------------------------ |
| `commit-sha`  | No       | `${{ github.sha }}` | Commit SHA to resolve the merged PR for. |

## Outputs

| Name        | Description                                                  |
| ----------- | -------------------------------------------------------------|
| `pr-number` | Number of the PR merged via this commit, or empty if none matched. |
