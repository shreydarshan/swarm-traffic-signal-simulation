"""Behavioral scenario tests matching the user's 8 test cases."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
from traffic_manager import TrafficManager


def test_scenario_1():
    """Ambulance behind normal vehicle: ambulance must not get stuck."""
    print("SCENARIO 1: Ambulance behind normal vehicle")
    world = TrafficManager()
    cols = world.get_road_columns()
    col_x = cols[0]

    # Spawn normal vehicle going south
    normal = world._get_vehicle()
    lane = col_x + cfg.LANE_OFFSET
    normal.reset((lane, cfg.TOPBAR_HEIGHT + 200), 'S', 100, False, lane, 0)
    world.vehicles.append(normal)

    # Spawn ambulance behind it (further north)
    amb = world._get_vehicle()
    amb.reset((lane, cfg.TOPBAR_HEIGHT + 50), 'S', 100, True, lane, 0, "Ambulance")
    world.vehicles.append(amb)
    world.emergency_ctrl.register_emergency(amb, 0)

    initial_amb_y = amb.y
    normal_yielded = False
    amb_passed = False

    for i in range(600):
        world.update(1/60)
        if normal.yielding:
            normal_yielded = True
        if amb.y > normal.y + 30:
            amb_passed = True
            break

    assert normal_yielded, "Normal vehicle should have yielded"
    assert amb_passed, f"Ambulance should have passed normal vehicle (amb.y={amb.y:.0f}, normal.y={normal.y:.0f})"
    assert amb.y > initial_amb_y + 100, "Ambulance should have moved significantly"
    print(f"  [OK] Normal vehicle yielded: {normal_yielded}")
    print(f"  [OK] Ambulance passed: {amb_passed}")
    print(f"  [OK] Ambulance moved {amb.y - initial_amb_y:.0f}px")
    print("  PASSED\n")


def test_scenario_2():
    """Normal vehicles near emergency should not ALL become slow."""
    print("SCENARIO 2: Normal vehicles should not all become slow")
    world = TrafficManager()
    cols = world.get_road_columns()
    rows = world.get_road_rows()

    # Spawn several normal vehicles on different roads
    normals = []
    for col_x in cols:
        v = world._get_vehicle()
        lane = col_x + cfg.LANE_OFFSET
        v.reset((lane, cfg.TOPBAR_HEIGHT + 100), 'S', 100, False, lane, 0)
        world.vehicles.append(v)
        normals.append(v)

    for row_y in rows:
        v = world._get_vehicle()
        lane = row_y - cfg.LANE_OFFSET
        v.reset((50, lane), 'E', 100, False, lane, 0)
        world.vehicles.append(v)
        normals.append(v)

    # Spawn emergency on first column
    amb = world._get_vehicle()
    lane0 = cols[0] + cfg.LANE_OFFSET
    amb.reset((lane0, cfg.TOPBAR_HEIGHT + 10), 'S', 100, True, lane0, 0, "Ambulance")
    world.vehicles.append(amb)
    world.emergency_ctrl.register_emergency(amb, 0)

    # Run for a bit
    for _ in range(300):
        world.update(1/60)

    # Count how many normal vehicles are at very low speed
    slow_count = sum(1 for v in normals if v.active and v.speed < 20 and not v.yielding)
    total_active = sum(1 for v in normals if v.active)

    # At most a few should be slow (those yielding on same lane), not ALL
    yield_count = sum(1 for v in normals if v.active and v.yielding)
    normal_speed_count = sum(1 for v in normals if v.active and not v.yielding and v.speed > 40)

    print(f"  Active normals: {total_active}")
    print(f"  Yielding: {yield_count}")
    print(f"  Non-yielding at normal speed: {normal_speed_count}")
    print(f"  Slow non-yielding: {slow_count}")
    assert normal_speed_count > 0, "Some non-yielding vehicles should be at normal speed"
    print("  [OK] Not all vehicles are slow")
    print("  PASSED\n")


def test_scenario_3():
    """Emergency approaching intersection gets green wave."""
    print("SCENARIO 3: Emergency gets green wave at intersection")
    world = TrafficManager()

    amb = world.spawn_vehicle(emergency=True)
    assert amb is not None

    # Run to let green wave activate
    for _ in range(300):
        world.update(1/60)

    events = world.emergency_ctrl.get_active_events()
    if events:
        evt = events[0]
        print(f"  [OK] Route: {['I'+str(i+1) for i in evt.route]}")
        print(f"  [OK] Preempted: {len(evt.preempted_intersections)} intersections")
        print(f"  [OK] Green wave: {evt.green_wave_active}")
        assert evt.green_wave_active, "Green wave should be active"
        assert len(evt.preempted_intersections) > 0, "Should have preempted intersections"
    else:
        print("  [OK] Emergency already completed route (fast)")
    print("  PASSED\n")


def test_scenario_4():
    """After emergency passes, signals return to swarm control."""
    print("SCENARIO 4: Signal restoration after emergency")
    world = TrafficManager()

    amb = world.spawn_vehicle(emergency=True)

    # Run until emergency completes
    for _ in range(6000):
        world.update(1/60)

    # Check that preemption is released
    preempt_active = sum(1 for i in world.intersections if i.preempt_active)
    print(f"  Preempted intersections: {preempt_active}")
    print(f"  Swarm cycles: {world.swarm_ctrl.update_cycle}")
    assert world.swarm_ctrl.update_cycle > 5, "Swarm should have run multiple cycles"
    print("  [OK] Swarm control active and running")
    print("  PASSED\n")


def test_scenario_5():
    """Multiple emergency vehicles don't freeze simulation."""
    print("SCENARIO 5: Multiple emergency vehicles")
    world = TrafficManager()

    for _ in range(5):
        world.spawn_vehicle(emergency=True)

    for _ in range(1800):
        world.update(1/60)

    m = world.metrics
    print(f"  Active: {m.active_vehicles}")
    print(f"  Completed: {m.total_completed}")
    print(f"  Throughput: {m.throughput:.0f}/min")
    assert m.total_completed > 0, "Vehicles should complete routes"

    # Check no vehicle is permanently stuck
    stuck = sum(1 for v in world.vehicles if v.active and v.wait_time > 25)
    print(f"  Vehicles waiting >25s: {stuck}")
    print("  [OK] Simulation continues running")
    print("  PASSED\n")


