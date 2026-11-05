# 0005. The Nav2 occupancy map is rasterised from the building file

- Status: accepted
- Date: 2026-11-05

## Context

Nav2 needs a 2D occupancy grid map (PGM image + map YAML). `rmf_building_map_tools` does not
produce one (spec 0001, open question 4). The map has to match the generated world: same walls,
same thickness (ADR 0003), same open door leaves (ADR 0004).

This ADR fixes the direction now; the code comes with the Nav2 spec.

## Decision

Deterministic Python code (shapely) reads the building file and draws the map directly:

- each wall as a rectangle (centre line + thickness), each open door leaf at the same pose the
  generator wrapper uses;
- free space inside the building outline, unknown outside;
- resolution 0.05 m (Nav2 default), origin taken from the building file's coordinates, so map
  and world frames coincide without any alignment step.

## Alternatives considered

- **`gazebo_ros2_2dmap_plugin` (used by `external/gazebo_world_generator`).** Ray-casts the
  running world, so it captures exactly what Gazebo has. But it is a separate C++ package that
  must be built from source in the conda env, and every map needs a Gazebo run.
- **SLAM (`slam_toolbox`).** Closest to a real robot, but slow, noisy and needs an exploration
  route; map errors would mix with parser errors in the eval.
- **Decide later.** Possible, but the door decision (ADR 0004) already constrains the map, and
  the choice is clear.

## Consequences

- Maps are produced in seconds without Gazebo and can be unit-tested against known geometry.
- Map and world come from the same building file; if they disagree, it is a bug in our code, not
  noise. Door leaf poses must be computed in one place and shared by the wrapper and the map.
- The map shows only what the building file describes. Anything Gazebo adds on its own (none
  today) would be missing.
- A SLAM map can still be added later as an eval comparison.
