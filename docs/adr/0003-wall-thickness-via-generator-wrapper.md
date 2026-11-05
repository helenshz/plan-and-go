# 0003. Real wall thickness via our own wrapper around `building_map_generator`

- Status: accepted
- Date: 2026-11-05

## Context

Walls on a floor plan have a real thickness (typically 0.1–0.5 m), and it matters: it changes
room sizes, door depths and what the robot's laser sees. `rmf_building_map_tools` 1.5.0 hard-codes
every wall at 0.1 m (`building_map/wall.py:16-17`); no building file parameter changes it.
Spec 0001 left this open (question 2). We must not edit the installed package.

How the generator builds walls (1.5.0): `Level.generate_walls` groups walls by identical
parameter dicts and creates one `Wall` object per group, looked up as `building_map.level.Wall`.
`Wall.wall_thickness` is used for both the visual and the collision mesh.

## Decision

1. Each wall in the building file carries a custom parameter `thickness` (double, metres).
   `rmf_building_map_tools` ignores unknown wall parameters, so the file stays valid for it.
2. We provide our own entry point, `python -m plan_and_go.generate_world`, with the same
   arguments as `building_map_generator`. Before calling the upstream `main()`, it replaces
   `building_map.level.Wall` with a subclass that sets `wall_thickness` from the group's
   `thickness` parameter when present.
3. Walls without `thickness` keep the upstream 0.1 m, so hand-written files like the spec 0001
   fixture behave exactly as before.

A prototype on the spec 0001 fixture (one wall set to 0.3 m) produced a 0.3 m wide mesh for that
wall and 0.1 m for the rest.

## Alternatives considered

- **Accept 0.1 m and compare centre lines in evals.** No code, but rooms and the robot's view
  are wrong by up to half a wall on each side, and the IFC ground truth has real thickness.
  Rejected.
- **Post-process the generated SDF/OBJ.** Possible, but means parsing and rewriting meshes the
  generator already wrote. More code than a three-line subclass.
- **Fork or vendor `rmf_building_map_tools`.** Full control, but we would own a copy of a whole
  package to change one attribute.

## Consequences

- World generation goes through our wrapper; tests and scripts call it instead of
  `ros2 run rmf_building_map_tools building_map_generator`.
- The patch depends on 1.5.0 internals (`building_map.level.Wall`, `wall_thickness`). An
  integration test with a thick wall catches a change when the package is upgraded.
- Walls are grouped by exact parameters, so each distinct thickness becomes a separate mesh.
  The Writer rounds thickness to 1 cm to keep the number of groups small.
- Wall height stays 2.5 m; the same mechanism could set it later if needed.
