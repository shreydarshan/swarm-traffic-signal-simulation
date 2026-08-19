"""
traffic_manager.py — World simulation: road network, vehicle spawning,
car-following, signal compliance, and coordination.

2x2 grid, emergency vehicles get true priority (skip red signals,
other vehicles yield), improved spawning reliability.
"""

import random
import math
import config as cfg
from models import Vehicle, Intersection
from signal_controller import SignalController
from swarm_controller import SwarmController
from emergency_controller import EmergencyController
from metrics import MetricsEngine


class TrafficManager:
    """
    The simulation world. Manages the road network, vehicles, and
    orchestrates all controllers.
    """

    def __init__(self):
        self.time = 0.0
        self.paused = False
        self.speed_multiplier = cfg.SPEED_OPTIONS[cfg.DEFAULT_SPEED_INDEX]
        self.scenario = cfg.DEFAULT_SCENARIO

        # ── Build road network ──────────────────────────────────────
        self.intersections = []
        self.grid = {}

        self._road_area_w = cfg.INITIAL_WIDTH - cfg.SIDEBAR_WIDTH
        self._road_area_h = cfg.INITIAL_HEIGHT - cfg.TOPBAR_HEIGHT - cfg.BOTTOMBAR_HEIGHT

        self._build_network()

        # ── Controllers ─────────────────────────────────────────────
        self.signal_ctrl = SignalController()
        self.swarm_ctrl = SwarmController(self.intersections)
        self.emergency_ctrl = EmergencyController(self.intersections, self.signal_ctrl)
        self.metrics = MetricsEngine()

        # ── Vehicle pool ────────────────────────────────────────────
        scenario = cfg.TRAFFIC_SCENARIOS[self.scenario]
        self.max_vehicles = scenario['max_vehicles']
        self.pool = [Vehicle() for _ in range(400)]
        self.vehicles = []
        self.spawn_timer = 0.0
        self.spawn_interval = scenario['spawn_interval']

        # Emergency auto-spawn timer
        self._next_emergency_time = random.uniform(
            cfg.EMERGENCY_SPAWN_INTERVAL_MIN,
            cfg.EMERGENCY_SPAWN_INTERVAL_MAX
        )

    def _build_network(self):
        """Create the 2x2 grid of intersections and link neighbours."""
        self.intersections.clear()
        self.grid.clear()

        rows = cfg.GRID_ROWS
        cols = cfg.GRID_COLS
        area_w = self._road_area_w
        area_h = self._road_area_h

        sx = area_w // (cols + 1)
        sy = area_h // (rows + 1)

        idx = 0
        for r in range(rows):
            for c in range(cols):
                cx = sx * (c + 1)
                cy = cfg.TOPBAR_HEIGHT + sy * (r + 1)
                inter = Intersection(idx, (cx, cy), r, c)
                self.intersections.append(inter)
                self.grid[(r, c)] = inter
                idx += 1

        # Link neighbours
        for r in range(rows):
            for c in range(cols):
                inter = self.grid[(r, c)]
                inter.neighbours = {
                    'N': self.grid.get((r - 1, c)),
                    'S': self.grid.get((r + 1, c)),
                    'E': self.grid.get((r, c + 1)),
                    'W': self.grid.get((r, c - 1)),
                }

    def update_layout(self, road_area_w, road_area_h):
        """Recalculate intersection positions when window resizes."""
        self._road_area_w = road_area_w
        self._road_area_h = road_area_h

        rows = cfg.GRID_ROWS
        cols = cfg.GRID_COLS
        sx = road_area_w // (cols + 1)
        sy = road_area_h // (rows + 1)

        for inter in self.intersections:
            cx = sx * (inter.col + 1)
            cy = cfg.TOPBAR_HEIGHT + sy * (inter.row + 1)
            inter.center = (cx, cy)

    def set_scenario(self, scenario_key):
        if scenario_key in cfg.TRAFFIC_SCENARIOS:
            self.scenario = scenario_key
            scenario = cfg.TRAFFIC_SCENARIOS[scenario_key]
            self.spawn_interval = scenario['spawn_interval']
            self.max_vehicles = scenario['max_vehicles']

    def set_speed(self, multiplier):
        self.speed_multiplier = multiplier

    # ── Lane geometry helpers ───────────────────────────────────────

    def get_road_columns(self):
        xs = set()
        for inter in self.intersections:
            xs.add(inter.center[0])
        return sorted(xs)

    def get_road_rows(self):
        ys = set()
        for inter in self.intersections:
            ys.add(inter.center[1])
        return sorted(ys)

    # ── Vehicle spawning ────────────────────────────────────────────

    def _get_vehicle(self):
        for v in self.pool:
            if not v.active:
                return v
        return None

    def spawn_vehicle(self, emergency=False, emergency_type=None):
        """Spawn a vehicle at a random edge of the network."""
        if len(self.vehicles) >= self.max_vehicles and not emergency:
            return None

        v = self._get_vehicle()
        if not v:
            return None

        road_cols = self.get_road_columns()
        road_rows = self.get_road_rows()
        if not road_cols or not road_rows:
            return None

        margin = 30
        side = random.choice(['N', 'S', 'E', 'W'])

        if side == 'N':
            col_x = random.choice(road_cols)
            lane = col_x + cfg.LANE_OFFSET
            x = lane
            y = cfg.TOPBAR_HEIGHT - margin
            direction = 'S'
        elif side == 'S':
            col_x = random.choice(road_cols)
            lane = col_x - cfg.LANE_OFFSET
            x = lane
            y = cfg.TOPBAR_HEIGHT + self._road_area_h + margin
            direction = 'N'
        elif side == 'E':
            row_y = random.choice(road_rows)
            lane = row_y + cfg.LANE_OFFSET
            x = self._road_area_w + margin
            y = lane
            direction = 'W'
        else:
            row_y = random.choice(road_rows)
            lane = row_y - cfg.LANE_OFFSET
            x = -margin
            y = lane
            direction = 'E'

        is_emerg = emergency
        e_type = emergency_type or ""
        if is_emerg and not e_type:
            e_type = random.choice(cfg.EMERGENCY_TYPES)

        speed = random.uniform(cfg.BASE_SPEED_MIN, cfg.BASE_SPEED_MAX)
        v.reset((x, y), direction, speed, is_emerg, lane, self.time, e_type)
        self.vehicles.append(v)
        self.metrics.on_vehicle_spawn(v)

        # Immediately register emergency vehicles for green-wave
        if is_emerg:
            self.emergency_ctrl.register_emergency(v, self.time)

        return v

    # ── Main update loop ────────────────────────────────────────────

    def update(self, dt):
        if self.paused:
            return

        sim_dt = dt * self.speed_multiplier
        self.time += sim_dt

        # ── Spawn vehicles ──────────────────────────────────────────
        self.spawn_timer += sim_dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer -= self.spawn_interval
            self.spawn_vehicle()

        # Auto-spawn emergency vehicles
        if self.time >= self._next_emergency_time:
            self.spawn_vehicle(emergency=True)
            self._next_emergency_time = self.time + random.uniform(
                cfg.EMERGENCY_SPAWN_INTERVAL_MIN,
                cfg.EMERGENCY_SPAWN_INTERVAL_MAX
            )

        # ── Update queue counts ─────────────────────────────────────
        self._update_queues()

        # ── Signal controller ───────────────────────────────────────
        for inter in self.intersections:
            self.signal_ctrl.update(inter, self.time)

        # ── Swarm optimisation ──────────────────────────────────────
        self.swarm_ctrl.update(self.time)

        # ── Emergency controller ────────────────────────────────────
        self.emergency_ctrl.detect_and_manage(self.vehicles, self.time)

        # ── Vehicle update ──────────────────────────────────────────
        self._update_vehicles(sim_dt)

        # ── Metrics ─────────────────────────────────────────────────
        self.metrics.update(self.vehicles, self.intersections,
                            self.emergency_ctrl, self.time)

    def _update_queues(self):
        """Count vehicles waiting at each intersection approach."""
        for inter in self.intersections:
            inter.queue_n = 0
            inter.queue_s = 0
            inter.queue_e = 0
            inter.queue_w = 0
            inter.approaching_ns = 0
            inter.approaching_ew = 0

        for v in self.vehicles:
            if not v.active:
                continue
            inter, dist = self._find_next_intersection(v)
            if inter is None:
                continue

            if dist < cfg.EMERGENCY_DETECTION_RADIUS:
                if v.direction in ('N', 'S'):
                    inter.approaching_ns += 1
                else:
                    inter.approaching_ew += 1

            if dist < cfg.STOP_LINE_OFFSET + 120 and v.speed < 30:
                if v.direction == 'N':
                    inter.queue_n += 1
                elif v.direction == 'S':
                    inter.queue_s += 1
                elif v.direction == 'E':
                    inter.queue_e += 1
                elif v.direction == 'W':
                    inter.queue_w += 1

    def _find_next_intersection(self, v):
        """Find the next intersection ahead of vehicle v."""
        best = None
        best_dist = float('inf')

        for inter in self.intersections:
            ix, iy = inter.center
            dist = 0
            on_road = False

            if v.direction in ('N', 'S'):
                if abs(ix - v.lane_center) < cfg.ROAD_HALF_WIDTH + 8:
                    if v.direction == 'N' and iy < v.y:
                        on_road = True
                        dist = v.y - iy
                    elif v.direction == 'S' and iy > v.y:
                        on_road = True
                        dist = iy - v.y
            else:
                if abs(iy - v.lane_center) < cfg.ROAD_HALF_WIDTH + 8:
                    if v.direction == 'E' and ix > v.x:
                        on_road = True
                        dist = ix - v.x
                    elif v.direction == 'W' and ix < v.x:
                        on_road = True
                        dist = v.x - ix

            if on_road and dist < best_dist:
                best = inter
                best_dist = dist

        return best, best_dist

    def _update_vehicles(self, dt):
        """Update all vehicles with car-following and signal compliance."""
        road_area_w = self._road_area_w
        road_area_bottom = cfg.TOPBAR_HEIGHT + self._road_area_h
        margin = 250

        for v in list(self.vehicles):
            if not v.active:
                continue

            # ── Remove off-screen vehicles ──────────────────────────
            if (v.x < -margin or v.x > road_area_w + margin
                    or v.y < cfg.TOPBAR_HEIGHT - margin or v.y > road_area_bottom + margin):
                v.deactivate()
                self.vehicles.remove(v)
                self.metrics.on_vehicle_complete(v, self.time)
                continue

            target_speed = v.max_speed
            should_stop = False

            # ── Emergency vehicles: skip red signals (they have preemption) ──
            if v.is_emergency:
                # Emergency vehicles only need car-following, not signal compliance
                # They should still avoid crashing into other vehicles
                leader_dist = self._find_leader_distance(v)
                if leader_dist is not None:
                    gap = leader_dist - cfg.VEHICLE_LENGTH
                    if gap < cfg.MIN_GAP:
                        # Emergency: other vehicles should yield, but maintain safety
                        target_speed = min(target_speed, 15.0)
                    elif gap < cfg.REACTION_DISTANCE:
                        follow_speed = v.max_speed * ((gap - cfg.MIN_GAP) /
                                                       (cfg.REACTION_DISTANCE - cfg.MIN_GAP))
                        target_speed = min(target_speed, max(20, follow_speed))

                v.stopped = False
                v.update(dt, target_speed)
                continue

            # ── Normal vehicles: signal compliance ──────────────────
            inter, dist_to_center = self._find_next_intersection(v)
            if inter is not None:
                stop_dist = dist_to_center - cfg.STOP_LINE_OFFSET

                if stop_dist > 0 and stop_dist < cfg.REACTION_DISTANCE + 40:
                    if inter.is_red_for(v.direction):
                        if stop_dist < 8:
                            should_stop = True
                        else:
                            ratio = stop_dist / (cfg.REACTION_DISTANCE + 20)
                            target_speed = min(target_speed, v.max_speed * ratio)
                            if target_speed < 5:
                                should_stop = True

                    elif inter.is_yellow_for(v.direction):
                        if stop_dist > 25:
                            ratio = stop_dist / (cfg.REACTION_DISTANCE + 20)
                            target_speed = min(target_speed, v.max_speed * ratio)
                            if target_speed < 5:
                                should_stop = True

            # ── Car-following ───────────────────────────────────────────
            leader_dist = self._find_leader_distance(v)
            if leader_dist is not None:
                gap = leader_dist - cfg.VEHICLE_LENGTH
                if gap < cfg.MIN_GAP * 0.5:
                    should_stop = True
                elif gap < cfg.MIN_GAP:
                    target_speed = min(target_speed, 5.0)
                elif gap < cfg.REACTION_DISTANCE:
                    follow_speed = v.max_speed * ((gap - cfg.MIN_GAP) /
                                                   (cfg.REACTION_DISTANCE - cfg.MIN_GAP))
                    target_speed = min(target_speed, max(0, follow_speed))

            # ── Emergency yield: pull aside ──────────────────────────
            emergency_behind = self._is_emergency_approaching(v)

            if emergency_behind and not v.yielding:
                # Start yielding: shift to edge of road and stop
                v.yielding = True
                v.original_lane_center = v.lane_center
                v.lane_center += cfg.YIELD_OFFSET
                should_stop = True

            elif v.yielding:
                if not emergency_behind:
                    # Emergency has passed, return to normal lane
                    v.yielding = False
                    v.lane_center = v.original_lane_center
                else:
                    # Still yielding, remain stopped at side of road
                    should_stop = True

            v.stopped = should_stop
            v.update(dt, target_speed if not should_stop else 0)

    def _is_emergency_approaching(self, v):
        """Check if an emergency vehicle is approaching from behind on v's lane.
        Route-aware: only same-direction, same-lane emergencies trigger yield."""
        check_lane = v.original_lane_center if v.yielding else v.lane_center
        for other in self.vehicles:
            if other is v or not other.active or not other.is_emergency:
                continue
            if v.direction != other.direction:
                continue
            if abs(check_lane - other.lane_center) > 8:
                continue
            # Positive = v is ahead of emergency (emergency is behind, approaching)
            dist = other.distance_ahead_to(v.x, v.y)
            if 0 < dist < cfg.EMERGENCY_DETECTION_RADIUS * 0.5:
                return True
        return False

    def _find_leader_distance(self, v):
        """Find the distance to the nearest vehicle ahead in the same lane."""
        min_dist = float('inf')
        found = False
        search_range = cfg.REACTION_DISTANCE * 2.5

        for other in self.vehicles:
            if other is v or not other.active:
                continue
            if not v.is_on_same_lane(other):
                continue
            dist = v.distance_ahead_to(other.x, other.y)
            if 0 < dist < search_range and dist < min_dist:
                min_dist = dist
                found = True

        return min_dist if found else None

    # ── Reset ───────────────────────────────────────────────────────

    def reset(self):
        for v in self.vehicles:
            v.deactivate()
        self.vehicles.clear()

        self.time = 0.0
        self.spawn_timer = 0.0
        self._next_emergency_time = random.uniform(
            cfg.EMERGENCY_SPAWN_INTERVAL_MIN,
            cfg.EMERGENCY_SPAWN_INTERVAL_MAX
        )
        Vehicle._next_id = 1

        for inter in self.intersections:
            inter.signal_state = cfg.SIG_NS_GREEN
            inter.state_start_time = 0.0
            inter.preempt_active = False
            inter.preempt_direction = None
            inter.preempt_vehicle_id = None
            inter.preempt_transitioning = False
            inter.queue_n = 0
            inter.queue_s = 0
            inter.queue_e = 0
            inter.queue_w = 0
            inter.approaching_ns = 0
            inter.approaching_ew = 0
            inter.total_phase_changes = 0
            inter.preempt_count = 0
            inter.swarm_ns_green = cfg.DEFAULT_GREEN_TIME
            inter.swarm_ew_green = cfg.DEFAULT_GREEN_TIME

        self.swarm_ctrl = SwarmController(self.intersections)
        self.emergency_ctrl = EmergencyController(self.intersections, self.signal_ctrl)
        self.metrics.reset()
        self.set_scenario(self.scenario)
