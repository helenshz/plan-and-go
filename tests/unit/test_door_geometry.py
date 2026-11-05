"""Spec 0002 acceptance criterion 7: open door leaf pose (ADR 0004)."""

import math

import pytest

from plan_and_go.door_geometry import open_leaves, open_slide_pose, open_swing_pose

UPSTREAM_90_DEG = 3.14 / 2  # rmf_building_map_tools uses 3.14 for pi


def test_swing_leaf_is_perpendicular_with_one_end_at_hinge():
    # 1 m door, closed leaf centred at 0, hinge at +0.5; turned by -90 deg
    pose = open_swing_pose(0.0, 0.5, -math.pi / 2)
    assert (pose.x, pose.y, pose.yaw) == pytest.approx((0.5, 0.5, -math.pi / 2), abs=1e-3)
    # the leaf's two ends: hinge end stays at the hinge
    half = 0.5
    ends = [(pose.x + k * half * math.cos(pose.yaw), pose.y + k * half * math.sin(pose.yaw))
            for k in (-1, 1)]
    assert any(e == pytest.approx((0.5, 0.0), abs=1e-3) for e in ends)


def test_sliding_leaf_is_shifted_by_its_width():
    pose = open_slide_pose(0.0, 1.0)
    assert (pose.x, pose.y, pose.yaw) == pytest.approx((1.0, 0.0, 0.0), abs=1e-3)


def test_open_leaves_hinged_door_in_world_frame():
    # spec 0001 door: (4, 2) -> (4, 3); the leaf opens into room_b (x > 4) at the y = 2 end
    [leaf] = open_leaves((4.0, 2.0), (4.0, 3.0), 'hinged')
    assert (leaf.x, leaf.y) == pytest.approx((4.5, 2.0), abs=2e-3)
    assert abs(math.cos(leaf.yaw)) == pytest.approx(1.0, abs=1e-3)  # leaf runs along x
    assert leaf.width == pytest.approx(0.99)


def test_open_leaves_motion_direction_picks_the_other_room():
    [leaf] = open_leaves((4.0, 2.0), (4.0, 3.0), 'hinged', motion_direction=-1)
    assert leaf.x == pytest.approx(3.5, abs=2e-3)


def test_open_leaves_sliding_door_slides_along_wall():
    [leaf] = open_leaves((4.0, 2.0), (4.0, 3.0), 'sliding')
    # door frame x points from end (4, 3) to start (4, 2): the leaf moves to y = 1.5
    assert (leaf.x, leaf.y) == pytest.approx((4.0, 1.5), abs=1e-3)


def test_open_leaves_matches_upstream_angle():
    [leaf] = open_leaves((0.0, 0.0), (1.0, 0.0), 'hinged')
    door_yaw = math.pi  # from end (1, 0) to start (0, 0)
    assert leaf.yaw == pytest.approx(door_yaw - UPSTREAM_90_DEG)
