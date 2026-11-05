"""Spec 0002 acceptance criteria 1-4: the Writer."""

from pathlib import Path

import pytest
import yaml

from plan_and_go.parse_result import ParseResult
from plan_and_go.writer import DoorNotOnWallError, save_building, write_building

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'


def _level(building):
    return building['levels']['L1']


def _xy(level, idx):
    return tuple(level['vertices'][idx][:2])


def _segments(level, key):
    """Edges as sets of endpoint coordinates, rounded to 1 mm, with their params."""
    return [
        (frozenset({tuple(round(c, 3) for c in _xy(level, i)),
                    tuple(round(c, 3) for c in _xy(level, j))}), params)
        for i, j, params in level[key]
    ]


def _seg(a, b):
    return frozenset({a, b})


def _parse(walls, doors=(), rooms=(), px_per_m=100.0):
    return ParseResult.model_validate({
        'scale': {'p1': [0, 0], 'p2': [px_per_m, 0], 'meters': 1.0},
        'walls': list(walls), 'doors': list(doors), 'rooms': list(rooms),
    })


# --- criterion 1: the spec 0001 layout from pixels -------------------------------------------

@pytest.fixture(scope='module')
def two_rooms():
    data = yaml.safe_load((FIXTURES / 'two_rooms.parse.yaml').read_text())
    return write_building(ParseResult.model_validate(data), 'two_rooms')


def test_two_rooms_header(two_rooms):
    assert two_rooms['coordinate_system'] == 'cartesian_meters'
    assert list(two_rooms['levels']) == ['L1']


def test_two_rooms_walls_in_metres(two_rooms):
    walls = {seg: params['thickness'][1] for seg, params in _segments(_level(two_rooms), 'walls')}
    assert walls == {
        _seg((0.0, 0.0), (8.0, 0.0)): 0.1,
        _seg((8.0, 0.0), (8.0, 5.0)): 0.1,
        _seg((8.0, 5.0), (0.0, 5.0)): 0.1,
        _seg((0.0, 5.0), (0.0, 0.0)): 0.5,
        # shared wall, split around the door
        _seg((4.0, 0.0), (4.0, 2.0)): 0.1,
        _seg((4.0, 3.0), (4.0, 5.0)): 0.1,
    }


def test_two_rooms_door(two_rooms):
    level = _level(two_rooms)
    [(i, j, params)] = level['doors']
    # orientation kept: p1 (500, 500) px -> (4, 2) m is the start vertex
    assert _xy(level, i) == pytest.approx((4.0, 2.0), abs=1e-3)
    assert _xy(level, j) == pytest.approx((4.0, 3.0), abs=1e-3)
    assert params['name'] == [1, 'door_ab']
    assert params['type'] == [1, 'hinged']
    assert params['plugin'] == [1, 'none']


def test_two_rooms_room_vertices(two_rooms):
    level = _level(two_rooms)
    named = {v[3]: tuple(v[:2]) for v in level['vertices'] if v[3]}
    assert named == {'room_a': pytest.approx((2.0, 2.5)), 'room_b': pytest.approx((6.0, 2.5))}


def test_two_rooms_floor_reaches_outer_wall_faces(two_rooms):
    level = _level(two_rooms)
    [floor] = level['floors']
    pts = [_xy(level, i) for i in floor['vertices']]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    # hull of the centre lines grown by half the thickest wall (0.25 m)
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((-0.25, 8.25, -0.25, 5.25))


def test_saved_file_round_trips(two_rooms, tmp_path):
    path = tmp_path / 'two_rooms.building.yaml'
    save_building(two_rooms, path)
    assert yaml.safe_load(path.read_text()) == two_rooms


# --- criterion 2: merging endpoints ----------------------------------------------------------

def test_endpoints_within_merge_tol_share_a_vertex():
    # 3 px = 3 cm apart at 100 px/m, below the 5 cm default
    building = write_building(_parse([
        {'p1': [0, 0], 'p2': [100, 0], 'thickness': 10},
        {'p1': [103, 0], 'p2': [103, 100], 'thickness': 10},
    ]), 'b')
    level = _level(building)
    (_, end_a, _), (start_b, _, _) = level['walls']
    assert end_a == start_b


def test_endpoints_beyond_merge_tol_stay_apart():
    # 8 px = 8 cm apart
    building = write_building(_parse([
        {'p1': [0, 0], 'p2': [100, 0], 'thickness': 10},
        {'p1': [108, 0], 'p2': [108, 100], 'thickness': 10},
    ]), 'b')
    (_, end_a, _), (start_b, _, _) = _level(building)['walls']
    assert end_a != start_b


# --- criterion 3: splitting walls at doors ---------------------------------------------------

def test_door_in_middle_of_wall_leaves_two_pieces():
    building = write_building(_parse(
        [{'p1': [0, 0], 'p2': [400, 0], 'thickness': 10}],
        doors=[{'name': 'd', 'p1': [150, 0], 'p2': [250, 0]}],
    ), 'b')
    walls = {seg for seg, _ in _segments(_level(building), 'walls')}
    assert walls == {_seg((0.0, 0.0), (1.5, 0.0)), _seg((2.5, 0.0), (4.0, 0.0))}


def test_door_at_end_of_wall_leaves_one_piece():
    building = write_building(_parse(
        [{'p1': [0, 0], 'p2': [400, 0], 'thickness': 10}],
        doors=[{'name': 'd', 'p1': [300, 0], 'p2': [400, 0]}],
    ), 'b')
    walls = {seg for seg, _ in _segments(_level(building), 'walls')}
    assert walls == {_seg((0.0, 0.0), (3.0, 0.0))}


def test_door_drawn_on_face_of_thick_wall_is_projected_to_centre_line():
    # 40 px (0.4 m) thick wall; door drawn on its face, 18 px off the centre line
    building = write_building(_parse(
        [{'p1': [0, 0], 'p2': [400, 0], 'thickness': 40}],
        doors=[{'name': 'd', 'p1': [150, 18], 'p2': [250, 18]}],
    ), 'b')
    level = _level(building)
    [(i, j, _)] = level['doors']
    assert [_xy(level, i)[1], _xy(level, j)[1]] == pytest.approx([0.0, 0.0])


# --- criterion 4: door not on any wall --------------------------------------------------------

def test_door_off_wall_raises_with_name():
    with pytest.raises(DoorNotOnWallError, match='door_kitchen'):
        write_building(_parse(
            [{'p1': [0, 0], 'p2': [400, 0], 'thickness': 10}],
            doors=[{'name': 'door_kitchen', 'p1': [150, 50], 'p2': [250, 50]}],
        ), 'b')


def test_door_beyond_wall_end_raises():
    with pytest.raises(DoorNotOnWallError):
        write_building(_parse(
            [{'p1': [0, 0], 'p2': [400, 0], 'thickness': 10}],
            doors=[{'name': 'd', 'p1': [380, 0], 'p2': [480, 0]}],
        ), 'b')
