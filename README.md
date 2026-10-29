# plan-and-go

One floor plan, one sentence, and a robot walks to its goal in a building generated from that plan.

Course project for *Agentic AI and Foundation Models* (WS2026/27).

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

The LLMs only produce structured data (YAML / JSON plans). Geometry conversion, SDF generation and navigation are handled by deterministic code.

## Repository layout

```
plan-and-go/
├── docs/PROJECT_PLAN.md               project plan, related work, eval design (Chinese)
└── external/gazebo_world_generator    git submodule (MIT): SDF utils, JSON validator, LLM wrapper
```

## Setup

```bash
git clone --recurse-submodules <repo-url>
# or, in an existing clone:
git submodule update --init --recursive
```

External dependencies, not vendored here:

- ROS 2 Humble + Gazebo Classic 11 (or Jazzy + Harmonic)
- [`rmf_building_map_tools`](https://github.com/open-rmf/rmf_traffic_editor) to convert `.building.yaml` to `.world`
- TurtleBot3: `sudo apt install ros-humble-turtlebot3*`

## Third-party code

| Component | License |
|---|---|
| [robotics-upo/gazebo_world_generator](https://github.com/robotics-upo/gazebo_world_generator) | MIT |
| [open-rmf/rmf_traffic_editor](https://github.com/open-rmf/rmf_traffic_editor) | Apache-2.0 |
