# 0001. Building file to Gazebo world backend

- Status: accepted
- Date: 2026-10-29
- Branch: `feat/backend-smoke-test`

## Goal

Show that the deterministic backend works end to end: a correct, hand-written building file is
turned into a Gazebo world by `rmf_building_map_tools`, a TurtleBot3 loads into that world, and
its laser scanner sees the walls.

No VLM is involved. If a later stage fails, this spec lets us tell a parser error from a backend
error.

## Inputs

A hand-written fixture, `tests/fixtures/two_rooms.building.yaml`, describing an invented layout:

- `coordinate_system: cartesian_meters`, so vertices are in metres and no drawing is needed.
- One level. Two rooms of 4 m × 5 m side by side, 8 m × 5 m in total, with closed outer walls.
  - `room_a`: x 0–4, y 0–5. `room_b`: x 4–8, y 0–5.
- One hinged door, 1 m wide, in the middle of the shared wall (x = 4, y 2.0–3.0), with
  `plugin: none` (static, closed). The shared wall is split around the door.
- One floor polygon per room, serving as the ground, with a custom `room_name` parameter
  (`room_a`, `room_b`).

## Deliverables

- The fixture above.
- `launch/sim.launch.py`: starts headless or GUI Gazebo with a given world file and spawns a
  TurtleBot3 at a given pose. It adds the generated model directory to `GAZEBO_MODEL_PATH` and
  defaults `TURTLEBOT3_MODEL` to `burger` when unset.
- An integration test marked `@pytest.mark.integration`, skipped by default and run with
  `pytest -m integration`. It writes generated files to pytest's `tmp_path`.

## Acceptance criteria

All are checked by the integration test.

1. `ros2 run rmf_building_map_tools building_map_generator gazebo <fixture> <world> <model_dir>`
   exits with code 0 and writes the `.world` file.
2. The `.world` file contains a model for the door.
3. `gzserver` loads the world and the TurtleBot3 without `[Err]` log lines.
4. With the robot spawned at (2.0, 2.5) in `room_a`, the minimum range on `/scan` is
   1.95 m ± 0.15 m (distance from the room centre to the inner face of the nearest wall, given
   0.1 m walls; the tolerance covers the scanner's offset from the robot centre).

## Constraints

- No LLM calls. Everything here is deterministic code.
- Wall thickness and height are fixed by `rmf_building_map_tools` at 0.1 m and 2.5 m
  (`building_map/wall.py:16-17`); yaml parameters cannot change them.
- The generated world has no ground plane of its own, so the floor polygons are required.
- `libdoor.so` (the RMF door plugin) is not in the conda env, hence `plugin: none` on the door.
- Manual runs write generated files to `outputs/` (gitignored).
- Do not edit `external/gazebo_world_generator` or the installed `rmf_building_map_tools`.

## Out of scope

- VLM parser and self-critic.
- The intermediate schema the parser will output, and the Writer that turns it into a building
  file.
- Nav2, occupancy grid maps and the robot passing through the door.
- Floor plans exported from Revit/IFC, and evals.

## Open questions

1. **Door traversal.** Without `libdoor.so`, a door is either static and closed (`plugin: none`)
   or a free, unactuated panel. How should the robot get through a door: build the RMF door
   plugin from source, model doors as wall gaps, or something else? Decide when navigation
   is needed; likely an ADR.
2. **Real wall thickness.** All walls come out 0.1 m thick. Accept it and compare wall centre
   lines in evals, or extend `Wall` in our own code to read a thickness parameter? Decide in the
   eval spec.
3. **Writer coordinates.** Should the Writer emit pixel coordinates with a scale measurement
   (`reference_image`, can be overlaid on the floor plan in traffic_editor) or metres
   (`cartesian_meters`)? Decide in spec 0002.
4. **Map for Nav2.** `rmf_building_map_tools` produces no occupancy grid. Rasterise walls from
   the building file ourselves, run SLAM, or use the map plugin from
   `external/gazebo_world_generator`? Decide when Nav2 comes in.
