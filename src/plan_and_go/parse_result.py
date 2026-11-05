"""Parse result: what the parser reports about one floor plan.

Spec: docs/specs/0002-parse-result-and-writer.md. All coordinates are drawing pixels
[x, y] with y pointing down (ADR 0002). The Writer turns this into a building file.
"""

import math
from typing import List, Literal, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

Point = Tuple[float, float]

# Names become Gazebo model names and, in stage 2, planner targets.
NAME_PATTERN = r'^[A-Za-z0-9_]+$'


def _length(p1: Point, p2: Point) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


class _Strict(BaseModel):
    # Reject fields the parser invents instead of silently dropping them.
    model_config = ConfigDict(extra='forbid')


class Scale(_Strict):
    """A known distance on the drawing, e.g. a dimension line or a scale bar."""

    p1: Point = Field(description='One end of the known distance [px]')
    p2: Point = Field(description='Other end of the known distance [px]')
    meters: float = Field(gt=0, description='Real distance between p1 and p2 [m]')

    @model_validator(mode='after')
    def _distinct_points(self):
        if _length(self.p1, self.p2) == 0:
            raise ValueError('scale p1 and p2 must differ')
        return self


class Wall(_Strict):
    """A straight wall: its centre line and thickness."""

    p1: Point = Field(description='Start of the centre line [px]')
    p2: Point = Field(description='End of the centre line [px]')
    thickness: float = Field(gt=0, description='Wall thickness [px]')

    @model_validator(mode='after')
    def _nonzero_length(self):
        if _length(self.p1, self.p2) == 0:
            raise ValueError(f'wall {self.p1}-{self.p2} has zero length')
        return self


class Door(_Strict):
    """An opening in a wall, given by the two ends of the opening."""

    name: str = Field(pattern=NAME_PATTERN, description='Unique name, e.g. door_1')
    p1: Point = Field(description='One end of the opening [px]')
    p2: Point = Field(description='Other end of the opening [px]')
    type: Literal['hinged', 'sliding'] = 'hinged'

    @model_validator(mode='after')
    def _nonzero_length(self):
        if _length(self.p1, self.p2) == 0:
            raise ValueError(f'door {self.name} has zero length')
        return self


class Room(_Strict):
    """A named room, located by one point inside it."""

    name: str = Field(pattern=NAME_PATTERN, description='Unique name, e.g. kitchen')
    at: Point = Field(description='A point inside the room, e.g. where its name is printed [px]')


class ParseResult(_Strict):
    """Walls, doors, rooms and scale of one floor plan, in drawing pixels."""

    scale: Scale
    walls: List[Wall] = Field(min_length=1)
    doors: List[Door] = Field(default_factory=list)
    rooms: List[Room] = Field(default_factory=list)

    @model_validator(mode='after')
    def _unique_names(self):
        names = [d.name for d in self.doors] + [r.name for r in self.rooms]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f'names must be unique across doors and rooms: {duplicates}')
        return self
