# Agent skills

| Skill | Source | License |
|---|---|---|
| `grill-with-docs` (wrapper: calls `grilling` + `domain-modeling`) | [mattpocock/skills](https://github.com/mattpocock/skills) @ `a496f55`, `skills/engineering/grill-with-docs` | MIT, see `LICENSE-mattpocock-skills` |
| `grilling` | same repo, `skills/productivity/grilling` | MIT |
| `domain-modeling` | same repo, `skills/engineering/domain-modeling` | MIT |

Copied verbatim except for the Codex-only `agents/openai.yaml` files, which were dropped.
Local changes to the skills are made in separate commits so the diff to upstream stays visible.

Local changes:

- `domain-modeling/ADR-FORMAT.md`: ADRs follow `docs/adr/template.md` (Status, Date, Context,
  Decision, Alternatives, Consequences) instead of the upstream one-paragraph format; English only.
  The "when to offer an ADR" criteria are kept unchanged.
- `grilling/SKILL.md`: questions in Chinese, written files in English.
