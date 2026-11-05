"""Shared helpers for integration tests that run Gazebo with launch/sim.launch.py."""

import math
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
LAUNCH_FILE = REPO / 'launch' / 'sim.launch.py'

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def write_and_generate(parse_fixture, out_dir, building_name):
    """Parse result fixture -> Writer -> generate_world.

    Returns (CompletedProcess of the generator, world path, model dir).
    """
    from plan_and_go.parse_result import ParseResult
    from plan_and_go.writer import save_building, write_building

    out_dir = Path(out_dir)
    building_file = out_dir / f'{building_name}.building.yaml'
    world = out_dir / f'{building_name}.world'
    model_dir = out_dir / 'models'

    parse_result = ParseResult.model_validate(yaml.safe_load(Path(parse_fixture).read_text()))
    save_building(write_building(parse_result, building_name), building_file)

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(REPO / 'src'),
                                                      env.get('PYTHONPATH')]))
    result = subprocess.run(
        [sys.executable, '-m', 'plan_and_go.generate_world', 'gazebo',
         str(building_file), str(world), str(model_dir)],
        capture_output=True, text=True, timeout=120, env=env,
    )
    return result, world, model_dir


def run_sim(world, model_dir, x, y, log_path, domain_id, gazebo_port, n_scans=5, timeout=90.0):
    """Launch headless Gazebo with the robot at (x, y); return (last LaserScan or None, log)."""
    env = dict(os.environ)
    env.pop('TURTLEBOT3_MODEL', None)  # exercise the launch file's default
    env['ROS_DOMAIN_ID'] = str(domain_id)
    env['GAZEBO_MASTER_URI'] = f'http://localhost:{gazebo_port}'

    with open(log_path, 'w') as log:
        proc = subprocess.Popen(
            ['ros2', 'launch', str(LAUNCH_FILE),
             f'world:={world}', f'model_dir:={model_dir}',
             f'x:={x}', f'y:={y}', 'gui:=false'],
            env=env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,  # own process group, so we can stop gzserver too
        )
        try:
            scan = _wait_for_scan(domain_id, n_scans, timeout)
        finally:
            _stop(proc)

    return scan, ANSI.sub('', Path(log_path).read_text())


def err_lines(log):
    return [line for line in log.splitlines() if '[Err]' in line]


def valid_ranges(scan):
    return [r for r in scan.ranges if math.isfinite(r) and scan.range_min <= r <= scan.range_max]


def ranges_around(scan, degrees, half_width_deg):
    """Raw ranges (inf = no return) of the rays within half_width_deg of the given angle."""
    out = []
    for i, r in enumerate(scan.ranges):
        angle = math.degrees(scan.angle_min + i * scan.angle_increment)
        diff = (angle - degrees + 180.0) % 360.0 - 180.0
        if abs(diff) <= half_width_deg:
            out.append(r)
    return out


def _wait_for_scan(domain_id, n_scans, timeout):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan

    rclpy.init(domain_id=domain_id)
    node = rclpy.create_node('integration_test_scan_probe')
    scans = []
    node.create_subscription(LaserScan, '/scan', scans.append, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + timeout
        # Skip the first few scans: the robot drops 1 cm onto the floor after spawning.
        while len(scans) < n_scans and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
        return scans[-1] if scans else None
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _stop(proc):
    if proc.poll() is not None:
        return
    pgid = os.getpgid(proc.pid)
    os.killpg(pgid, signal.SIGINT)
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(pgid, signal.SIGKILL)
        proc.wait()
