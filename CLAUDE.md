# CLAUDE.md

Course project for *Agentic AI and Foundation Models* (TUM, WS2026/27). Graded mainly on the
development process: Git history, ADRs, traces, tests and evals. Keep that in mind for every change.

## What this is

Floor plan (PDF/image) → VLM parser agent with self-critic loop → `.building.yaml` (Open-RMF)
→ `rmf_building_map_tools` → Gazebo `.world` → TurtleBot3 + Nav2.
Stage 2 (stretch): text task → LLM planner (fixed action set) → Nav2.

Full plan, related work and eval design: `docs/PROJECT_PLAN.md` (Chinese).
Architecture decisions: `docs/adr/`.

## Core rule

LLMs only output structured data (validated against a schema). Geometry, YAML/SDF generation,
validation and navigation are deterministic code. See `docs/adr/0001-building-yaml-as-ir.md`.
Do not add LLM calls to code paths that can be done deterministically.

## Environment

- All project dependencies live in one conda env on the Data disk (RoboStack, ROS 2 Humble,
  Gazebo Classic 11, Python 3.9):
  `conda activate /media/helenshz/Data/your_env_path/plan_and_go`
- Never install project deps with `sudo apt` (root partition is nearly full) and never
  `source /opt/ros/humble/setup.bash` together with this env; the system ROS conflicts with it.
- In the env: `rmf_building_map_tools` 1.5.0, `turtlebot3_gazebo`, `navigation2`/`nav2_bringup`,
  `gazebo_ros`, `ros-base`. `traffic_editor` (GUI) is not on conda; build from source if needed.
- `external/gazebo_world_generator`: git submodule (MIT). Do not edit it; wrap or import instead.

## LLM usage and cost

- Cheap models only (Gemini Flash / GLM Flash via an OpenAI-compatible API). Every test and eval
  run calls the model, so keep prompts small and record the cost of each eval run.
- API keys only in `.env` (gitignored). Never hard-code or print them.
- Unit tests must not call a real LLM; mock the client. Real calls belong in evals.

## Workflow

- Spec before code; for any non-trivial architectural choice, add an ADR in `docs/adr/`
  (copy `docs/adr/template.md`, next number).
- Never commit, push, force-push, merge or delete branches without the user's explicit approval
  for that specific action. Editing a file is not permission to commit it, and an earlier
  approval does not carry over. After changes, show what changed and propose the commit message.
- Work on a branch, one commit per finished step; the message says what and why.
- Commit subjects follow Conventional Commits: `<type>: <lowercase summary>`, imperative, no
  trailing period. Types: `feat` (new functionality), `fix` (bug fix), `docs` (docs, ADRs,
  report), `test` (tests/evals only), `refactor` (no behaviour change), `chore` (env, tooling,
  scripts, traces, config). Example: `feat: add self-critic wall closure check`.
- Do not squash merges; the history is graded.
- Transcripts: run `scripts/save_traces.sh` before committing a session's work. It copies
  Claude Code sessions into `traces/`, redacts anything that looks like a key and fails if
  any remains.

## Out of scope (for now)

Curved walls, stairs, multi-level buildings, multi-robot RMF scheduling.
