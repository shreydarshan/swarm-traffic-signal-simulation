"""
models.py — Data models for the simulation.

Vehicle and Intersection representations, preserving the original pool-reuse
pattern and extending with physics, routing, and signal state machine support.
"""

import math
import random
import config as cfg


# ═══════════════════════════════════════════════════════════════════════
#  Vehicle
# ═══════════════════════════════════════════════════════════════════════

class Vehicle:
    """
    A vehicle that moves through the road network.

    Preserves the original pool pattern (active/inactive), adding
    acceleration-based car-following and proper signal compliance.
    """

    _next_id = 1

    def __init__(self):
        self.active = False
        self.id = 0
        self.x = 0.0
        self.y = 0.0
        self.direction = 'S'          # N / S / E / W
        self.speed = 0.0              # current speed (px/s)
        self.max_speed = 100.0        # desired cruising speed
        self.is_emergency = False
        self.emergency_type = ""      # "Ambulance", "Fire Truck", "Police"
        self.lane_center = 0.0

        # Physics
        self.target_speed = 0.0       # what the vehicle wants to reach
        self.stopped = False
        self.wait_time = 0.0
        self.travel_time = 0.0
        self.distance_travelled = 0.0

        # Route (list of intersection indices for emergency green-wave)
        self.route = []
        self.passed_intersections = set()

        # Spawn time (for metrics)
        self.spawn_time = 0.0

        # Detection state
        self.detected_at = set()      # intersection indices that detected this vehicle

        # Yield state (for emergency priority)
        self.yielding = False
        self.original_lane_center = 0.0

    def reset(self, pos, direction, max_speed, emergency, lane_center,
              sim_time, emergency_type=""):
        """Activate this vehicle from the pool."""
        self.id = Vehicle._next_id
        Vehicle._next_id += 1

        self.x, self.y = pos
        self.direction = direction
        self.max_speed = max_speed * (cfg.EMERGENCY_SPEED_MULT if emergency else 1.0)
        self.speed = self.max_speed * 0.5   # start at half speed (accelerate in)
        self.target_speed = self.max_speed
        self.is_emergency = emergency
        self.emergency_type = emergency_type if emergency else ""
        self.lane_center = lane_center

        self.stopped = False
        self.wait_time = 0.0
        self.travel_time = 0.0
        self.distance_travelled = 0.0
        self.spawn_time = sim_time

        self.route = []
        self.passed_intersections = set()
        self.detected_at = set()
        self.yielding = False
        self.original_lane_center = lane_center
        self.active = True

    def deactivate(self):
        self.active = False

    def front_position(self):
        """Return the position of the front bumper."""
        half = cfg.VEHICLE_LENGTH / 2
        if self.direction == 'N':
            return (self.x, self.y - half)
        elif self.direction == 'S':
            return (self.x, self.y + half)
        elif self.direction == 'E':
            return (self.x + half, self.y)
        elif self.direction == 'W':
            return (self.x - half, self.y)
        return (self.x, self.y)

    def rear_position(self):
        """Return the position of the rear bumper."""
        half = cfg.VEHICLE_LENGTH / 2
        if self.direction == 'N':
            return (self.x, self.y + half)
        elif self.direction == 'S':
            return (self.x, self.y - half)
        elif self.direction == 'E':
            return (self.x - half, self.y)
        elif self.direction == 'W':
            return (self.x + half, self.y)
        return (self.x, self.y)

    def distance_ahead_to(self, px, py):
        """Signed distance from this vehicle's front to a point ahead.
        Positive means the point is ahead, negative means behind."""
        fx, fy = self.front_position()
        if self.direction == 'N':
            return fy - py   # py < fy means ahead
        elif self.direction == 'S':
            return py - fy
        elif self.direction == 'E':
            return px - fx
        elif self.direction == 'W':
            return fx - px
        return 0

    def is_on_same_lane(self, other):
        """Check if two vehicles share the same lane (same direction & lane_center)."""
        if self.direction != other.direction:
            return False
        if self.direction in ('N', 'S'):
            return abs(self.lane_center - other.lane_center) < 5
        else:
            return abs(self.lane_center - other.lane_center) < 5

    def update(self, dt, target_speed=None):
        """
        Update vehicle position using simple acceleration model.
        target_speed overrides self.target_speed if provided.
        """
        if target_speed is not None:
            self.target_speed = target_speed

        self.travel_time += dt

        # Always snap lateral position to lane_center (needed for yield shift)
        if self.direction in ('N', 'S'):
            self.x = self.lane_center
        else:
            self.y = self.lane_center

        if self.stopped:
            self.wait_time += dt
            # Decelerate to zero
            if self.speed > 0:
                self.speed = max(0, self.speed - cfg.DECELERATION * dt)
            return

        # Accelerate / decelerate toward target
        if self.speed < self.target_speed:
            self.speed = min(self.target_speed,
                             self.speed + cfg.ACCELERATION * dt)
        elif self.speed > self.target_speed:
            self.speed = max(self.target_speed,
                             self.speed - cfg.DECELERATION * dt)

        step = self.speed * dt
        self.distance_travelled += step

        if self.direction == 'N':
            self.y -= step
            self.x = self.lane_center
        elif self.direction == 'S':
            self.y += step
            self.x = self.lane_center
        elif self.direction == 'E':
            self.x += step
            self.y = self.lane_center
        elif self.direction == 'W':
            self.x -= step
            self.y = self.lane_center


