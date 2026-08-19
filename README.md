# Swarm-Based Traffic Signal Simulation

> **Adaptive Traffic Signal Control with Emergency Vehicle Priority and Coordinated Green-Wave Propagation**

A real-time simulation demonstrating how decentralised swarm/PSO-inspired intelligence can dynamically optimise traffic signals across a coordinated intersection network, with priority green-wave corridors for emergency and VIP vehicles.

---

## Overview

Traditional traffic control systems rely on fixed-timer or simple actuated signals that cannot adapt to changing demand patterns. This project implements a **Particle Swarm Optimisation (PSO)** based approach where each intersection acts as an intelligent agent in a swarm, continuously optimising signal timing based on real-time traffic conditions, neighbour state, and downstream congestion.

The system also features a **route-aware emergency priority system** that creates coordinated green-wave corridors across multiple intersections, allowing emergency vehicles to pass through with minimal delay while maintaining signal safety.

---

## Features

### Swarm-Based Adaptive Control
- Each intersection runs a PSO particle swarm with 15 particles
- Decision variables: NS green duration, EW green duration
- Fitness function considers: queue balance, total queue, downstream congestion, approach pressure
- Periodic optimisation cycles (~5 seconds) that adapt to changing traffic

### Signal State Machine
- Proper 6-state FSM: `NS_GREEN → NS_YELLOW → ALL_RED → EW_GREEN → EW_YELLOW → ALL_RED`
- No conflicting greens are ever possible
- Configurable timing: min/max green, yellow, all-red clearance
- Safety constraints always override optimisation proposals

### Emergency Vehicle Priority
- Three emergency vehicle types: Ambulance, Fire Truck, Police
- Conceptual detection via RFID, Siren, or V2X sensors
- Route-aware multi-intersection green-wave coordination
- Safe preemption: current phase → yellow → all-red → emergency green
- Automatic restoration of normal adaptive control after passage
- ETA-based lookahead for proactive signal preparation

### Realistic Vehicle Behaviour
- Acceleration/deceleration car-following model
- Stop-line based signal compliance (vehicles actually stop at red)
- Safe following distance with proportional braking
- Yellow-light decision (stop if safe, proceed if committed)
- Multiple vehicle types with varied speeds

### Real-Time Metrics
- Average/max wait time (from actual vehicle data)
- Queue lengths per intersection per direction
- Throughput (vehicles/minute, rolling 60s window)
- Congestion level (LOW/MODERATE/HIGH/CRITICAL)
- Emergency response times
- Swarm optimisation cycle and cost tracking

### Professional Dashboard
- Dark-theme traffic management centre interface
- Road network with stop lines, lane markings, and signal indicators
- Real-time sidebar panels: Metrics, Signal Status, Swarm Control, Emergency Status
- Emergency alert banners with vehicle tracking
- Simulation controls with speed adjustment

---

## Architecture

```
main.py                  ← Entry point, game loop, event handling
config.py                ← All configurable constants
models.py                ← Vehicle and Intersection data models
signal_controller.py     ← 6-state signal FSM with safety guarantees
swarm_controller.py      ← PSO-based signal timing optimisation
emergency_controller.py  ← Detection, priority, green-wave coordination
traffic_manager.py       ← World simulation, spawning, car-following
metrics.py               ← Real-time statistics from actual events
ui.py                    ← Professional dashboard rendering
```

### Data Flow

```
Traffic Conditions → PSO Swarm → Proposed Green Durations
                                          ↓
                              Signal Safety Validator
                                          ↓
                              Valid Signal Plan → Traffic Lights
                                          ↓
                              Vehicles obey signals (stop/go)
                                          ↓
                              Metrics collected from vehicle events
```

### Emergency Green-Wave Flow

```
Emergency Vehicle Detected (RFID/Siren/V2X)
        ↓
Compute Route (upcoming intersections)
        ↓
Calculate ETA per intersection
        ↓
Request Preemption (safe transition)
        ↓
Current GREEN → YELLOW → ALL_RED → Emergency GREEN
        ↓
Vehicle passes → Release preemption
        ↓
Normal adaptive control resumes
```

---

## Swarm / PSO Algorithm

Each intersection maintains a swarm of 15 particles. Each particle represents a candidate signal plan (NS green duration, EW green duration).

**Fitness Function:**
```
cost = imbalance × 15 + queue × 2 + downstream × 0.3 + approach_pressure + extreme_penalty
```

**PSO Update (standard velocity + position):**
```
v_new = w × v_old + c1 × r1 × (p_best - x) + c2 × r2 × (g_best - x)
x_new = x + v_new
```

Parameters: `w=0.7, c1=1.5, c2=1.8`

The global best fitness decays by 5% each cycle to allow re-adaptation to changing traffic conditions.

**Safety invariant:** PSO only proposes durations. The signal controller state machine validates all transitions.

---

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `E` | Spawn Emergency Vehicle |
| `S` | Toggle Swarm ON/OFF |
| `R` | Reset Simulation |
| `1` | Low Traffic |
| `2` | Normal Traffic |
| `3` | High Traffic |
| `4` | Peak Hour |
| `+`/`-` | Adjust simulation speed (0.5×–4×) |
| `ESC` | Menu / Exit |

---

## Traffic Scenarios

| Scenario | Spawn Interval | Max Vehicles |
|----------|---------------|-------------|
| Low | 1.8s | 40 |
| Normal | 0.9s | 100 |
| High | 0.45s | 200 |
| Peak | 0.25s | 300 |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/shreydarshan/swarm-traffic-signal-simulation.git
cd swarm-traffic-signal-simulation

# Install dependencies
pip install -r requirements.txt
```

### Requirements
- Python 3.8+
- pygame >= 2.1.0
- numpy >= 1.21.0

---

## How to Run

```bash
python main.py
```

The simulation opens with a menu screen. Click **START SIMULATION** to begin.

---

## Technologies

- **Python** — Core simulation logic
- **Pygame** — Real-time rendering and interaction
- **NumPy** — Numerical support
- **PSO (Particle Swarm Optimisation)** — Adaptive signal control

---

## Results

- Reduced average wait time through adaptive signal timing
- Improved throughput via queue-aware green duration allocation
- Coordinated green-wave corridors for emergency vehicles
- Demonstrated inter-intersection coordination via PSO neighbourhood communication
- Real-time metrics confirm actual simulation state (not estimated)

---

## Limitations

- Vehicles travel in straight lines (no turning at intersections)
- Simplified car-following model (no lane changing)
- PSO operates on green durations only (no full phase/cycle optimisation)
- 2D top-down view only
- No real sensor hardware (detection is conceptual/simulated)

---

## Future Scope

- Vehicle turning and route planning through the grid
- Deep reinforcement learning for signal control comparison
- Integration with real-time sensor data (camera, inductive loops)
- 3D visualisation
- Multi-modal traffic (pedestrians, cyclists)
- Large-scale city network simulation
- Cloud-based distributed swarm coordination

---

## Authors

- Shrey Darshan
- Rajat Kanwar
- Shaurya Taneja

---

## Note

This project was developed as part of Project-Based Learning (PBL).
