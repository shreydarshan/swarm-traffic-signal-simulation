"""
test_simulation.py -- Automated test suite for the swarm traffic simulation.
Tests signal safety, vehicle compliance, swarm optimization, emergency
green-wave, and metrics accuracy.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
from models import Vehicle, Intersection
from signal_controller import SignalController
from swarm_controller import SwarmController
from emergency_controller import EmergencyController
from traffic_manager import TrafficManager
from metrics import MetricsEngine


def test_signal_state_machine():
    print("TEST: Signal State Machine")
    inter = Intersection(0, (200, 200), 0, 0)
    ctrl = SignalController()

    assert inter.signal_state == cfg.SIG_NS_GREEN
    assert inter.is_green_for('N')
    assert inter.is_red_for('E')

    t = 0.0
    states_seen = []
    prev_state = inter.signal_state
    for _ in range(5000):
        t += 0.1
        ctrl.update(inter, t)
        if inter.signal_state != prev_state:
            states_seen.append(cfg.SIGNAL_STATE_NAMES[inter.signal_state])
            prev_state = inter.signal_state
        if len(states_seen) >= 10:
            break

    expected_pattern = ["NS_YELLOW", "ALL_RED", "EW_GREEN", "EW_YELLOW", "ALL_RED"]
    for i, expected in enumerate(expected_pattern):
        assert states_seen[i] == expected, f"State {i} should be {expected}, got {states_seen[i]}"

    # Safety: never should NS and EW be green simultaneously
    t = 0.0
    inter2 = Intersection(0, (200, 200), 0, 0)
    for _ in range(10000):
        t += 0.05
        ctrl.update(inter2, t)
        ns_green = inter2.signal_state == cfg.SIG_NS_GREEN
        ew_green = inter2.signal_state == cfg.SIG_EW_GREEN
        assert not (ns_green and ew_green), "CONFLICT!"

    print("  [OK] FSM transitions correctly")
    print("  [OK] No conflicting greens in 10000 ticks")
    print("  PASSED\n")


def test_yellow_and_allred():
    print("TEST: Yellow and All-Red Duration")
    inter = Intersection(0, (200, 200), 0, 0)
    ctrl = SignalController()
    t = 0.0
    dt = 0.01

    while inter.signal_state != cfg.SIG_NS_YELLOW:
        t += dt
        ctrl.update(inter, t)
        if t > 100:
            assert False, "Never reached NS_YELLOW"

    yellow_start = t
    while inter.signal_state == cfg.SIG_NS_YELLOW:
        t += dt
        ctrl.update(inter, t)
    yellow_duration = t - yellow_start
    assert abs(yellow_duration - cfg.YELLOW_TIME) < 0.05

    assert inter.signal_state == cfg.SIG_ALL_RED_1
    allred_start = t
    while inter.signal_state == cfg.SIG_ALL_RED_1:
        t += dt
        ctrl.update(inter, t)
    allred_duration = t - allred_start
    assert abs(allred_duration - cfg.ALL_RED_TIME) < 0.05

    print(f"  [OK] Yellow: {yellow_duration:.2f}s (expected {cfg.YELLOW_TIME}s)")
    print(f"  [OK] All-red: {allred_duration:.2f}s (expected {cfg.ALL_RED_TIME}s)")
    print("  PASSED\n")


def test_vehicle_stops_at_red():
    print("TEST: Vehicle Stops at Red Light")
    world = TrafficManager()

    t = 0.0
    while world.intersections[0].signal_state != cfg.SIG_EW_GREEN:
        t += 0.05
        world.time = t
        for inter in world.intersections:
            world.signal_ctrl.update(inter, t)

    road_cols = world.get_road_columns()
    col_x = road_cols[0]
    v = world._get_vehicle()
    lane = col_x + cfg.LANE_OFFSET
    v.reset((lane, cfg.TOPBAR_HEIGHT + 10), 'S', 100, False, lane, t)
    world.vehicles.append(v)

    for _ in range(300):
        t += 1/60
        world.time = t
        for inter in world.intersections:
            world.signal_ctrl.update(inter, t)
        world._update_vehicles(1/60)

    assert v.speed < 15 or v.stopped, f"Vehicle should have stopped, speed={v.speed:.1f}"
    print(f"  [OK] Vehicle stopped at red (speed={v.speed:.1f})")
    print("  PASSED\n")


def test_swarm_optimization():
    print("TEST: Swarm/PSO Optimization")
    world = TrafficManager()

    initial_ns = [i.swarm_ns_green for i in world.intersections]
    for _ in range(20):
        world.spawn_vehicle()

    for _ in range(int(cfg.PSO_UPDATE_INTERVAL * 60 * 3)):
        world.update(1/60)

    assert world.swarm_ctrl.update_cycle > 0, "PSO should have run"

    changed = any(
        abs(inter.swarm_ns_green - initial_ns[i]) > 0.01
        for i, inter in enumerate(world.intersections)
    )
    assert changed, "PSO should modify timing"

    print(f"  [OK] PSO cycles: {world.swarm_ctrl.update_cycle}")
    print(f"  [OK] Best cost: {world.swarm_ctrl.get_best_cost():.2f}")
    print("  PASSED\n")


def test_emergency_green_wave():
    print("TEST: Emergency Green-Wave")
    world = TrafficManager()

    ev = world.spawn_vehicle(emergency=True, emergency_type="Ambulance")
    assert ev is not None
    assert ev.is_emergency

    for _ in range(600):
        world.update(1/60)
        if world.emergency_ctrl.get_active_event_count() > 0:
            break

    events = world.emergency_ctrl.get_active_events()
    assert len(events) > 0, "Should have active emergency events"

    event = events[0]
    assert event.green_wave_active
    assert len(event.preempted_intersections) > 0

    print(f"  [OK] Detection: {event.detection_method}")
    print(f"  [OK] Preempted: {len(event.preempted_intersections)} intersections")
    print("  PASSED\n")


def test_emergency_safe_preemption():
    print("TEST: Emergency Safe Preemption")
    inter = Intersection(0, (200, 200), 0, 0)
    inter.signal_state = cfg.SIG_EW_GREEN
    inter.state_start_time = 0.0
    ctrl = SignalController()

    ctrl.request_preemption(inter, 'NS', 1, 0.0)
    assert inter.preempt_active
    assert inter.signal_state != cfg.SIG_NS_GREEN

    t = 0.0
    states = [cfg.SIGNAL_STATE_NAMES[inter.signal_state]]
    for _ in range(2000):
        t += 0.01
        ctrl.update(inter, t)
        name = cfg.SIGNAL_STATE_NAMES[inter.signal_state]
        if name != states[-1]:
            states.append(name)
        if inter.signal_state == cfg.SIG_NS_GREEN:
            break

    assert inter.signal_state == cfg.SIG_NS_GREEN
    assert "EW_YELLOW" in states
    assert "ALL_RED" in states

    seq = " -> ".join(states)
    print(f"  [OK] Sequence: {seq}")
    print("  PASSED\n")


def test_metrics_accuracy():
    print("TEST: Metrics Accuracy")
    world = TrafficManager()

    for _ in range(3600):
        world.update(1/60)

    m = world.metrics
    assert m.total_spawned > 0
    assert m.active_vehicles >= 0
    assert m.total_completed >= 0

    print(f"  [OK] Spawned: {m.total_spawned}")
    print(f"  [OK] Avg wait: {m.avg_wait_time:.1f}s")
    print(f"  [OK] Throughput: {m.throughput:.0f}/min")
    print("  PASSED\n")


def test_intersection_coordination():
    print("TEST: Intersection Coordination (2x2)")
    world = TrafficManager()

    assert len(world.intersections) == 4, f"Should have 4, got {len(world.intersections)}"

    # Each corner of 2x2 has exactly 2 neighbours
    for inter in world.intersections:
        n = sum(1 for nb in inter.neighbours.values() if nb is not None)
        assert n == 2, f"I{inter.index+1} should have 2 neighbours, got {n}"

    print("  [OK] 4 intersections")
    print("  [OK] Each has 2 neighbours")
    print("  PASSED\n")


def test_traffic_scenarios():
    print("TEST: Traffic Scenarios")
    world = TrafficManager()

    for name, expected_interval in [("LOW", 2.0), ("NORMAL", 1.2), ("HIGH", 0.6), ("PEAK", 0.35)]:
        world.set_scenario(name)
        assert abs(world.spawn_interval - expected_interval) < 0.01

    print("  [OK] All scenarios work")
    print("  PASSED\n")


def test_reset():
    print("TEST: Reset")
    world = TrafficManager()
    for _ in range(600):
        world.update(1/60)

    world.reset()
    assert world.time == 0.0
    assert len(world.vehicles) == 0
    assert world.metrics.total_spawned == 0

    print("  [OK] Reset works")
    print("  PASSED\n")


def test_emergency_spawn_reliability():
    print("TEST: Emergency Spawn Reliability")
    world = TrafficManager()

    # Spawn 10 emergency vehicles in a row
    successes = 0
    for i in range(10):
        ev = world.spawn_vehicle(emergency=True)
        if ev is not None and ev.is_emergency:
            successes += 1

    assert successes == 10, f"Only {successes}/10 spawns succeeded"

    # All should be registered
    events = world.emergency_ctrl.active_events
    assert len(events) >= 10, f"Only {len(events)}/10 registered"

    print(f"  [OK] 10/10 emergency spawns succeeded")
    print(f"  [OK] {len(events)} events registered")
    print("  PASSED\n")


def test_emergency_vehicle_speed():
    print("TEST: Emergency Vehicle Speed")
    world = TrafficManager()

    ev = world.spawn_vehicle(emergency=True)
    normal = world.spawn_vehicle()

    assert ev.max_speed > normal.max_speed * 1.1, \
        f"Emergency speed {ev.max_speed:.0f} should be >> normal {normal.max_speed:.0f}"

    print(f"  [OK] Emergency speed: {ev.max_speed:.0f} vs normal: {normal.max_speed:.0f}")
    print("  PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("SWARM TRAFFIC SIMULATION -- TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_signal_state_machine,
        test_yellow_and_allred,
        test_vehicle_stops_at_red,
        test_swarm_optimization,
        test_emergency_green_wave,
        test_emergency_safe_preemption,
        test_metrics_accuracy,
        test_intersection_coordination,
        test_traffic_scenarios,
        test_reset,
        test_emergency_spawn_reliability,
        test_emergency_vehicle_speed,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL]: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR]: {e}")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
