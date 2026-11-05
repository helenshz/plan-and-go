# 0002. Parse result schema and Writer

- Status: accepted
- Date: 2026-11-05
- Branch: `feat/schema-writer`

## Goal

Define the structured data the parser (VLM) will output, the **parse result**, and write the
**Writer**: deterministic code that turns a parse result into a building file that
`rmf_building_map_tools` accepts.

After this spec the backend can be driven from a parse result instead of a hand-written building
file. The VLM itself comes in spec 0003; here every parse result is hand-written.

Decisions taken for this spec:

- `docs/adr/0002-parser-pixels-writer-meters.md`: pixels in the parse result, metres in the
  building file.
- `docs/adr/0003-wall-thickness-via-generator-wrapper.md`: walls have a real thickness, applied
  by our own wrapper around `building_map_generator`. This answers spec 0001 open question 2.
- `docs/adr/0004-doors-static-and-open.md`: doors are static leaves fixed open, placed by the
  same wrapper. This answers spec 0001 open question 1.
- `docs/adr/0005-nav2-map-from-building-file.md` (spec 0001 open question 4) is not
  implemented here, but the door leaf pose is computed in one function so the map can reuse it.

## Parse result

A pydantic v2 model, exported as JSON Schema so it can later be passed to the VLM as its
structured output format. All coordinates are drawing pixels `[x, y]`, with y pointing down.

```yaml
scale:                  # a known distance on the drawing
  p1: [100, 700]
  p2: [900, 700]
  meters: 8.0
walls:                  # straight walls: centre line + thickness, all in pixels
  - {p1: [100, 700], p2: [900, 700], thickness: 10}
  - {p1: [500, 700], p2: [500, 200], thickness: 10}
doors:                  # each door lies on a wall
  - name: door_ab
    p1: [500, 500]
    p2: [500, 400]
    type: hinged        # hinged | sliding; default hinged
rooms:                  # one point inside each room, e.g. where its name is printed
  - name: room_a
    at: [300, 450]
```

Validation in the model (fails before the Writer runs):

- `scale.meters > 0`, `scale.p1 != scale.p2`.
- Walls and doors have non-zero length; wall `thickness > 0` (required: the drawing always
  shows it, and a default would hide parser omissions).
- Door and room names are unique, non-empty and match `[A-Za-z0-9_]+`
  (they become Gazebo model names and, in stage 2, planner targets).
- At least one wall.

## Writer

`write_building(parse_result, building_name) -> dict`, plus a helper that dumps it to a
`.building.yaml` file. Steps, all deterministic:

1. **Pixels → metres.** `s = scale.meters / |p2 - p1|` (metres per pixel). With `x0` the
   smallest wall x and `y1` the largest wall y in pixels:
   `x_m = (x_px - x0) * s`, `y_m = (y1 - y_px) * s`. The lower-left corner of the walls'
   centre-line bounding box becomes the origin, and y points up.
   Wall thickness: `thickness_m = thickness_px * s`, rounded to 0.01 m (ADR 0003), written as
   the wall parameter `thickness: [3, <metres>]`.
2. **Merge endpoints.** Wall and door endpoints closer than `merge_tol` (default 0.05 m) are
   merged into one vertex, so walls that meet share a vertex.
3. **Split walls at doors.** Each door must lie on exactly one wall: both endpoints within
   `max(door_tol, thickness / 2)` of that wall's centre line (`door_tol` defaults to 0.05 m, so
   a door drawn on either face of a thick wall still counts) and inside its extent. The door is
   projected onto the centre line, and the wall is replaced by the pieces on either side of it,
   keeping the wall's thickness (a piece shorter than `merge_tol` is dropped). A door that lies on no wall raises `DoorNotOnWallError` naming the door.
4. **Doors.** `type` from the parse result, `motion_degrees: 90`, `motion_direction: 1`,
   `plugin: none` (static; `libdoor.so` is not available). The wrapper opens the leaf (ADR 0004).
5. **Rooms.** Each room becomes a named vertex at its point (vertex name = room name). It is
   not connected to any wall.
6. **Floor.** One floor polygon: the convex hull of all wall endpoints, grown by half the
   thickest wall so it reaches under the outer wall faces. The generated world has no ground
   plane of its own (spec 0001), so a floor is required.
7. Output: `coordinate_system: cartesian_meters`, one level `L1`, elevation 0.