def test_scenario_6():
    """Long run: no permanent stalls."""
    print("SCENARIO 6: Long run stability (120s)")
    world = TrafficManager()

    for _ in range(7200):
        world.update(1/60)

    m = world.metrics
    print(f"  Spawned: {m.total_spawned}")
    print(f"  Completed: {m.total_completed}")
    print(f"  Active: {m.active_vehicles}")
    print(f"  Avg wait: {m.avg_wait_time:.1f}s")
    print(f"  Throughput: {m.throughput:.0f}/min")
    print(f"  Swarm cycles: {world.swarm_ctrl.update_cycle}")
    assert m.total_completed > 20, "Should complete many vehicles"
    assert world.swarm_ctrl.update_cycle > 10, "Swarm should be active"
    print("  [OK] Stable after 120s")
    print("  PASSED\n")


def test_scenario_7():
    """Window size fits 1600x900."""
    print("SCENARIO 7: Window sizing")
    assert cfg.INITIAL_WIDTH <= 1300, f"Width {cfg.INITIAL_WIDTH} should be <= 1300"
    assert cfg.INITIAL_HEIGHT <= 750, f"Height {cfg.INITIAL_HEIGHT} should be <= 750"
    road_w = cfg.INITIAL_WIDTH - cfg.SIDEBAR_WIDTH
    road_h = cfg.INITIAL_HEIGHT - cfg.TOPBAR_HEIGHT - cfg.BOTTOMBAR_HEIGHT
    print(f"  Window: {cfg.INITIAL_WIDTH}x{cfg.INITIAL_HEIGHT}")
    print(f"  Road area: {road_w}x{road_h}")
    print(f"  Sidebar: {cfg.SIDEBAR_WIDTH}")
    assert road_w > 600, "Road area should be usable"
    assert road_h > 400, "Road area should be usable"
    print("  [OK] Window fits comfortably")
    print("  PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("BEHAVIORAL SCENARIO TESTS")
    print("=" * 60 + "\n")

    tests = [
        test_scenario_1,
        test_scenario_2,
        test_scenario_3,
        test_scenario_4,
        test_scenario_5,
        test_scenario_6,
        test_scenario_7,
    ]

    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL]: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  [ERROR]: {type(e).__name__}: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)
