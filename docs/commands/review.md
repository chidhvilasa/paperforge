# paperforge review

Run an AI-assisted paper review using the `llm` CLI tool. Output is advisory only and never a source of truth.

## Usage

```
paperforge review [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| None | — | — |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Project root directory |
| `--model`, `-m` | `None` | llm model to use (e.g. `gpt-4o`). Uses the llm default if omitted. |
| `--help` | — | Show help and exit |

## Example

```bash
# Review with the default llm model
paperforge review

# Review with GPT-4o
paperforge review --model gpt-4o

# Review with a local model
paperforge review --model mistral-7b-instruct-v0.1

# Review a project in another directory
paperforge review --path ~/papers/vanet-paper --model claude-3-5-sonnet
```

## Output

Prints the AI's response in a yellow "AI Review" panel (yellow = advisory, not
authoritative), then two confirmation lines:

```
╭─ AI Review ────────────────────────────────────────╮
│ 1. NOVELTY                                         │
│    ...                                             │
│ ...                                                │
╰─────────────────────────────────────────────────────╯
Review saved to .paperforge/review/latest_review.md
This output is advisory only. Verify all suggestions.
```

## Errors

| Condition | Message |
|-----------|---------|
| Project not initialized | `Not a PaperForge project. Run \`paperforge init\` first.` (exit 1) |
| Doctor ERRORs found | `Review blocked. Fix all ERRORs before running review.` — lists each issue, exits 1 before calling llm |
| `llm` not found on PATH | `llm is not available on PATH.` / `Install it with: uv add llm` / `Then configure a model: llm keys set openai` (exit 1) |
| `llm` exits non-zero | `llm call failed.` followed by the captured stderr and `Check your llm configuration: llm models list` (exit 1) |

## Notes

- **Requires `llm` on PATH.** Install separately: `pip install llm` or `uv add llm`. Configure API keys with `llm keys set openai`.
- **Runs doctor checks first.** Any ERROR blocks the review. Fix all errors before reviewing.
- Output is **advisory only**. It never becomes a source of truth. See [CONSTITUTION.md](../../CONSTITUTION.md).
- Review output is saved to `.paperforge/review/latest_review.md`.
- `review/` is in `.paperforge/.gitignore` — AI output is never committed to git.
- Use `--model` to specify any model supported by your `llm` installation.

**Related commands:** `paperforge doctor`, `paperforge build`
