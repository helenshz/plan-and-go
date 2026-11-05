# 0002. Parser outputs drawing pixels; the Writer converts to metres

- Status: accepted
- Date: 2026-11-05

## Context

The parser (VLM) reads a floor plan image and must report where walls, doors and rooms are.
Something has to turn positions on the drawing into positions in the world, in metres. Spec 0001
left open (question 3) whether the building file should keep drawing pixels plus a scale
measurement (`coordinate_system: reference_image`, the format `traffic_editor` writes) or be in
metres (`cartesian_meters`).

Forces:

- A VLM is good at pointing at things in an image and bad at arithmetic. Asking it to read
  dimensions and convert to metres mixes two error sources that we could not tell apart.
- The robot, Nav2, the stage 2 planner and any real-world use all work in metres. Metres also
  make the building file readable and its errors measurable in centimetres without knowing the
  drawing.
- The spec 0001 fixture is in `cartesian_meters` and its integration test passes; that path
  through `rmf_building_map_tools` is known to work.

## Decision

1. The parse result (the schema the parser fills in) uses **drawing pixel coordinates**, with
   the image's y axis pointing down, exactly as the VLM sees the image.
2. The parse result carries a **scale**: two pixel points and the real distance between them in
   metres, read from a dimension line or a scale bar.
3. The **Writer** (deterministic code) converts pixels to metres, flips the y axis and writes a
   building file with `coordinate_system: cartesian_meters`.

## Alternatives considered

- **VLM outputs metres directly.** Simplest Writer, but the VLM would do the scaling itself;
  scale and position errors could not be separated in the eval, and the self-critic could not
  check the scale on its own. Rejected.
- **Writer emits `reference_image` (pixels + `measurements`) and lets
  `building_map_generator` scale it.** Keeps the file overlayable on the drawing in
  `traffic_editor`, but the building file is then in pixels (unreadable without the drawing),
  the y flip and scaling are hidden inside an undocumented tool, and `traffic_editor` is not
  available in our conda env anyway. Rejected.

## Consequences

- Scale is one explicit, checkable number. The self-critic can compare it with other dimension
  labels; the eval can report scale error separately from position error.
- The building file is in metres and directly comparable with IFC-derived ground truth.
- The Writer owns the pixel → metre transform (scale, y flip, origin) and must be unit-tested.
- Generated files can no longer be overlaid on the drawing in `traffic_editor` as ADR 0001
  expected. If we need a visual check, we draw the parse result over the image ourselves
  (pixel coordinates are still in the parse result).
