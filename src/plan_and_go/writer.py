"""Writer: parse result (drawing pixels) -> building file (metres).

Spec: docs/specs/0002-parse-result-and-writer.md. Deterministic; no LLM calls.
Errors are raised as WriterError subclasses whose message names the element, so the
self-critic can pass them back to the parser.
"""

import math
from pathlib import Path
from typing import List, Tuple, Union

import yaml
from shapely.geometry import MultiPoint

from plan_and_go.parse_result import ParseResult

XY = Tuple[float, float]

# rmf_building_map_tools parameter type codes
_STRING, _INT, _DOUBLE = 1, 2, 3

LEVEL = 'L1'
MIN_THICKNESS = 0.01  # [m]; thickness is rounded to 1 cm (ADR 0003)


class WriterError(ValueError):
    """The parse result cannot be turned into a consistent building file."""


class DoorNotOnWallError(WriterError):
    pass


def write_building(
    parse_result: ParseResult,
    building_name: str,
    merge_tol: float = 0.05,
    door_tol: float = 0.05,
) -> dict:
    """Return the building file for `parse_result` as a dict (see save_building)."""
    to_m, s = _pixel_to_metre(parse_result)

    walls = [
        (to_m(w.p1), to_m(w.p2), max(MIN_THICKNESS, round(w.thickness * s, 2)))
        for w in parse_result.walls
    ]
    doors = []
    for d in parse_result.doors:
        walls, a, b = _split_wall_at_door(walls, d.name, to_m(d.p1), to_m(d.p2),
                                          merge_tol, door_tol)
        doors.append((d.name, d.type, a, b))

    vertices = _VertexList(merge_tol)
    wall_edges = []
    for a, b, t in walls:
        i, j = vertices.add(a), vertices.add(b)
        if i != j:
            wall_edges.append([i, j, {'thickness': [_DOUBLE, t]}])

    door_edges = []
    for name, door_type, a, b in doors:
        door_edges.append([vertices.add(a), vertices.add(b), {
            'name': [_STRING, name],
            'type': [_STRING, door_type],
            'motion_degrees': [_DOUBLE, 90.0],
            'motion_direction': [_INT, 1],
            'plugin': [_STRING, 'none'],
        }])

    for room in parse_result.rooms:
        vertices.add_named(to_m(room.at), room.name)

    floor = _floor_polygon([p for a, b, _ in walls for p in (a, b)],
                           max(t for _, _, t in walls))
    floor_indices = [vertices.add_unmerged(p) for p in floor]

    return {
        'building_name': building_name,
        'coordinate_system': 'cartesian_meters',
        'levels': {
            LEVEL: {
                'elevation': 0.0,
                'vertices': vertices.to_yaml(),
                'walls': wall_edges,
                'doors': door_edges,
                'floors': [{'vertices': floor_indices, 'parameters': {}}],
            },
        },
    }


def save_building(building: dict, path: Union[str, Path]) -> None:
    """Write a building dict from write_building to a .building.yaml file."""
    with open(path, 'w') as f:
        yaml.safe_dump(building, f, sort_keys=False, default_flow_style=None)


def _pixel_to_metre(parse_result: ParseResult):
    """Pixel -> metre transform: scale, y flip, origin at the walls' lower-left corner."""
    sc = parse_result.scale
    s = sc.meters / math.hypot(sc.p2[0] - sc.p1[0], sc.p2[1] - sc.p1[1])
    xs = [p[0] for w in parse_result.walls for p in (w.p1, w.p2)]
    ys = [p[1] for w in parse_result.walls for p in (w.p1, w.p2)]
    x0, y1 = min(xs), max(ys)  # image y points down: the largest y is the bottom

    def to_m(p) -> XY:
        return ((p[0] - x0) * s, (y1 - p[1]) * s)

    return to_m, s


def _split_wall_at_door(walls, door_name, d1: XY, d2: XY, merge_tol, door_tol):
    """Replace the wall the door lies on by the pieces either side of it.

    Returns the new wall list and the door's endpoints projected onto that wall's centre line.
    """
    hits = []
    for idx, (a, b, t) in enumerate(walls):
        tol = max(door_tol, t / 2.0)
        proj = [_project(a, b, p) for p in (d1, d2)]
        length = _dist(a, b)
        if all(dist <= tol and -merge_tol <= u <= length + merge_tol for u, dist in proj):
            hits.append((max(dist for _, dist in proj), idx, proj))

    if not hits:
        raise DoorNotOnWallError(f'door {door_name} does not lie on any wall')
    if len(hits) > 1:
        raise WriterError(f'door {door_name} lies on {len(hits)} overlapping walls')

    _, idx, proj = hits[0]
    a, b, t = walls[idx]
    length = _dist(a, b)
    u1, u2 = sorted(min(max(u, 0.0), length) for u, _ in proj)
    p_u1, p_u2 = _along(a, b, u1), _along(a, b, u2)

    pieces = []
    if u1 >= merge_tol:
        pieces.append((a, p_u1, t))
    if length - u2 >= merge_tol:
        pieces.append((p_u2, b, t))
    new_walls = walls[:idx] + pieces + walls[idx + 1:]

    # Keep the door's own orientation (p1 -> p2): it decides which way the leaf opens.
    first_u = proj[0][0]
    return (new_walls, p_u1, p_u2) if first_u <= proj[1][0] else (new_walls, p_u2, p_u1)


def _floor_polygon(points: List[XY], max_thickness: float) -> List[XY]:
    """Convex hull of the wall centre lines, grown to reach under the outer wall faces."""
    hull = MultiPoint(points).convex_hull.buffer(max_thickness / 2.0, join_style=2)
    return [(float(x), float(y)) for x, y in list(hull.exterior.coords)[:-1]]


class _VertexList:
    """Building file vertices; points within merge_tol share a vertex."""

    def __init__(self, merge_tol: float):
        self.merge_tol = merge_tol
        self.points: List[XY] = []
        self.names: List[str] = []

    def add(self, p: XY) -> int:
        for i, q in enumerate(self.points):
            if self.names[i] == '' and _dist(p, q) < self.merge_tol:
                return i
        return self.add_unmerged(p)

    def add_unmerged(self, p: XY, name: str = '') -> int:
        self.points.append(p)
        self.names.append(name)
        return len(self.points) - 1

    def add_named(self, p: XY, name: str) -> int:
        return self.add_unmerged(p, name)

    def to_yaml(self) -> list:
        return [[round(x, 4), round(y, 4), 0.0, name]
                for (x, y), name in zip(self.points, self.names)]


def _dist(a: XY, b: XY) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _project(a: XY, b: XY, p: XY) -> Tuple[float, float]:
    """Position of p along a->b [m from a] and its distance from the line through a, b."""
    length = _dist(a, b)
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    px, py = p[0] - a[0], p[1] - a[1]
    return px * ux + py * uy, abs(px * uy - py * ux)


def _along(a: XY, b: XY, u: float) -> XY:
    length = _dist(a, b)
    return (a[0] + (b[0] - a[0]) * u / length, a[1] + (b[1] - a[1]) * u / length)
