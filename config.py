"""
config.py — Central configuration for Swarm-Based Traffic Signal Simulation.

All tunable constants live here so nothing is hard-coded elsewhere.
Organised by subsystem for clarity.
"""


# ── Window & Rendering ──────────────────────────────────────────────
INITIAL_WIDTH = 1250
INITIAL_HEIGHT = 720
MIN_WIDTH = 1100
MIN_HEIGHT = 650
FPS = 60

# ── Grid / Road Network ─────────────────────────────────────────────
GRID_ROWS = 2
GRID_COLS = 2

ROAD_HALF_WIDTH = 34          # half-width of each road segment (pixels)
LANE_OFFSET = 17              # offset from road centre to lane centre
INTERSECTION_SIZE = 30        # half-size of intersection box

# ── Vehicle Dimensions ───────────────────────────────────────────────
VEHICLE_LENGTH = 18
VEHICLE_WIDTH = 10
EMERGENCY_VEHICLE_LENGTH = 24
EMERGENCY_VEHICLE_WIDTH = 13

# ── Vehicle Physics (car-following) ──────────────────────────────────
BASE_SPEED_MIN = 80           # px/s
BASE_SPEED_MAX = 130          # px/s
EMERGENCY_SPEED_MULT = 1.8    # emergency vehicles are 80% faster
ACCELERATION = 200            # px/s²  (how quickly vehicles speed up)
DECELERATION = 350            # px/s²  (comfortable braking)
HARD_BRAKE = 600              # px/s²  (emergency braking)

MIN_GAP = 20                  # minimum bumper-to-bumper gap (pixels)
REACTION_DISTANCE = 55        # distance at which a vehicle starts reacting
STOP_LINE_OFFSET = 40         # distance from intersection centre to stop line
YIELD_OFFSET = 14             # lateral shift (px) when yielding to emergency

# ── Signal Timing (seconds) ─────────────────────────────────────────
MIN_GREEN_TIME = 5.0          # allow faster switching when queues are empty
MAX_GREEN_TIME = 35.0
DEFAULT_GREEN_TIME = 12.0     # shorter default for snappier cycling
YELLOW_TIME = 2.5
ALL_RED_TIME = 1.5

# Early-termination: if current green direction has 0 queued vehicles
# and min green has elapsed, and opposing queue >= this threshold, switch early
EARLY_SWITCH_QUEUE_THRESHOLD = 1

# Signal states (enum-like)
SIG_NS_GREEN = 0
SIG_NS_YELLOW = 1
SIG_ALL_RED_1 = 2       # clearance after NS
SIG_EW_GREEN = 3
SIG_EW_YELLOW = 4
SIG_ALL_RED_2 = 5       # clearance after EW

SIGNAL_STATE_NAMES = {
    SIG_NS_GREEN: "NS_GREEN",
    SIG_NS_YELLOW: "NS_YELLOW",
    SIG_ALL_RED_1: "ALL_RED",
    SIG_EW_GREEN: "EW_GREEN",
    SIG_EW_YELLOW: "EW_YELLOW",
    SIG_ALL_RED_2: "ALL_RED",
}

# ── PSO / Swarm Parameters ──────────────────────────────────────────
PSO_NUM_PARTICLES = 12
PSO_INERTIA = 0.6
PSO_COGNITIVE = 1.4           # personal best weight
PSO_SOCIAL = 2.0              # global best weight
PSO_UPDATE_INTERVAL = 3.0     # seconds between swarm optimisation cycles
PSO_NEIGHBOUR_WEIGHT = 0.4    # how much neighbour state influences decisions

# Decision variable bounds
PSO_GREEN_MIN = 5.0
PSO_GREEN_MAX = 35.0

# ── Emergency / VIP ─────────────────────────────────────────────────
EMERGENCY_TYPES = ["Ambulance", "Fire Truck", "Police"]
EMERGENCY_SPAWN_INTERVAL_MIN = 15.0   # min seconds between auto-spawns
EMERGENCY_SPAWN_INTERVAL_MAX = 35.0   # max seconds between auto-spawns
EMERGENCY_DETECTION_RADIUS = 500      # pixels – detect early for green wave prep
GREEN_WAVE_LOOKAHEAD = 4              # how many intersections ahead to coordinate

# ── Traffic Scenarios ────────────────────────────────────────────────
TRAFFIC_SCENARIOS = {
    "LOW":    {"spawn_interval": 2.0,  "max_vehicles": 25,  "label": "Low Traffic"},
    "NORMAL": {"spawn_interval": 1.2,  "max_vehicles": 60,  "label": "Normal Traffic"},
    "HIGH":   {"spawn_interval": 0.6,  "max_vehicles": 120, "label": "High Traffic"},
    "PEAK":   {"spawn_interval": 0.35, "max_vehicles": 200, "label": "Peak Hour"},
}
DEFAULT_SCENARIO = "NORMAL"

VIP_PROBABILITY = 0.0          # probability a *normal* spawn is emergency (auto-spawn handles this)

# ── Colour Palette (dark dashboard theme) ────────────────────────────
BG_DARK = (18, 22, 30)
BG_PANEL = (26, 32, 44)
BG_CARD = (34, 42, 56)
BG_CARD_HOVER = (44, 54, 70)
ROAD_COLOR = (50, 55, 65)
ROAD_MARKING = (90, 95, 105)
LANE_DIVIDER = (70, 75, 85)
GRASS_COLOR = (28, 38, 28)

TEXT_PRIMARY = (230, 235, 245)
TEXT_SECONDARY = (160, 170, 185)
TEXT_MUTED = (100, 110, 125)
TEXT_ACCENT = (80, 180, 255)

SIGNAL_RED = (220, 50, 50)
SIGNAL_YELLOW = (240, 200, 0)
SIGNAL_GREEN = (50, 210, 80)
SIGNAL_DIM = (45, 50, 60)

VEHICLE_NORMAL = (70, 130, 220)
VEHICLE_EMERGENCY_AMB = (255, 80, 60)
VEHICLE_EMERGENCY_FIRE = (255, 140, 0)
VEHICLE_EMERGENCY_POLICE = (100, 80, 255)
VEHICLE_OUTLINE = (20, 25, 35)

SIREN_COLOR_A = (255, 40, 40)
SIREN_COLOR_B = (60, 120, 255)

ACCENT_GREEN = (40, 200, 120)
ACCENT_RED = (230, 70, 70)
ACCENT_YELLOW = (240, 200, 40)
ACCENT_BLUE = (60, 150, 255)

BTN_PRIMARY = (40, 120, 220)
BTN_PRIMARY_HOVER = (60, 145, 245)
BTN_DANGER = (200, 55, 55)
BTN_DANGER_HOVER = (230, 80, 80)
BTN_SUCCESS = (35, 160, 80)
BTN_SUCCESS_HOVER = (55, 190, 110)

EMERGENCY_BANNER_BG = (80, 20, 20)
EMERGENCY_BANNER_BORDER = (220, 50, 50)

# ── UI Layout Proportions ───────────────────────────────────────────
SIDEBAR_WIDTH = 310           # right-side dashboard panel width
TOPBAR_HEIGHT = 48
BOTTOMBAR_HEIGHT = 48
PANEL_PADDING = 10
PANEL_RADIUS = 8

# ── Simulation Speed Multipliers ────────────────────────────────────
SPEED_OPTIONS = [0.5, 1.0, 2.0, 4.0]
DEFAULT_SPEED_INDEX = 1       # index into SPEED_OPTIONS -> 1.0x
