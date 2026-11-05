# plan-and-go

Turns a floor plan into a simulated building that a robot can drive in. These terms describe the
building as the project sees it, independent of any one file format.

## Language

**Room**:
A named area of the building enclosed by walls and doors.
_Avoid_: Floor (in RMF a floor is only the polygon that represents a room's ground), space, zone

**Wall**:
A straight, solid segment with a thickness, given by its centre line between two points, that the
robot cannot pass.
_Avoid_: Edge, line

**Door**:
An opening in a wall through which the robot may pass between two rooms, whether or not it has a
door leaf.
_Avoid_: Gap, opening, portal

**Building file**:
The single description of one building's walls, doors and rooms from which the simulated world is
produced; the project's intermediate representation.
_Avoid_: Map, layout, yaml

**Floor plan**:
The input drawing (PDF or image) of one level of a building.
_Avoid_: Map, layout, image

**Parser**:
The VLM component that reads a floor plan and fills in a parse result.
_Avoid_: Detector, extractor

**Parse result**:
What the parser reports about one floor plan: walls, doors, rooms and the scale, in drawing pixels.
_Avoid_: Output, prediction, plan

**Scale**:
A known distance on the floor plan (two points and their real distance in metres), used to turn
pixels into metres.
_Avoid_: Measurement (RMF's name for it), ratio

**Writer**:
The deterministic code that turns a parse result into a building file.
_Avoid_: Generator (that is `building_map_generator`, which turns a building file into a world)

**World**:
The simulated building the robot is placed in.
_Avoid_: Scene, environment, map