Errors the Writer raises are exceptions with a message naming the element, so the self-critic
(spec 0003+) can pass them back to the parser.

## Code layout

- `src/plan_and_go/parse_result.py`: the pydantic model and JSON Schema export.
- `src/plan_and_go/writer.py`: the Writer.
- `src/plan_and_go/generate_world.py`: `python -m plan_and_go.generate_world gazebo <building>
  <world> <model_dir>`, the upstream generator with per-wall thickness (ADR 0003) and open door
  leaves (ADR 0004). The open leaf pose is a plain function of the door's endpoints, type and
  motion parameters, unit-tested on its own.
- `pytest.ini`: `pythonpath = src`, so no package install is needed.
- `pydantic` (v2) added to `environment.yml`.

## Acceptance criteria

Unit tests (no ROS, no LLM):

1. A parse result of the spec 0001 layout drawn at 100 px/m, with y down
   (`tests/fixtures/two_rooms.parse.yaml`), is written to a building file whose walls, door and
   room vertices are at the spec 0001 positions in metres (± 1 mm). In this fixture the left
   outer wall (x = 0) is 50 px thick and all others 10 px, and the building file has
   `thickness` 0.5 and 0.1 accordingly.
2. Endpoints within `merge_tol` become one vertex; endpoints further apart do not.
3. The wall a door lies on is split into two pieces around the door; a door at the end of a wall
   leaves one piece.
4. A door not on any wall raises `DoorNotOnWallError` with the door's name in the message.
5. Invalid parse results (zero-length wall, duplicate room name, `meters <= 0`) are rejected by
   validation.
6. `ParseResult.model_json_schema()` produces a JSON Schema.
7. Open leaf pose: for a 1 m hinged door the leaf is perpendicular to the wall with one end at
   the hinge; for a 1 m sliding door it is shifted 1 m along the wall. Both checked in the door
   frame (± 1 mm).

Integration test (`@pytest.mark.integration`):

8. The building file written from `two_rooms.parse.yaml`, generated with
   `plan_and_go.generate_world`, passes the spec 0001 checks: the generator succeeds, the world
   contains `door_ab` and gzserver loads it without `[Err]`.
9. In that world the robot at (2.0, 2.5) sees the nearest wall, the thick left wall, at
   1.75 ± 0.08 m (2.0 m to its centre line minus 0.25 m). With the upstream 0.1 m wall it would
   be about 1.92 m, so this also checks that the thickness reached Gazebo.
10. From the same pose, the laser ray straight ahead (+x, through the doorway) reads more than
    3.0 m (or no return). With a closed leaf it would read about 1.98 m.
11. The spec 0001 integration test still passes unchanged (it uses the upstream generator).

Door types (added 2026-11-05, after review): a second fixture,
`tests/fixtures/door_types.parse.yaml`, has three rooms, a 0.9 m hinged door in a horizontal
wall and a 1.2 m sliding door in a vertical wall.

12. In the generated `.world` (XML, no Gazebo), for each door: the model is static and sits at the
    middle of the opening (± 1 cm), its x axis lies along the wall, the leaf is
    `width - 0.01` m wide, the joint is `revolute` for the hinged door and `prismatic` for the
    sliding door, and the leaf pose in the world matches `door_geometry.open_leaves` (± 1 cm):
    hinged perpendicular to the wall, sliding parallel to it and shifted by the door width.
13. In Gazebo, a robot in the room both doors lead out of looks through each doorway: the rays
    within ± 5° of each door's direction read more than 3.0 m (or no return).

## Out of scope

- Calling a VLM, prompts and the self-critic loop (spec 0003).
- Snapping wall endpoints onto the middle of another wall (T-junctions); left to the
  self-critic's closure check.
- Room polygons and connectivity (derived later from walls for the self-critic and Nav2).
- Wall height (stays 2.5 m).
- Driving the robot through the door, the occupancy map and Nav2 (ADR 0005, Nav2 spec).

## Open questions

1. **Room vertices in the building file.** Named vertices are the simplest place for room names,
   but RMF also uses named vertices as navigation graph waypoints. Revisit when Nav2 or RMF
   tasks come in.
2. **Tolerances.** `merge_tol` and `door_tol` are in metres after scaling. Whether 5 cm suits
   real VLM output is decided once we see parser output in spec 0003.
