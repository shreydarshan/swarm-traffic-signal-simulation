"""
emergency_controller.py — Emergency/VIP vehicle detection, priority, and green-wave.

Handles:
- Immediate detection of emergency vehicles upon spawn or when within range
- Route determination through the grid
- Multi-intersection green-wave coordination (preempt ALL route intersections)
- Safe signal preemption (delegates to signal_controller)
- Automatic restoration of normal control after passage
"""

import random
import math
import config as cfg


class EmergencyEvent:
    """Tracks one active emergency vehicle and its priority state."""

    def __init__(self, vehicle, route, detection_time):
        self.vehicle = vehicle
        self.route = route                   # list of intersection indices
        self.detection_time = detection_time
        self.detection_method = random.choice(["RFID", "Siren", "V2X"])
        self.preempted_intersections = set()
        self.passed_intersections = set()
        self.green_wave_active = False
        self.completed = False
        self.response_time = 0.0


class EmergencyController:
    """
    Manages all emergency vehicle events for the simulation.

    Works with signal_controller to safely preempt intersections
    and create coordinated green waves.
    """

    def __init__(self, intersections, signal_ctrl):
        self.intersections = intersections
        self.signal_ctrl = signal_ctrl
        self.inter_by_index = {i.index: i for i in intersections}
        self.active_events = []
        self.completed_events = []

    def register_emergency(self, vehicle, sim_time):
        """
        Immediately register a newly spawned emergency vehicle.
        Called directly from traffic_manager when E is pressed or auto-spawn.
        This ensures instant detection without waiting for detection radius.
        """
        # Check if already tracked
        tracked_ids = {e.vehicle.id for e in self.active_events if not e.completed}
        if vehicle.id in tracked_ids:
            return

        route = self.compute_route(vehicle)
        if route:
            event = EmergencyEvent(vehicle, route, sim_time)
            event.green_wave_active = True
            self.active_events.append(event)
            vehicle.route = route
            # Immediately preempt all route intersections
            self._coordinate_green_wave(event, vehicle, sim_time)

    def compute_route(self, vehicle):
        """
        Determine which intersections the vehicle will pass through
        based on its current position and direction.
        Returns a list of intersection indices in order of encounter.
        """
        route = []
        for inter in self.intersections:
            ix, iy = inter.center
            on_path = False
            dist = 0

            if vehicle.direction in ('N', 'S'):
                if abs(ix - vehicle.lane_center) < cfg.ROAD_HALF_WIDTH + 15:
                    if vehicle.direction == 'N' and iy < vehicle.y:
                        on_path = True
                        dist = vehicle.y - iy
                    elif vehicle.direction == 'S' and iy > vehicle.y:
                        on_path = True
                        dist = iy - vehicle.y
            else:
                if abs(iy - vehicle.lane_center) < cfg.ROAD_HALF_WIDTH + 15:
                    if vehicle.direction == 'E' and ix > vehicle.x:
                        on_path = True
                        dist = ix - vehicle.x
                    elif vehicle.direction == 'W' and ix < vehicle.x:
                        on_path = True
                        dist = vehicle.x - ix

            if on_path:
                route.append((dist, inter.index))

        route.sort()
        return [idx for _, idx in route[:cfg.GREEN_WAVE_LOOKAHEAD]]

    def detect_and_manage(self, vehicles, sim_time):
        """
        Main update loop:
        1. Detect emergency vehicles that weren't registered yet
        2. Coordinate green waves
        3. Release passed intersections
        """
        active_emergency = [v for v in vehicles if v.active and v.is_emergency]
        tracked_ids = {e.vehicle.id for e in self.active_events if not e.completed}

        # Detect any untracked emergency vehicles (e.g. from auto-spawn)
        for v in active_emergency:
            if v.id not in tracked_ids:
                detected = False
                for inter in self.intersections:
                    dist = math.hypot(v.x - inter.center[0], v.y - inter.center[1])
                    if dist < cfg.EMERGENCY_DETECTION_RADIUS:
                        detected = True
                        break
                if detected:
                    self.register_emergency(v, sim_time)

        # Update existing events
        for event in list(self.active_events):
            if event.completed:
                continue

            v = event.vehicle
            if not v.active:
                self._complete_event(event, sim_time)
                continue

            # Update route -- remove passed intersections
            updated_route = []
            for idx in event.route:
                inter = self.inter_by_index.get(idx)
                if inter is None:
                    continue

                ix, iy = inter.center
                margin = cfg.STOP_LINE_OFFSET + 30
                passed = False

                if v.direction == 'N' and v.y < iy - margin:
                    passed = True
                elif v.direction == 'S' and v.y > iy + margin:
                    passed = True
                elif v.direction == 'E' and v.x > ix + margin:
                    passed = True
                elif v.direction == 'W' and v.x < ix - margin:
                    passed = True

                if passed:
                    event.passed_intersections.add(idx)
                    if idx in event.preempted_intersections:
                        self.signal_ctrl.release_preemption(inter, sim_time)
                        event.preempted_intersections.discard(idx)
                else:
                    updated_route.append(idx)

            event.route = updated_route
            v.route = updated_route

            if not updated_route:
                self._complete_event(event, sim_time)
                continue

            # Continue coordinating green wave
            self._coordinate_green_wave(event, v, sim_time)

        self.active_events = [e for e in self.active_events if not e.completed]

    def _complete_event(self, event, sim_time):
        """Mark an event as completed and release all preempted intersections."""
        event.completed = True
        event.response_time = sim_time - event.detection_time
        self.completed_events.append(event)

        for idx in list(event.preempted_intersections):
            inter = self.inter_by_index.get(idx)
            if inter:
                self.signal_ctrl.release_preemption(inter, sim_time)
        event.preempted_intersections.clear()

    def _coordinate_green_wave(self, event, vehicle, sim_time):
        """
        Request green wave for ALL upcoming intersections along the route.
        Preempt immediately -- the signal controller handles safe transition.
        """
        direction = vehicle.direction
        axis = 'NS' if direction in ('N', 'S') else 'EW'

        for idx in event.route:
            inter = self.inter_by_index.get(idx)
            if inter is None:
                continue

            # Always request preemption for all route intersections
            self.signal_ctrl.request_preemption(inter, axis, vehicle.id, sim_time)
            event.preempted_intersections.add(idx)

    def get_active_event_count(self):
        return len([e for e in self.active_events if not e.completed])

    def get_active_events(self):
        return [e for e in self.active_events if not e.completed]

    def get_average_response_time(self):
        if not self.completed_events:
            return 0.0
        total = sum(e.response_time for e in self.completed_events)
        return total / len(self.completed_events)

    def reset(self):
        self.active_events.clear()
        self.completed_events.clear()
