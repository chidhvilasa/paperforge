# paperforge improve

AI-assisted claim text improvement. Suggests precision and IEEE journal style enhancements using `llm`, recording history snapshots before applying edits. Never auto-applies changes.

## Usage

```
paperforge improve [CLAIM_ID] [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `CLAIM_ID` | Specific claim ID to improve (e.g. `claim_01`) | Optional (required unless `--all` is passed) |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--model`, `-m` | `llm default` | Model to pass to `llm` (e.g. `gpt-4o`, `claude-3-5-sonnet`) |
| `--all`, `-a` | `false` | Process all unverified claims sequentially |
| `--help` | — | Show help and exit |

## Examples

```bash
# Improve a single claim
paperforge improve claim_01

# Improve all unverified claims with a custom model
paperforge improve --all --model gpt-4o
```

## Interactive Prompting

For each targeted claim, `paperforge improve`:
1. Constructs a prompt incorporating linked experiment metrics and relevant doctor issues.
2. Calls `llm prompt` and displays the formatted suggestions panel.
3. Extracts suggested text from the output.
4. Asks for confirmation: `Apply suggested text? [y/n/s(kip all)]`.
5. If `y` is chosen:
   - Records a history snapshot of the previous claim state.
   - Updates the claim text in `.paperforge/claims/<claim_id>.yaml`.

## Safety & Governance

- **Advisory only**: Suggestions are presented to the user for explicit approval.
- **Non-destructive**: Snapshots are saved to `.paperforge/history/` before edits are written.
- **Offline / Local first**: Requires user-configured `llm` CLI setup.

**Related commands:** `paperforge doctor`, `paperforge review`, `paperforge diff`, `paperforge log`
