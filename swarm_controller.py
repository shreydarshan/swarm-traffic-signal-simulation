"""
swarm_controller.py — PSO-inspired adaptive traffic signal optimisation.

Each intersection is treated as a particle in a swarm. The decision variables
are the green-phase durations for NS and EW. The fitness function rewards
low queue lengths, short wait times, and good throughput, while penalising
downstream congestion.

Safety: The PSO only *proposes* green durations. The signal_controller.py
state machine decides when and how to apply them.
"""

import random
import config as cfg


class Particle:
    """One PSO particle representing a candidate signal plan for an intersection."""

    def __init__(self):
        self.ns_green = random.uniform(cfg.PSO_GREEN_MIN, cfg.PSO_GREEN_MAX)
        self.ew_green = random.uniform(cfg.PSO_GREEN_MIN, cfg.PSO_GREEN_MAX)

        self.vel_ns = random.uniform(-2, 2)
        self.vel_ew = random.uniform(-2, 2)

        self.best_ns = self.ns_green
        self.best_ew = self.ew_green
        self.best_fitness = float('inf')


class SwarmController:
    """
    PSO-based signal timing optimiser for the entire network.

    Periodically evaluates traffic conditions at each intersection
    and adjusts green durations to minimise a cost function.
    """

    def __init__(self, intersections):
        self.intersections = intersections
        self.num_intersections = len(intersections)

        # Each intersection gets its own swarm of particles
        self.swarms = {}
        for inter in intersections:
            particles = [Particle() for _ in range(cfg.PSO_NUM_PARTICLES)]
            self.swarms[inter.index] = {
                'particles': particles,
                'global_best_ns': cfg.DEFAULT_GREEN_TIME,
                'global_best_ew': cfg.DEFAULT_GREEN_TIME,
                'global_best_fitness': float('inf'),
            }

        self.last_update_time = 0.0
        self.update_cycle = 0
        self.active = True

    def update(self, sim_time):
        """
        Run one PSO optimisation cycle if enough time has elapsed.
        Returns True if an update was performed.
        """
        if not self.active:
            return False

        if sim_time - self.last_update_time < cfg.PSO_UPDATE_INTERVAL:
            return False

        self.last_update_time = sim_time
        self.update_cycle += 1

        for inter in self.intersections:
            if inter.preempt_active:
                continue  # don't optimise during emergency preemption

            swarm = self.swarms[inter.index]
            self._optimise_intersection(inter, swarm)

        return True

    def get_best_cost(self):
        """Return the best (lowest) fitness across all intersection swarms."""
        best = float('inf')
        for swarm in self.swarms.values():
            if swarm['global_best_fitness'] < best:
                best = swarm['global_best_fitness']
        return best if best < float('inf') else 0.0

    def get_average_cost(self):
        """Return the average best fitness across all intersection swarms."""
        total = 0.0
        count = 0
        for swarm in self.swarms.values():
            if swarm['global_best_fitness'] < float('inf'):
                total += swarm['global_best_fitness']
                count += 1
        return total / max(1, count)

    # ── Internal PSO logic ──────────────────────────────────────────

    def _demand_ratio_green(self, ns_q, ew_q):
        """
        Compute demand-proportional green split.
        This serves as a strong heuristic seed for particles.
        """
        total = ns_q + ew_q
        if total == 0:
            return cfg.DEFAULT_GREEN_TIME, cfg.DEFAULT_GREEN_TIME

        ns_frac = max(0.2, ns_q / total)
        ew_frac = max(0.2, ew_q / total)

        total_green = cfg.DEFAULT_GREEN_TIME * 2
        ns_g = max(cfg.PSO_GREEN_MIN, min(cfg.PSO_GREEN_MAX, total_green * ns_frac))
        ew_g = max(cfg.PSO_GREEN_MIN, min(cfg.PSO_GREEN_MAX, total_green * ew_frac))
        return ns_g, ew_g

    def _fitness(self, inter, ns_green, ew_green):
        """
        Evaluate the fitness (cost) of a candidate signal plan.

        Lower is better. The cost considers:
        - Queue imbalance relative to green allocation
        - Total queue length
        - Neighbour downstream congestion
        - Starvation penalty (queue growing while getting no green)
        """
        ns_q = inter.ns_queue
        ew_q = inter.ew_queue
        total_q = ns_q + ew_q

        # Queue-to-green ratio (want proportional service)
        total_green = ns_green + ew_green
        if total_green <= 0:
            return 1000.0

        ns_ratio = ns_green / total_green
        ew_ratio = ew_green / total_green

        demand_total = max(1, ns_q + ew_q)
        ns_demand_ratio = ns_q / demand_total
        ew_demand_ratio = ew_q / demand_total

        # Imbalance cost: how far the green allocation deviates from demand
        imbalance = abs(ns_ratio - ns_demand_ratio) + abs(ew_ratio - ew_demand_ratio)

        # Total queue cost — heavily penalise large queues
        queue_cost = total_q * 3.0

        # Starvation: if one direction has a large queue but gets little green
        starvation = 0.0
        if ns_q > 3 and ns_green < cfg.PSO_GREEN_MIN + 2:
            starvation += ns_q * 5.0
        if ew_q > 3 and ew_green < cfg.PSO_GREEN_MIN + 2:
            starvation += ew_q * 5.0

        # Downstream congestion penalty
        downstream_cost = 0.0
        for direction, neighbour in inter.neighbours.items():
            if neighbour is not None:
                n_queue = neighbour.ns_queue + neighbour.ew_queue
                downstream_cost += n_queue * cfg.PSO_NEIGHBOUR_WEIGHT

        # Approaching vehicle pressure
        approach_cost = 0.0
        if inter.approaching_ns > inter.approaching_ew + 2 and ns_green < ew_green:
            approach_cost += (inter.approaching_ns - inter.approaching_ew) * 2.0
        elif inter.approaching_ew > inter.approaching_ns + 2 and ew_green < ns_green:
            approach_cost += (inter.approaching_ew - inter.approaching_ns) * 2.0

        fitness = (imbalance * 20.0
                   + queue_cost
                   + starvation
                   + downstream_cost
                   + approach_cost)
        return fitness

    def _optimise_intersection(self, inter, swarm):
        """Run one PSO iteration for a single intersection."""
        particles = swarm['particles']

        # Seed one particle with demand-proportional split for fast convergence
        demand_ns, demand_ew = self._demand_ratio_green(inter.ns_queue, inter.ew_queue)
        particles[0].ns_green = demand_ns
        particles[0].ew_green = demand_ew

        for p in particles:
            # Evaluate fitness
            fitness = self._fitness(inter, p.ns_green, p.ew_green)

            # Update personal best
            if fitness < p.best_fitness:
                p.best_fitness = fitness
                p.best_ns = p.ns_green
                p.best_ew = p.ew_green

            # Update global best
            if fitness < swarm['global_best_fitness']:
                swarm['global_best_fitness'] = fitness
                swarm['global_best_ns'] = p.ns_green
                swarm['global_best_ew'] = p.ew_green

        # Update velocities and positions
        for p in particles:
            r1 = random.random()
            r2 = random.random()

            # Velocity update (standard PSO)
            p.vel_ns = (cfg.PSO_INERTIA * p.vel_ns
                        + cfg.PSO_COGNITIVE * r1 * (p.best_ns - p.ns_green)
                        + cfg.PSO_SOCIAL * r2 * (swarm['global_best_ns'] - p.ns_green))

            p.vel_ew = (cfg.PSO_INERTIA * p.vel_ew
                        + cfg.PSO_COGNITIVE * r1 * (p.best_ew - p.ew_green)
                        + cfg.PSO_SOCIAL * r2 * (swarm['global_best_ew'] - p.ew_green))

            # Clamp velocities
            max_vel = 4.0
            p.vel_ns = max(-max_vel, min(max_vel, p.vel_ns))
            p.vel_ew = max(-max_vel, min(max_vel, p.vel_ew))

            # Position update
            p.ns_green = max(cfg.PSO_GREEN_MIN,
                             min(cfg.PSO_GREEN_MAX, p.ns_green + p.vel_ns))
            p.ew_green = max(cfg.PSO_GREEN_MIN,
                             min(cfg.PSO_GREEN_MAX, p.ew_green + p.vel_ew))

        # Apply best solution to intersection
        inter.swarm_ns_green = swarm['global_best_ns']
        inter.swarm_ew_green = swarm['global_best_ew']

        # Decay global best fitness to allow adaptation to changing traffic
        swarm['global_best_fitness'] *= 1.08
