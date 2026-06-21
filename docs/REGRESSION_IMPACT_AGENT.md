# Regression Impact Agent

The Regression Impact Agent is a deterministic QA helper. It reads changed files and PR text, then suggests the regression test IDs that should be rerun.

It does not approve releases, mark manual tests as passed, or replace human evidence. Its job is to reduce tracking mistakes.

## Is This Using An LLM?

No. The current agent does not call an LLM or external AI API.

It is an agent in the practical software sense: it observes an input, applies rules, decides the next testing action, and hands that action to CI.

Current loop:

```text
PR diff / local changed files
        -> path rules
        -> suggested regression IDs
        -> automated command pack
        -> manual verification list
```

This is intentionally safer for QA because regression selection should be predictable. An LLM can be added later as a summarizer or reviewer, but it should not be the source of truth for release approval.

## What It Does

1. Reads changed files from a PR or local git diff.
2. Matches those files against `qa/regression-impact-agent-rules.json`.
3. Extracts manually mentioned test IDs such as `SIT-D-011` from PR text.
4. Outputs suggested regression IDs.
5. Lets the existing runner, `scripts/run_regression_pack.py`, execute automated checks and list manual checks.

## Local Usage

From the repo root:

```bash
scripts/suggest_regression_pack.py --changed-file ArthamantriAndroid/app/src/main/java/com/finsaathi/android/core/FinancialRiskMessageDetector.kt
```

Expected output:

```text
SIT-D-011
```

For a readable report:

```bash
scripts/suggest_regression_pack.py \
  --changed-file ArthamantriAndroid/app/src/main/java/com/finsaathi/android/core/FinancialRiskMessageDetector.kt \
  --markdown
```

For your current local uncommitted changes:

```bash
scripts/suggest_regression_pack.py --markdown
```

Then run the suggested regression pack:

```bash
scripts/run_regression_pack.py SIT-D-011 --run-auto
```

## GitHub Actions Integration

The workflow `.github/workflows/regression-pack.yml` now runs the agent on pull requests.

PR flow:

1. You open a PR.
2. The workflow reads the PR diff.
3. The Regression Impact Agent suggests test IDs.
4. The workflow combines:
   - IDs mentioned by you in the PR title/body
   - IDs suggested by the agent from changed files
5. CI runs the automated command pack.
6. The GitHub Actions summary shows:
   - automated pass/fail status
   - manual verification still required
   - conditional verification still required

## How To Tell The System Manual Testing Is Done

Manual testing cannot be auto-proven by CI. Record it in the PR body or a PR comment.

Example:

```markdown
## Manual Verification

- [x] SIT-D-011 PASS - Pixel 7, Android 14, red-risk SMS alert displayed.
- [x] SIT-D-012 PASS - Yellow-risk message showed non-blocking warning.
- [x] SIT-D-013 PASS - Green/benign message did not interrupt.
- [x] SIT-D-014 PASS - Alert copy was readable in Hindi.

## Conditional Verification

- [x] UAT-004 Not impacted - warning explanation copy did not change.
```

## Rule Updates

When a new component or test ID is added, update:

- `qa/regression-impact-agent-rules.json` for path-to-test suggestions.
- `qa/regression-impact-map.yml` for automated/manual rerun packs.

Keep the agent conservative: it is better to suggest one extra regression pack than miss a risky area.
