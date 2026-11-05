# 0004. Doors are static door leaves fixed in the open position

- Status: accepted
- Date: 2026-11-05

## Context

The robot has to move between rooms, so it must get through doors. `rmf_building_map_tools`
generates each door as a model with a leaf and a joint, actuated by the RMF door plugin
`libdoor.so`, which only opens on requests from the RMF door supervisor. The plugin is not in our
conda env, and RMF scheduling is out of scope (CLAUDE.md). With `plugin: none` the door is a
static model, and the leaf sits in the closed position, so the rooms are not connected in
simulation (spec 0001, open question 1).

We still want doors to look like doors in Gazebo (a visible leaf) and to keep them in the building
file with their names, because the parser reports them and the stage 2 planner refers to them.

## Decision

1. Doors stay in the building file as RMF doors with `plugin: none` (static).
2. Our generator wrapper (ADR 0003) places each door leaf in its open position:
   - hinged: the leaf is turned by `motion_degrees` (90°) about its hinge, on the side given by
     `motion_direction`, so it stands perpendicular to the wall next to the opening;
   - sliding: the leaf is moved by its own width along the wall, beside the opening.
   A static model ignores its joints, so only the leaf's pose changes.
3. Doors are always open; there is no closed state in simulation.

A prototype on the spec 0001 fixture put the hinged leaf perpendicular to the wall in `room_b`;
in Gazebo the laser at the centre of `room_a` looked through the doorway (range beyond the
scanner's 3.5 m limit instead of about 1.98 m to a closed leaf), with no `[Err]` lines.

## Alternatives considered

- **Doorway as a gap, no leaf.** Equally passable and simpler, but the door is invisible in
  Gazebo, which makes worlds harder to check by eye. Rejected at the user's request.
- **Static closed doors (status quo).** Rooms are disconnected; navigation impossible.
- **Build `libdoor.so` from source.** Real opening and closing, but needs the RMF door
  supervisor and fleet adapter; RMF scheduling is out of scope.
- **Free-swinging leaf (not static, no plugin).** The robot could push it, but the leaf's
  position is unpredictable: the laser sees it as an obstacle and runs are not reproducible.

## Consequences

- Rooms are connected in simulation; Nav2 can plan through doorways.
- An open hinged leaf takes up space in one room (a 1 m door sweeps a 1 m strip along the wall).
  The occupancy map (ADR 0005) must include it, or Nav2 will plan into it.
- `inspect door is closed` style tasks (stage 2) cannot be simulated; doors only exist as
  targets and passages.
- The patch depends on `Door.generate_swing_section` / `generate_sliding_section` in 1.5.0;
  an integration test that looks through a doorway catches a change.