# ═══════════════════════════════════════════════════════════════════════
#  Intersection
# ═══════════════════════════════════════════════════════════════════════

class Intersection:
    """
    A single intersection with a proper signal state machine.

    Preserves the original centre/grid concept while adding:
    - 6-state FSM (NS_GREEN, NS_YELLOW, ALL_RED_1, EW_GREEN, EW_YELLOW, ALL_RED_2)
    - Queue tracking per direction
    - Neighbour references for coordination
    - Swarm decision variables
    """

    def __init__(self, index, center, row, col):
        self.index = index
        self.center = center
        self.row = row
        self.col = col

        # Signal state machine
        self.signal_state = cfg.SIG_NS_GREEN
        self.state_start_time = 0.0
        self.current_green_duration = cfg.DEFAULT_GREEN_TIME

        # Emergency preemption
        self.preempt_active = False
        self.preempt_direction = None      # 'NS' or 'EW'
        self.preempt_vehicle_id = None
        self.preempt_transitioning = False  # True while safely transitioning to preempt phase

        # Queue tracking (vehicles waiting at each approach)
        self.queue_n = 0
        self.queue_s = 0
        self.queue_e = 0
        self.queue_w = 0

        # Approaching vehicle counts
        self.approaching_ns = 0
        self.approaching_ew = 0

        # Neighbours (set by traffic_manager during init)
        self.neighbours = {}   # {'N': Intersection, 'S': ..., 'E': ..., 'W': ...}

        # Swarm decision variables (set by PSO controller)
        self.swarm_ns_green = cfg.DEFAULT_GREEN_TIME
        self.swarm_ew_green = cfg.DEFAULT_GREEN_TIME
        self.swarm_offset = 0.0     # phase offset for coordination

        # Statistics
        self.total_phase_changes = 0
        self.preempt_count = 0

    @property
    def ns_queue(self):
        return self.queue_n + self.queue_s

    @property
    def ew_queue(self):
        return self.queue_e + self.queue_w

    def is_green_for(self, direction):
        """Check if the signal is green for a given vehicle direction."""
        if direction in ('N', 'S'):
            return self.signal_state == cfg.SIG_NS_GREEN
        else:
            return self.signal_state == cfg.SIG_EW_GREEN

    def is_yellow_for(self, direction):
        """Check if the signal is yellow for a given vehicle direction."""
        if direction in ('N', 'S'):
            return self.signal_state == cfg.SIG_NS_YELLOW
        else:
            return self.signal_state == cfg.SIG_EW_YELLOW

    def is_red_for(self, direction):
        """Check if the signal is red (or all-red) for a given vehicle direction."""
        return not self.is_green_for(direction) and not self.is_yellow_for(direction)

    def time_in_state(self, sim_time):
        """Seconds since the current state began."""
        return sim_time - self.state_start_time

    def remaining_green(self, sim_time):
        """Seconds remaining in the current green phase, or 0 if not green."""
        if self.signal_state in (cfg.SIG_NS_GREEN, cfg.SIG_EW_GREEN):
            elapsed = sim_time - self.state_start_time
            return max(0, self.current_green_duration - elapsed)
        return 0.0

    def stop_line_position(self, direction):
        """Return (x, y) of the stop line for vehicles approaching from `direction`."""
        cx, cy = self.center
        offset = cfg.STOP_LINE_OFFSET
        if direction == 'N':
            return (cx, cy + offset)    # vehicle going N stops south of centre
        elif direction == 'S':
            return (cx, cy - offset)
        elif direction == 'E':
            return (cx - offset, cy)
        elif direction == 'W':
            return (cx + offset, cy)
        return self.center

    def __repr__(self):
        return f"I({self.row},{self.col})"
