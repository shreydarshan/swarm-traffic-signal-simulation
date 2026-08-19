"""
signal_controller.py — Traffic signal state machine with safety guarantees.

Implements a proper 6-state finite state machine for each intersection:

    NS_GREEN -> NS_YELLOW -> ALL_RED_1 -> EW_GREEN -> EW_YELLOW -> ALL_RED_2 -> (repeat)

Key features:
- Safety invariant: no conflicting greens ever.
- Early phase termination when current direction has cleared and opposing has demand.
- Emergency preemption transitions safely through yellow -> all-red first.
- Swarm-proposed durations are respected within safety bounds.
"""

import config as cfg


class SignalController:
    """
    Manages signal state transitions for all intersections.

    The swarm controller proposes green durations; this controller ensures
    all transitions are safe before applying them.  It also performs
    demand-responsive early switching so empty phases don't waste time.
    """

    def update(self, intersection, sim_time):
        """
        Advance the signal state machine for a single intersection.
        Called every simulation tick.
        """
        state = intersection.signal_state
        elapsed = intersection.time_in_state(sim_time)

        # ── Handle emergency preemption transition ──────────────────
        if intersection.preempt_transitioning:
            self._handle_preempt_transition(intersection, sim_time, state, elapsed)
            return

        # ── If preempt is active and we're already in the correct green,
        #    hold the green (don't let normal logic switch away) ──────
        if intersection.preempt_active:
            target_green = (cfg.SIG_NS_GREEN if intersection.preempt_direction == 'NS'
                            else cfg.SIG_EW_GREEN)
            if state == target_green:
                # Hold green for emergency — don't switch
                return

        # ── Normal state machine ────────────────────────────────────
        if state == cfg.SIG_NS_GREEN:
            green_dur = intersection.swarm_ns_green
            green_dur = max(cfg.MIN_GREEN_TIME, min(cfg.MAX_GREEN_TIME, green_dur))

            ns_q = intersection.ns_queue
            ew_q = intersection.ew_queue

            # Early termination conditions (after MIN_GREEN):
            # 1) Current direction empty, opposing has demand
            # 2) Opposing queue much larger than current (imbalance)
            if elapsed >= cfg.MIN_GREEN_TIME:
                if ns_q == 0 and ew_q >= cfg.EARLY_SWITCH_QUEUE_THRESHOLD:
                    self._transition(intersection, cfg.SIG_NS_YELLOW, sim_time)
                elif ew_q >= ns_q * 3 + 2 and ew_q >= 3 and elapsed >= cfg.MIN_GREEN_TIME + 2:
                    self._transition(intersection, cfg.SIG_NS_YELLOW, sim_time)
                elif elapsed >= green_dur:
                    self._transition(intersection, cfg.SIG_NS_YELLOW, sim_time)
            elif elapsed >= green_dur:
                self._transition(intersection, cfg.SIG_NS_YELLOW, sim_time)

        elif state == cfg.SIG_NS_YELLOW:
            if elapsed >= cfg.YELLOW_TIME:
                self._transition(intersection, cfg.SIG_ALL_RED_1, sim_time)

        elif state == cfg.SIG_ALL_RED_1:
            if elapsed >= cfg.ALL_RED_TIME:
                self._transition(intersection, cfg.SIG_EW_GREEN, sim_time)
                intersection.current_green_duration = intersection.swarm_ew_green

        elif state == cfg.SIG_EW_GREEN:
            green_dur = intersection.swarm_ew_green
            green_dur = max(cfg.MIN_GREEN_TIME, min(cfg.MAX_GREEN_TIME, green_dur))

            ns_q = intersection.ns_queue
            ew_q = intersection.ew_queue

            # Early termination (mirror of NS logic)
            if elapsed >= cfg.MIN_GREEN_TIME:
                if ew_q == 0 and ns_q >= cfg.EARLY_SWITCH_QUEUE_THRESHOLD:
                    self._transition(intersection, cfg.SIG_EW_YELLOW, sim_time)
                elif ns_q >= ew_q * 3 + 2 and ns_q >= 3 and elapsed >= cfg.MIN_GREEN_TIME + 2:
                    self._transition(intersection, cfg.SIG_EW_YELLOW, sim_time)
                elif elapsed >= green_dur:
                    self._transition(intersection, cfg.SIG_EW_YELLOW, sim_time)
            elif elapsed >= green_dur:
                self._transition(intersection, cfg.SIG_EW_YELLOW, sim_time)

        elif state == cfg.SIG_EW_YELLOW:
            if elapsed >= cfg.YELLOW_TIME:
                self._transition(intersection, cfg.SIG_ALL_RED_2, sim_time)

        elif state == cfg.SIG_ALL_RED_2:
            if elapsed >= cfg.ALL_RED_TIME:
                self._transition(intersection, cfg.SIG_NS_GREEN, sim_time)
                intersection.current_green_duration = intersection.swarm_ns_green

    def request_preemption(self, intersection, direction_axis, vehicle_id, sim_time):
        """
        Request emergency preemption for an intersection.

        direction_axis: 'NS' or 'EW'

        This does NOT instantly switch the signal. Instead, it initiates
        a safe transition sequence:
          current -> yellow -> all-red -> emergency green
        """
        if intersection.preempt_active and intersection.preempt_direction == direction_axis:
            return  # already preempting for this direction

        intersection.preempt_active = True
        intersection.preempt_direction = direction_axis
        intersection.preempt_vehicle_id = vehicle_id
        intersection.preempt_count += 1

        # Check if we're already in the correct green phase
        if direction_axis == 'NS' and intersection.signal_state == cfg.SIG_NS_GREEN:
            return  # already green for the correct direction
        if direction_axis == 'EW' and intersection.signal_state == cfg.SIG_EW_GREEN:
            return  # already green for the correct direction

        # Start safe transition
        intersection.preempt_transitioning = True

    def release_preemption(self, intersection, sim_time):
        """Release emergency preemption, returning to normal adaptive control."""
        if not intersection.preempt_active:
            return
        intersection.preempt_active = False
        intersection.preempt_direction = None
        intersection.preempt_vehicle_id = None
        intersection.preempt_transitioning = False
        # Reset the green duration to swarm-recommended so it doesn't hold forever
        if intersection.signal_state == cfg.SIG_NS_GREEN:
            intersection.swarm_ns_green = max(cfg.MIN_GREEN_TIME,
                                               intersection.swarm_ns_green)
        elif intersection.signal_state == cfg.SIG_EW_GREEN:
            intersection.swarm_ew_green = max(cfg.MIN_GREEN_TIME,
                                               intersection.swarm_ew_green)

    # ── Internal helpers ────────────────────────────────────────────

    def _transition(self, intersection, new_state, sim_time):
        """Transition to a new signal state."""
        intersection.signal_state = new_state
        intersection.state_start_time = sim_time
        if new_state in (cfg.SIG_NS_GREEN, cfg.SIG_EW_GREEN):
            intersection.total_phase_changes += 1

    def _handle_preempt_transition(self, intersection, sim_time, state, elapsed):
        """
        Safely transition to the emergency green phase.

        Sequence:
        1. If currently green for the WRONG direction -> go to yellow
        2. If in yellow -> wait for yellow to complete -> go to all-red
        3. If in all-red -> wait for clearance -> go to emergency green
        4. If already green for the RIGHT direction -> done
        """
        target_axis = intersection.preempt_direction  # 'NS' or 'EW'
        target_green = cfg.SIG_NS_GREEN if target_axis == 'NS' else cfg.SIG_EW_GREEN

        if state == target_green:
            # Already green for emergency direction
            intersection.preempt_transitioning = False
            return

        # If in the opposing green, start yellow
        if state == cfg.SIG_NS_GREEN and target_axis == 'EW':
            self._transition(intersection, cfg.SIG_NS_YELLOW, sim_time)
        elif state == cfg.SIG_EW_GREEN and target_axis == 'NS':
            self._transition(intersection, cfg.SIG_EW_YELLOW, sim_time)

        # If in yellow, wait then go to all-red
        elif state in (cfg.SIG_NS_YELLOW, cfg.SIG_EW_YELLOW):
            if elapsed >= cfg.YELLOW_TIME:
                all_red = cfg.SIG_ALL_RED_1 if state == cfg.SIG_NS_YELLOW else cfg.SIG_ALL_RED_2
                self._transition(intersection, all_red, sim_time)

        # If in all-red, wait then go to target green
        elif state in (cfg.SIG_ALL_RED_1, cfg.SIG_ALL_RED_2):
            if elapsed >= cfg.ALL_RED_TIME:
                self._transition(intersection, target_green, sim_time)
                intersection.preempt_transitioning = False
                # Set a generous green for emergency passage
                if target_axis == 'NS':
                    intersection.swarm_ns_green = cfg.MAX_GREEN_TIME
                else:
                    intersection.swarm_ew_green = cfg.MAX_GREEN_TIME
