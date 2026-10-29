# plan-and-go

Turns a floor plan into a simulated building that a robot can drive in. These terms describe the
building as the project sees it, independent of any one file format.

## Language

**Room**:
A named area of the building enclosed by walls and doors.
_Avoid_: Floor (in RMF a floor is only the polygon that represents a room's ground), space, zone

**Wall**:
A straight, solid segment between two points that the robot cannot pass.
_Avoid_: Edge, line

**Door**:
An opening in a wall through which the robot may pass between two rooms, whether or not it has a
door leaf.
_Avoid_: Gap, opening, portal

**Building file**:
The single description of one building's walls, doors and rooms from which the simulated world is
produced; the project's intermediate representation.
_Avoid_: Map, layout, yaml

**World**:
The simulated building the robot is placed in.
_Avoid_: Scene, environment, map
