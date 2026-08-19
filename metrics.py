"""
metrics.py — Real-time metrics engine.

Tracks all simulation statistics from actual events, not estimates.
"""

import config as cfg


class MetricsEngine:
    """Collects and computes real-time simulation metrics."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.total_spawned = 0
        self.total_completed = 0
        self.active_vehicles = 0
        self.emergency_spawned = 0
        self.emergency_active = 0

        # Wait time tracking
        self._wait_times = []        # completed vehicle wait times
        self._current_waits = []     # active vehicle wait times (snapshot)

        # Travel time tracking
        self._travel_times = []

        # Queue lengths (updated each tick)
        self.current_queues = {}     # {intersection_index: {'N':n, 'S':n, 'E':n, 'W':n}}
        self.max_queue_ever = 0

        # Throughput
        self._completions_in_window = []   # list of (completion_time,)
        self.throughput_window = 60.0       # 60-second rolling window

        # Emergency response
        self._response_times = []

        # Congestion
        self.congestion_level = "LOW"

        # Signal stats
        self.total_phase_changes = 0

    def on_vehicle_spawn(self, vehicle):
        self.total_spawned += 1
        if vehicle.is_emergency:
            self.emergency_spawned += 1

    def on_vehicle_complete(self, vehicle, sim_time):
        self.total_completed += 1
        self._wait_times.append(vehicle.wait_time)
        self._travel_times.append(vehicle.travel_time)
        self._completions_in_window.append(sim_time)

    def on_emergency_complete(self, response_time):
        self._response_times.append(response_time)

    def update(self, vehicles, intersections, emergency_ctrl, sim_time):
        """Update all metrics from current simulation state."""
        # Active counts
        active = [v for v in vehicles if v.active]
        self.active_vehicles = len(active)
        self.emergency_active = sum(1 for v in active if v.is_emergency)

        # Current wait times
        self._current_waits = [v.wait_time for v in active if v.wait_time > 0]

        # Queue lengths per intersection
        for inter in intersections:
            self.current_queues[inter.index] = {
                'N': inter.queue_n,
                'S': inter.queue_s,
                'E': inter.queue_e,
                'W': inter.queue_w,
                'total': inter.queue_n + inter.queue_s + inter.queue_e + inter.queue_w,
            }
            total_q = inter.queue_n + inter.queue_s + inter.queue_e + inter.queue_w
            if total_q > self.max_queue_ever:
                self.max_queue_ever = total_q

        # Prune throughput window
        cutoff = sim_time - self.throughput_window
        self._completions_in_window = [
            t for t in self._completions_in_window if t > cutoff
        ]

        # Phase changes
        self.total_phase_changes = sum(i.total_phase_changes for i in intersections)

        # Congestion level
        total_queue = sum(
            q['total'] for q in self.current_queues.values()
        )
        if total_queue > len(intersections) * 12:
            self.congestion_level = "CRITICAL"
        elif total_queue > len(intersections) * 7:
            self.congestion_level = "HIGH"
        elif total_queue > len(intersections) * 3:
            self.congestion_level = "MODERATE"
        else:
            self.congestion_level = "LOW"

    # ── Computed Properties ─────────────────────────────────────────

    @property
    def avg_wait_time(self):
        all_waits = self._wait_times + self._current_waits
        if not all_waits:
            return 0.0
        return sum(all_waits) / len(all_waits)

    @property
    def max_wait_time(self):
        all_waits = self._wait_times + self._current_waits
        if not all_waits:
            return 0.0
        return max(all_waits)

    @property
    def avg_travel_time(self):
        if not self._travel_times:
            return 0.0
        return sum(self._travel_times) / len(self._travel_times)

    @property
    def throughput(self):
        """Vehicles completed per minute (rolling window)."""
        count = len(self._completions_in_window)
        return count * (60.0 / self.throughput_window)

    @property
    def total_queue(self):
        return sum(q['total'] for q in self.current_queues.values())

    @property
    def avg_response_time(self):
        if not self._response_times:
            return 0.0
        return sum(self._response_times) / len(self._response_times)
