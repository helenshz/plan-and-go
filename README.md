# plan-and-go

Give it a floor plan and a sentence: a VLM agent rebuilds the building in Gazebo, and a robot
drives where you told it to go.

> [!WARNING]
> **Work in progress.** This is a course project (*Agentic AI and Foundation Models*, TUM,
> WS2026/27) in its early stages. There is no runnable pipeline yet: the repository currently
> holds the plan, specs and design decisions. Interfaces and file formats will change. See
> [Status](#status) for what exists today.

## Pipeline

**Stage 1 (core): floor plan → Gazebo world**

```
floor plan (PDF / image)
   ↓  VLM parser agent + self-critic loop (walls, doors, rooms, scale)
.building.yaml
   ↓  rmf_building_map_tools building_map_generator
Gazebo .world
```

**Stage 2 (stretch): text task → robot execution**

```
"Go to the kitchen, check whether door 2 is closed, then return to the entrance"
   ↓  LLM task planner (fixed action set, targets validated against the map)
[{"action": "navigate", "target": "Kitchen"}, ...]
   ↓  room name → pose → Nav2 NavigateToPose / FollowWaypoints
TurtleBot3 in simulation
```

The LLMs only produce structured data (YAML / JSON plans). Geometry conversion, SDF generation
and navigation are handled by deterministic code
([ADR 0001](docs/adr/0001-building-yaml-as-ir.md)).

## Status

- [x] Project plan, related work and eval design ([`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md), Chinese)
- [x] Conda env with ROS 2 Humble, Gazebo Classic 11, `rmf_building_map_tools`, TurtleBot3, Nav2
- [ ] Spec for the deterministic backend *(in review on branch `feat/backend-smoke-test`)*
- [ ] Backend smoke test: hand-written building file → Gazebo world → TurtleBot3 sees the walls *(in progress)*
- [ ] Parser output schema and Writer (→ `.building.yaml`)
- [ ] VLM parser agent with self-critic loop
- [ ] Evals: floor plans exported from Revit/IFC as input and ground truth, baselines
- [ ] Stage 2: text task → LLM planner → Nav2

### Known limitations

- `rmf_building_map_tools` gives every wall a fixed thickness of 0.1 m and height of 2.5 m.
- The RMF door plugin is not available in the conda env, so doors are static for now.
- Out of scope: curved walls, stairs, multi-level buildings, multi-robot scheduling.

## Repository layout

```
plan-and-go/
├── README.md
├── CLAUDE.md                          instructions for the coding agent
├── environment.yml                    RoboStack conda env
├── docs/
│   ├── PROJECT_PLAN.md                project plan, related work, eval design (Chinese)
│   └── adr/                           architecture decision records
├── scripts/save_traces.sh             copy Claude Code transcripts into traces/, redact keys
├── traces/                            agent session transcripts (for the report)
├── .claude/skills/                    agent skills (grill-with-docs, domain-modeling)
└── external/gazebo_world_generator    git submodule (MIT): SDF utils, JSON validator, LLM wrapper
```

## Setup

```bash
git clone --recurse-submodules https://github.com/helenshz/plan-and-go.git
# or, in an existing clone:
git submodule update --init --recursive
```

ROS 2 Humble, Gazebo Classic 11, [`rmf_building_map_tools`](https://github.com/open-rmf/rmf_traffic_editor)
(`.building.yaml` → `.world`), TurtleBot3 and Nav2 are installed into a conda env from
[RoboStack](https://robostack.github.io) (Python 3.9), no system ROS needed:

```bash
conda env create -f environment.yml -p <path>/plan_and_go
conda activate <path>/plan_and_go
```

Do not source a system ROS (`/opt/ros/humble/setup.bash`) in the same shell.

LLM calls go through an OpenAI-compatible API (Gemini Flash / GLM Flash). Put API keys in a
`.env` file (gitignored); never commit them.

## How this project is developed

The course grades the development process, so the history is part of the deliverable:

- **Spec first**: each round of work starts with a written spec, produced after the coding
  agent interviews the author (`/grill-with-docs`).
- **Decisions**: non-trivial architectural choices get an ADR in `docs/adr/`.
- **Branches and PRs**: one branch per round, merged into `main` with a merge commit, never
  squashed. Commits follow Conventional Commits.
- **Traces**: Claude Code session transcripts are saved to `traces/` with keys redacted.

## Third-party code

| Component | License |
|---|---|
| [robotics-upo/gazebo_world_generator](https://github.com/robotics-upo/gazebo_world_generator) | MIT |
| [open-rmf/rmf_traffic_editor](https://github.com/open-rmf/rmf_traffic_editor) | Apache-2.0 |
| [mattpocock/skills](https://github.com/mattpocock/skills) (`.claude/skills/`) | MIT |
