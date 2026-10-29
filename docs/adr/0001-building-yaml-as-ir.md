# 0001. LLMs output structured data only; `.building.yaml` is the intermediate representation

- Status: accepted
- Date: 2026-10-29

## Context

The pipeline turns a floor plan image into a Gazebo world, and later a text instruction into
robot motion. A VLM is needed to read the drawing (walls, doors, room names, dimensions) and an
LLM to understand instructions. But LLMs are unreliable at exact geometry and at producing long,
syntactically strict formats such as SDF: coordinates drift, elements get hallucinated, and the
output is hard to check.

Open-RMF's `.building.yaml` is what a human produces today by tracing a floor plan in
`traffic_editor`. It is small (vertices in image pixels, walls and doors as vertex pairs, a scale
measurement), and `rmf_building_map_tools` already converts it to a Gazebo/Ignition world.

## Decision

1. LLM/VLM components produce only structured data validated against a schema:
   - the parser agent outputs vertices, walls, doors, room names and a scale measurement;
   - the task planner outputs a JSON plan from a fixed action set (`navigate`, `inspect`, ...)
     whose targets must exist in the map.
2. `.building.yaml` is the intermediate representation between perception and simulation.
3. Everything else is deterministic code: schema validation, geometric checks for the
   self-critic (closure, doors on walls, connectivity, dimension error), YAML writing,
   world generation (`building_map_generator`), name → pose lookup and Nav2 execution.

## Alternatives considered

- **LLM writes SDF/world files directly.** Long, strict XML with many coupled numbers;
  errors only show up in Gazebo and are hard to attribute. Rejected.
- **Custom JSON IR plus own SDF generator.** Full control, but re-implements what
  `rmf_building_map_tools` already does, and loses `traffic_editor` as a viewer/editor.
- **Pixel extrusion (linorobot2 `world_creator`).** No semantics (no doors or room names), text
  and dimension lines become walls. Kept as an eval baseline only.
- **IFC → mesh → Gazebo.** Needs a BIM model; the project targets plain drawings. Used as an
  upper bound / ground truth source in the eval.

## Consequences

- Every LLM output can be checked by code and unit-tested without calling a model; the
  self-critic loop gets precise error messages to feed back to the parser.
- Generated files open in `traffic_editor` on top of the drawing, so errors are visible and a
  corrected file serves directly as ground truth.
- Parser errors can be measured per element (walls/doors precision–recall, dimension error)
  instead of only "does the world look right".
- We depend on the `.building.yaml` schema, which is not formally documented: its fields must
  be taken from the `rmf_building_map_tools` source and pinned in our own schema/model.
- Anything the format cannot express (curved walls, stairs, furniture) is out of scope unless
  a later ADR extends the IR.
