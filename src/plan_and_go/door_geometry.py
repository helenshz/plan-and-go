"""Where an open door leaf sits (ADR 0004).

One source of truth for the open leaf pose, used by the generator wrapper
(generate_world.py) and later by the occupancy map (ADR 0005). The geometry mirrors
rmf_building_map_tools 1.5.0 (building_map/doors/*.py):

- door frame: origin at the middle of the opening, x along the opening pointing from the
  door's end vertex to its start vertex, yaw = atan2(y1 - y2, x1 - x2);
- leaf: a box of width `length - 0.01` and thickness 0.03 m, centred at x_offset (0 for single
  doors) when closed;
- hinged: hinge at the leaf's +x end, turned by motion_degrees (upstream uses 3.14, not pi);
  motion_direction > 0 means axis -z, i.e. a negative angle;
- sliding: the leaf moves along +x by up to `length`.
"""

import math
from typing import List, NamedTuple, Sequence, Tuple

LEAF_THICKNESS = 0.03  # Door.thickness in rmf_building_map_tools
LEAF_GAP = 0.01  # leaf width = opening length - LEAF_GAP


class Pose2D(NamedTuple):
    x: float
    y: float
    yaw: float


class Leaf(NamedTuple):
    """An open door leaf in the world frame: centre, yaw and box size [m]."""

    x: float
    y: float
    yaw: float
    width: float
    thickness: float = LEAF_THICKNESS


def open_swing_pose(x_offset: float, hinge_x: float, theta: float) -> Pose2D:
    """Centre of a swing leaf turned by theta [rad] about a hinge at (hinge_x, 0), door frame."""
    dx = x_offset - hinge_x
    return Pose2D(hinge_x + math.cos(theta) * dx, math.sin(theta) * dx, theta)


def open_slide_pose(x_offset: float, shift: float) -> Pose2D:
    """Centre of a sliding leaf moved by shift [m] along the door's x axis, door frame."""
    return Pose2D(x_offset + shift, 0.0, 0.0)


def swing_angle(bounds: Tuple[float, float], axis: str) -> float:
    """Open angle [rad] from an upstream swing section's joint bounds and axis."""
    theta = bounds[1] if bounds[1] != 0 else bounds[0]
    return -theta if axis == '-z' else theta


def slide_shift(bounds: Tuple[float, float]) -> float:
    """Open shift [m] from an upstream sliding section's joint bounds."""
    return bounds[1] if bounds[1] != 0 else bounds[0]


def open_leaves(
    p1: Sequence[float],
    p2: Sequence[float],
    door_type: str,
    motion_degrees: float = 90.0,
    motion_direction: int = 1,
) -> List[Leaf]:
    """Open leaves, in the world frame, of a door from vertex p1 (start) to p2 (end) [m]."""
    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    cx, cy = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
    door_yaw = math.atan2(p1[1] - p2[1], p1[0] - p2[0])
    width = length - LEAF_GAP

    if door_type == 'hinged':
        bounds = (0.0, 3.14 * motion_degrees / 180.0)
        axis = 'z' if motion_direction < 0 else '-z'
        local = open_swing_pose(0.0, length / 2.0, swing_angle(bounds, axis))
    elif door_type == 'sliding':
        local = open_slide_pose(0.0, slide_shift((0.0, length)))
    else:
        raise ValueError(f'unsupported door type: {door_type}')

    c, s = math.cos(door_yaw), math.sin(door_yaw)
    return [Leaf(
        cx + c * local.x - s * local.y,
        cy + s * local.x + c * local.y,
        door_yaw + local.yaw,
        width,
    )]
