"""building_map_generator with real wall thickness and open doors.

Usage (same arguments as the upstream tool; from the repo root, in the conda env):
    PYTHONPATH=src python -m plan_and_go.generate_world gazebo <building.yaml> <out.world> <model_dir>

Patches rmf_building_map_tools 1.5.0 in memory, then runs its generator unchanged:

- ADR 0003: walls with a `thickness` parameter [m] get that thickness instead of 0.1 m.
- ADR 0004: static doors (`plugin: none`) get their leaf in the open position.

The installed package is never modified.
"""

import sys

import building_map.level as _level
from building_map.doors.door import Door as _Door
from building_map.wall import Wall as _UpstreamWall

from plan_and_go.door_geometry import (
    open_slide_pose,
    open_swing_pose,
    slide_shift,
    swing_angle,
)


class ThickWall(_UpstreamWall):
    """One group of walls with identical parameters; reads their `thickness`."""

    def __init__(self, yaml_node, wall_params):
        super().__init__(yaml_node, wall_params)
        if 'thickness' in wall_params:
            self.wall_thickness = float(wall_params['thickness'].value)


_upstream_swing = _Door.generate_swing_section
_upstream_slide = _Door.generate_sliding_section


def _set_leaf_pose(door, name, pose):
    # A static model ignores joints, so the link pose alone decides where the leaf is.
    link = next(l for l in door.model_ele.findall('link') if l.get('name') == name)
    z = door.height / 2 + 0.01  # as in Door.generate_section
    link.find('pose').text = f'{pose.x} {pose.y} {z} 0 0 {pose.yaw}'


def _open_swing_section(self, name, width, x_offset, bounds, axis_pose, axis, options):
    _upstream_swing(self, name, width, x_offset, bounds, axis_pose, axis, options)
    if self.plugin == 'none':
        hinge_x = x_offset + axis_pose[0]
        _set_leaf_pose(self, name, open_swing_pose(x_offset, hinge_x, swing_angle(bounds, axis)))


def _open_sliding_section(self, name, width, x_offset, bounds, options):
    _upstream_slide(self, name, width, x_offset, bounds, options)
    if self.plugin == 'none':
        _set_leaf_pose(self, name, open_slide_pose(x_offset, slide_shift(bounds)))


def apply_patches():
    """Install the patches; safe to call more than once."""
    _level.Wall = ThickWall
    _Door.generate_swing_section = _open_swing_section
    _Door.generate_sliding_section = _open_sliding_section


def main(argv=None):
    from building_map_generator.building_map_generator import main as upstream_main

    apply_patches()
    if argv is not None:
        sys.argv = [sys.argv[0]] + list(argv)
    return upstream_main()


if __name__ == '__main__':
    sys.exit(main())
