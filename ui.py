"""
ui.py — Professional traffic management dashboard.

Dark-theme dashboard with:
- Road network visualization (left)
- Clean status panels (right sidebar)
- Controls bar (bottom)
- Title bar (top)
- Emergency alert banners
- Swarm optimization status
"""

import pygame
import math
import config as cfg


class DashboardUI:
    """Renders the complete simulation interface."""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._init_fonts()

    def _init_fonts(self):
        pygame.font.init()
        try:
            self.font_title = pygame.font.SysFont("Segoe UI", 20, bold=True)
            self.font_subtitle = pygame.font.SysFont("Segoe UI", 13)
            self.font_panel_title = pygame.font.SysFont("Segoe UI", 14, bold=True)
            self.font_body = pygame.font.SysFont("Segoe UI", 12)
            self.font_small = pygame.font.SysFont("Segoe UI", 11)
            self.font_big = pygame.font.SysFont("Segoe UI", 28, bold=True)
            self.font_btn = pygame.font.SysFont("Segoe UI", 12, bold=True)
            self.font_metric = pygame.font.SysFont("Consolas", 13, bold=True)
            self.font_signal = pygame.font.SysFont("Consolas", 10)
            self.font_menu_title = pygame.font.SysFont("Segoe UI", 38, bold=True)
            self.font_menu_sub = pygame.font.SysFont("Segoe UI", 15)
            self.font_menu_btn = pygame.font.SysFont("Segoe UI", 17, bold=True)
            self.font_menu_body = pygame.font.SysFont("Segoe UI", 13)
            self.font_menu_key = pygame.font.SysFont("Consolas", 13, bold=True)
        except Exception:
            self.font_title = pygame.font.SysFont(None, 22)
            self.font_subtitle = pygame.font.SysFont(None, 15)
            self.font_panel_title = pygame.font.SysFont(None, 16)
            self.font_body = pygame.font.SysFont(None, 14)
            self.font_small = pygame.font.SysFont(None, 13)
            self.font_big = pygame.font.SysFont(None, 30)
            self.font_btn = pygame.font.SysFont(None, 14)
            self.font_metric = pygame.font.SysFont(None, 15)
            self.font_signal = pygame.font.SysFont(None, 12)
            self.font_menu_title = pygame.font.SysFont(None, 40)
            self.font_menu_sub = pygame.font.SysFont(None, 17)
            self.font_menu_btn = pygame.font.SysFont(None, 19)
            self.font_menu_body = pygame.font.SysFont(None, 15)
            self.font_menu_key = pygame.font.SysFont(None, 15)

    def resize(self, w, h):
        self.screen_w = w
        self.screen_h = h

    def road_area(self):
        return (0, cfg.TOPBAR_HEIGHT,
                self.screen_w - cfg.SIDEBAR_WIDTH,
                self.screen_h - cfg.TOPBAR_HEIGHT - cfg.BOTTOMBAR_HEIGHT)

    # ═══════════════════════════════════════════════════════════════
    #  MENU SCREEN
    # ═══════════════════════════════════════════════════════════════

    def draw_menu(self, surf):
        surf.fill(cfg.BG_DARK)
        w, h = self.screen_w, self.screen_h
        mx, my = pygame.mouse.get_pos()

        # ── Decorative top accent line ──
        for i in range(3):
            c = (30 + i * 8, 60 + i * 12, 130 + i * 15)
            pygame.draw.rect(surf, c, (0, i * 2, w, 2))

        # ── Title block ──
        cy = h // 2 - 185

        title = self.font_menu_title.render("SWARM TRAFFIC CONTROL CENTER", True, cfg.TEXT_PRIMARY)
        surf.blit(title, (w // 2 - title.get_width() // 2, cy))
        cy += 50

        sub = self.font_menu_sub.render(
            "Adaptive Signal Control  |  PSO Optimization  |  Emergency Green-Wave",
            True, cfg.TEXT_ACCENT)
        surf.blit(sub, (w // 2 - sub.get_width() // 2, cy))
        cy += 30

        # Divider
        pygame.draw.line(surf, (50, 60, 80), (w // 2 - 250, cy), (w // 2 + 250, cy), 1)
        cy += 20

        # ── Feature summary (compact) ──
        features = [
            "Decentralized swarm intelligence optimizes traffic signals in real-time",
            "Emergency/VIP vehicles receive coordinated green-wave priority corridors",
            "4-intersection network with adaptive phase control and queue management",
        ]
        for line in features:
            lbl = self.font_menu_body.render(line, True, cfg.TEXT_SECONDARY)
            surf.blit(lbl, (w // 2 - lbl.get_width() // 2, cy))
            cy += 22
        cy += 15

        # ── Controls preview (compact) ──
        pygame.draw.rect(surf, cfg.BG_CARD, (w // 2 - 220, cy, 440, 85), border_radius=8)
        ky = cy + 10
        controls = [
            ("SPACE", "Pause/Resume"),
            ("E", "Spawn Emergency Vehicle"),
            ("1-4", "Traffic Level"),
            ("+/-", "Speed"),
        ]
        kx = w // 2 - 200
        for key, desc in controls:
            key_lbl = self.font_menu_key.render(key, True, cfg.ACCENT_YELLOW)
            desc_lbl = self.font_menu_body.render(desc, True, cfg.TEXT_SECONDARY)
            surf.blit(key_lbl, (kx, ky))
            surf.blit(desc_lbl, (kx + 55, ky))
            kx += 210
            if kx > w // 2 + 180:
                kx = w // 2 - 200
                ky += 22
        cy += 100

        # ── Buttons ──
        buttons = []
        btn_data = [
            ("START SIMULATION", cfg.BTN_SUCCESS, cfg.BTN_SUCCESS_HOVER),
            ("INSTRUCTIONS", cfg.BTN_PRIMARY, cfg.BTN_PRIMARY_HOVER),
            ("EXIT", cfg.BTN_DANGER, cfg.BTN_DANGER_HOVER),
        ]
        btn_w, btn_h = 280, 46
        btn_gap = 14

        for i, (label, color, hover_color) in enumerate(btn_data):
            rect = pygame.Rect(w // 2 - btn_w // 2, cy + i * (btn_h + btn_gap), btn_w, btn_h)
            is_hover = rect.collidepoint(mx, my)
            c = hover_color if is_hover else color
            pygame.draw.rect(surf, c, rect, border_radius=8)
            if is_hover:
                pygame.draw.rect(surf, (255, 255, 255, 60), rect, 2, border_radius=8)
            lbl = self.font_menu_btn.render(label, True, cfg.TEXT_PRIMARY)
            surf.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                            rect.centery - lbl.get_height() // 2))
            buttons.append((label, rect))

        # Footer
        footer = self.font_small.render(
            "PBL Project  --  Swarm-Based Traffic Signal Simulation with Emergency Priority",
            True, cfg.TEXT_MUTED)
        surf.blit(footer, (w // 2 - footer.get_width() // 2, h - 35))

        return buttons

    # ═══════════════════════════════════════════════════════════════
    #  INSTRUCTIONS SCREEN
    # ═══════════════════════════════════════════════════════════════

    def draw_instructions(self, surf):
        surf.fill(cfg.BG_DARK)
        w, h = self.screen_w, self.screen_h

        title = self.font_menu_title.render("INSTRUCTIONS", True, cfg.TEXT_PRIMARY)
        surf.blit(title, (w // 2 - title.get_width() // 2, 40))

        sections = [
            ("CONTROLS", [
                ("SPACE", "Pause / Resume simulation"),
                ("E", "Spawn Emergency / VIP Vehicle"),
                ("S", "Toggle Swarm Optimization ON/OFF"),
                ("R", "Reset Simulation"),
                ("1-4", "Low / Normal / High / Peak Traffic"),
                ("+/-", "Adjust simulation speed"),
                ("ESC", "Return to Menu"),
            ]),
            ("HOW IT WORKS", [
                ("", "Each intersection has a traffic signal cycling NS/EW phases."),
                ("", "PSO swarm optimization adjusts green durations based on queue demand."),
                ("", "Emergency vehicles trigger priority green-wave corridors."),
                ("", "The system safely transitions signals for emergency passage."),
                ("", "After the emergency vehicle passes, normal control resumes."),
            ]),
        ]

        y = 100
        for section_title, items in sections:
            lbl = self.font_panel_title.render(section_title, True, cfg.TEXT_ACCENT)
            surf.blit(lbl, (w // 2 - 260, y))
            y += 26
            for key, desc in items:
                if key:
                    klbl = self.font_menu_key.render(key, True, cfg.ACCENT_YELLOW)
                    surf.blit(klbl, (w // 2 - 240, y))
                    dlbl = self.font_menu_body.render(desc, True, cfg.TEXT_SECONDARY)
                    surf.blit(dlbl, (w // 2 - 170, y))
                else:
                    dlbl = self.font_menu_body.render(desc, True, cfg.TEXT_SECONDARY)
                    surf.blit(dlbl, (w // 2 - 240, y))
                y += 22
            y += 14

        hint = self.font_body.render("Press ESC to return to menu", True, cfg.TEXT_MUTED)
        surf.blit(hint, (w // 2 - hint.get_width() // 2, h - 45))

    # ═══════════════════════════════════════════════════════════════
    #  MAIN SIMULATION VIEW
    # ═══════════════════════════════════════════════════════════════

    def draw_simulation(self, surf, world, sim_time):
        surf.fill(cfg.BG_DARK)
        self._draw_topbar(surf, world, sim_time)
        self._draw_road_network(surf, world, sim_time)
        self._draw_vehicles(surf, world, sim_time)
        self._draw_sidebar(surf, world, sim_time)
        self._draw_bottombar(surf, world)

        if world.emergency_ctrl.get_active_event_count() > 0:
            self._draw_emergency_banner(surf, world, sim_time)

        if world.paused:
            self._draw_pause_overlay(surf)

    # ── Top bar ─────────────────────────────────────────────────────

    def _draw_topbar(self, surf, world, sim_time):
        bar_rect = pygame.Rect(0, 0, self.screen_w, cfg.TOPBAR_HEIGHT)
        pygame.draw.rect(surf, cfg.BG_PANEL, bar_rect)
        pygame.draw.line(surf, (40, 50, 65), (0, cfg.TOPBAR_HEIGHT - 1),
                         (self.screen_w, cfg.TOPBAR_HEIGHT - 1), 1)

        title = self.font_title.render("SWARM TRAFFIC CONTROL CENTER", True, cfg.TEXT_PRIMARY)
        surf.blit(title, (14, 13))

        minutes = int(sim_time) // 60
        seconds = int(sim_time) % 60
        time_str = f"TIME {minutes:02d}:{seconds:02d}"
        time_lbl = self.font_metric.render(time_str, True, cfg.TEXT_ACCENT)
        surf.blit(time_lbl, (self.screen_w - cfg.SIDEBAR_WIDTH - 160, 16))

        speed_str = f"{world.speed_multiplier:.1f}x"
        speed_lbl = self.font_metric.render(speed_str, True, cfg.ACCENT_YELLOW)
        surf.blit(speed_lbl, (self.screen_w - cfg.SIDEBAR_WIDTH - 50, 16))

    # ── Road network ────────────────────────────────────────────────

    def _draw_road_network(self, surf, world, sim_time):
        rx, ry, rw, rh = self.road_area()

        # Background
        pygame.draw.rect(surf, cfg.GRASS_COLOR, (rx, ry, rw, rh))

        road_cols = world.get_road_columns()
        road_rows = world.get_road_rows()

        # Vertical roads
        for col_x in road_cols:
            pygame.draw.rect(surf, cfg.ROAD_COLOR,
                             (col_x - cfg.ROAD_HALF_WIDTH, ry,
                              cfg.ROAD_HALF_WIDTH * 2, rh))

        # Horizontal roads
        for row_y in road_rows:
            pygame.draw.rect(surf, cfg.ROAD_COLOR,
                             (rx, row_y - cfg.ROAD_HALF_WIDTH,
                              rw, cfg.ROAD_HALF_WIDTH * 2))

        # Dashed lane dividers
        dash_len, dash_gap = 12, 10
        for col_x in road_cols:
            y = ry
            while y < ry + rh:
                pygame.draw.line(surf, cfg.LANE_DIVIDER,
                                 (col_x, y), (col_x, min(y + dash_len, ry + rh)), 1)
                y += dash_len + dash_gap
        for row_y in road_rows:
            x = rx
            while x < rx + rw:
                pygame.draw.line(surf, cfg.LANE_DIVIDER,
                                 (x, row_y), (min(x + dash_len, rx + rw), row_y), 1)
                x += dash_len + dash_gap

        # Intersections and signals
        for inter in world.intersections:
            self._draw_intersection(surf, inter, sim_time)

    def _draw_intersection(self, surf, inter, sim_time):
        cx, cy = inter.center
        sz = cfg.INTERSECTION_SIZE

        # Intersection box
        pygame.draw.rect(surf, cfg.ROAD_COLOR, (cx - sz, cy - sz, sz * 2, sz * 2))

        # Stop lines
        sl_color = (160, 165, 175)
        offset = cfg.STOP_LINE_OFFSET
        pygame.draw.line(surf, sl_color, (cx - sz, cy - offset), (cx, cy - offset), 2)
        pygame.draw.line(surf, sl_color, (cx, cy + offset), (cx + sz, cy + offset), 2)
        pygame.draw.line(surf, sl_color, (cx + offset, cy - sz), (cx + offset, cy), 2)
        pygame.draw.line(surf, sl_color, (cx - offset, cy), (cx - offset, cy + sz), 2)

        # Traffic lights
        self._draw_signal_lights(surf, inter, cx, cy, sim_time)

        # Label
        label = self.font_signal.render(f"I{inter.index + 1}", True, (140, 145, 155))
        surf.blit(label, (cx - label.get_width() // 2, cy - label.get_height() // 2))

    def _draw_signal_lights(self, surf, inter, cx, cy, sim_time):
        state = inter.signal_state
        positions = {
            'N': (cx - 9, cy - cfg.STOP_LINE_OFFSET - 15),
            'S': (cx + 3, cy + cfg.STOP_LINE_OFFSET + 4),
            'E': (cx + cfg.STOP_LINE_OFFSET + 4, cy - 9),
            'W': (cx - cfg.STOP_LINE_OFFSET - 15, cy + 3),
        }

        for direction, (lx, ly) in positions.items():
            axis = 'NS' if direction in ('N', 'S') else 'EW'

            if axis == 'NS':
                if state == cfg.SIG_NS_GREEN:
                    active = 'green'
                elif state == cfg.SIG_NS_YELLOW:
                    active = 'yellow'
                else:
                    active = 'red'
            else:
                if state == cfg.SIG_EW_GREEN:
                    active = 'green'
                elif state == cfg.SIG_EW_YELLOW:
                    active = 'yellow'
                else:
                    active = 'red'

            # Housing
            pygame.draw.rect(surf, (20, 20, 25),
                             (lx - 1, ly - 1, 13, 13), border_radius=2)

            center = (lx + 5, ly + 5)
            r = 4

            if active == 'green':
                pygame.draw.circle(surf, cfg.SIGNAL_GREEN, center, r)
                glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*cfg.SIGNAL_GREEN, 35), (r * 2, r * 2), r * 2)
                surf.blit(glow, (center[0] - r * 2, center[1] - r * 2))
            elif active == 'yellow':
                pygame.draw.circle(surf, cfg.SIGNAL_YELLOW, center, r)
                glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*cfg.SIGNAL_YELLOW, 35), (r * 2, r * 2), r * 2)
                surf.blit(glow, (center[0] - r * 2, center[1] - r * 2))
            else:
                pygame.draw.circle(surf, cfg.SIGNAL_RED, center, r)

    # ── Vehicles ────────────────────────────────────────────────────

    def _draw_vehicles(self, surf, world, sim_time):
        for v in world.vehicles:
            if not v.active:
                continue
            self._draw_vehicle(surf, v, sim_time)

    def _draw_vehicle(self, surf, v, sim_time):
        if v.is_emergency:
            self._draw_emergency_vehicle(surf, v, sim_time)
        else:
            if v.direction in ('N', 'S'):
                w, h = cfg.VEHICLE_WIDTH, cfg.VEHICLE_LENGTH
            else:
                w, h = cfg.VEHICLE_LENGTH, cfg.VEHICLE_WIDTH
            rect = pygame.Rect(0, 0, w, h)
            rect.center = (int(v.x), int(v.y))
            pygame.draw.rect(surf, cfg.VEHICLE_NORMAL, rect, border_radius=2)
            pygame.draw.rect(surf, cfg.VEHICLE_OUTLINE, rect, 1, border_radius=2)

    def _draw_emergency_vehicle(self, surf, v, sim_time):
        if v.direction in ('N', 'S'):
            w, h = cfg.EMERGENCY_VEHICLE_WIDTH, cfg.EMERGENCY_VEHICLE_LENGTH
        else:
            w, h = cfg.EMERGENCY_VEHICLE_LENGTH, cfg.EMERGENCY_VEHICLE_WIDTH

        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(v.x), int(v.y))

        if v.emergency_type == "Ambulance":
            body = cfg.VEHICLE_EMERGENCY_AMB
        elif v.emergency_type == "Fire Truck":
            body = cfg.VEHICLE_EMERGENCY_FIRE
        else:
            body = cfg.VEHICLE_EMERGENCY_POLICE

        pygame.draw.rect(surf, body, rect, border_radius=3)
        pygame.draw.rect(surf, cfg.VEHICLE_OUTLINE, rect, 1, border_radius=3)

        # Siren
        phase = int(sim_time * 8) % 2
        c1 = cfg.SIREN_COLOR_A if phase == 0 else cfg.SIREN_COLOR_B
        c2 = cfg.SIREN_COLOR_B if phase == 0 else cfg.SIREN_COLOR_A
        if v.direction in ('N', 'S'):
            pygame.draw.circle(surf, c1, (rect.centerx - 3, rect.top + 2), 2)
            pygame.draw.circle(surf, c2, (rect.centerx + 3, rect.top + 2), 2)
        else:
            pygame.draw.circle(surf, c1, (rect.left + 2, rect.centery - 3), 2)
            pygame.draw.circle(surf, c2, (rect.left + 2, rect.centery + 3), 2)

        # Glow
        glow_size = 28 + int(math.sin(sim_time * 10) * 5)
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*body[:3], 20), (glow_size, glow_size), glow_size)
        surf.blit(glow_surf, (int(v.x) - glow_size, int(v.y) - glow_size))

    # ── Sidebar ─────────────────────────────────────────────────────

    def _draw_sidebar(self, surf, world, sim_time):
        sx = self.screen_w - cfg.SIDEBAR_WIDTH
        sy = cfg.TOPBAR_HEIGHT
        sw = cfg.SIDEBAR_WIDTH
        sh = self.screen_h - cfg.TOPBAR_HEIGHT - cfg.BOTTOMBAR_HEIGHT

        pygame.draw.rect(surf, cfg.BG_PANEL, (sx, sy, sw, sh))
        pygame.draw.line(surf, (40, 50, 65), (sx, sy), (sx, sy + sh), 1)

        pad = cfg.PANEL_PADDING
        y = sy + pad
        pw = sw - pad * 2

        # ── TRAFFIC ─────────────────────────────────────────────────
        m = world.metrics
        y = self._draw_panel(surf, "TRAFFIC", sx + pad, y, pw, [
            ("Active", f"{m.active_vehicles}"),
            ("Completed", f"{m.total_completed}"),
            ("Avg Wait", f"{m.avg_wait_time:.1f}s"),
            ("Throughput", f"{m.throughput:.0f}/min"),
            ("Congestion", m.congestion_level),
        ])
        y += 8

        # ── SIGNALS ─────────────────────────────────────────────────
        signal_items = []
        for inter in world.intersections:
            state_name = cfg.SIGNAL_STATE_NAMES.get(inter.signal_state, "?")
            remaining = inter.remaining_green(sim_time)
            timer = f"{remaining:.0f}s" if remaining > 0 else ""
            preempt = " !" if inter.preempt_active else ""
            q = inter.ns_queue + inter.ew_queue
            signal_items.append(
                (f"I{inter.index + 1}{preempt}",
                 f"{state_name} {timer} Q:{q}")
            )
        y = self._draw_panel(surf, "SIGNALS", sx + pad, y, pw, signal_items)
        y += 8

        # ── SWARM CONTROL ───────────────────────────────────────────
        sc = world.swarm_ctrl
        status = "ACTIVE" if sc.active else "OFF"
        y = self._draw_panel(surf, "SWARM CONTROL", sx + pad, y, pw, [
            ("Status", status),
            ("Agents", f"{len(world.intersections)}"),
            ("Particles", f"{cfg.PSO_NUM_PARTICLES}"),
            ("Cycle", f"{sc.update_cycle}"),
            ("Best Cost", f"{sc.get_best_cost():.1f}"),
            ("Avg Cost", f"{sc.get_average_cost():.1f}"),
        ])
        y += 8

        # ── EMERGENCY ───────────────────────────────────────────────
        ec = world.emergency_ctrl
        events = ec.get_active_events()
        emerg_items = [
            ("Active", f"{len(events)}"),
            ("Spawned", f"{m.emergency_spawned}"),
            ("Avg Resp", f"{ec.get_average_response_time():.1f}s"),
        ]
        for evt in events[:2]:
            v = evt.vehicle
            route_str = "->".join(f"I{idx + 1}" for idx in evt.route[:4])
            name = f"{v.emergency_type[:4]}-{v.id % 100:02d}"
            emerg_items.append((name, f"{route_str} [{evt.detection_method}]"))

        highlight = len(events) > 0
        y = self._draw_panel(surf, "EMERGENCY", sx + pad, y, pw,
                              emerg_items, highlight=highlight)

    def _draw_panel(self, surf, title, x, y, w, items, highlight=False):
        pad = 7
        row_h = 19
        title_h = 24
        panel_h = title_h + len(items) * row_h + pad * 2

        bg = cfg.EMERGENCY_BANNER_BG if highlight else cfg.BG_CARD
        pygame.draw.rect(surf, bg, (x, y, w, panel_h), border_radius=cfg.PANEL_RADIUS)
        if highlight:
            pygame.draw.rect(surf, cfg.EMERGENCY_BANNER_BORDER,
                             (x, y, w, panel_h), 1, border_radius=cfg.PANEL_RADIUS)

        title_color = cfg.ACCENT_RED if highlight else cfg.TEXT_ACCENT
        title_lbl = self.font_panel_title.render(title, True, title_color)
        surf.blit(title_lbl, (x + pad, y + pad))

        iy = y + title_h + pad
        for key, value in items:
            klbl = self.font_body.render(key, True, cfg.TEXT_SECONDARY)
            vlbl = self.font_metric.render(str(value), True, cfg.TEXT_PRIMARY)
            surf.blit(klbl, (x + pad, iy))
            surf.blit(vlbl, (x + w - pad - vlbl.get_width(), iy))
            iy += row_h

        return y + panel_h

    # ── Bottom bar ──────────────────────────────────────────────────

    def _draw_bottombar(self, surf, world):
        bar_y = self.screen_h - cfg.BOTTOMBAR_HEIGHT
        pygame.draw.rect(surf, cfg.BG_PANEL, (0, bar_y, self.screen_w, cfg.BOTTOMBAR_HEIGHT))
        pygame.draw.line(surf, (40, 50, 65), (0, bar_y), (self.screen_w, bar_y), 1)

        pad = 12
        x = pad
        cy = bar_y + 15

        scenario = cfg.TRAFFIC_SCENARIOS[world.scenario]
        lbl = self.font_btn.render(f"Traffic: {scenario['label']}", True, cfg.TEXT_ACCENT)
        surf.blit(lbl, (x, cy)); x += lbl.get_width() + 25

        lbl = self.font_btn.render(f"Speed: {world.speed_multiplier:.1f}x", True, cfg.ACCENT_YELLOW)
        surf.blit(lbl, (x, cy)); x += lbl.get_width() + 25

        swarm_on = world.swarm_ctrl.active
        lbl = self.font_btn.render(f"Swarm: {'ON' if swarm_on else 'OFF'}",
                                    True, cfg.ACCENT_GREEN if swarm_on else cfg.ACCENT_RED)
        surf.blit(lbl, (x, cy)); x += lbl.get_width() + 25

        if world.paused:
            lbl = self.font_btn.render("PAUSED", True, cfg.ACCENT_YELLOW)
            surf.blit(lbl, (x, cy))

        hint = self.font_small.render(
            "SPACE:Pause  E:Emergency  S:Swarm  R:Reset  1-4:Traffic  +/-:Speed  ESC:Menu",
            True, cfg.TEXT_MUTED)
        surf.blit(hint, (self.screen_w - hint.get_width() - pad, cy + 1))

    # ── Emergency banner ────────────────────────────────────────────

    def _draw_emergency_banner(self, surf, world, sim_time):
        events = world.emergency_ctrl.get_active_events()
        if not events:
            return

        rx, ry, rw, rh = self.road_area()
        banner_h = 30
        pulse = int(abs(math.sin(sim_time * 4)) * 25)
        bg = (75 + pulse, 18, 18)
        pygame.draw.rect(surf, bg, (rx, ry, rw, banner_h))
        pygame.draw.line(surf, cfg.SIGNAL_RED, (rx, ry + banner_h - 1),
                         (rx + rw, ry + banner_h - 1), 2)

        evt = events[0]
        v = evt.vehicle
        route_str = " -> ".join(f"I{idx + 1}" for idx in evt.route[:4])
        text = (f"EMERGENCY PRIORITY -- {v.emergency_type} #{v.id % 100:02d}  "
                f"Route: {route_str}  "
                f"[{evt.detection_method}]  "
                f"GREEN WAVE: {'ACTIVE' if evt.green_wave_active else 'PENDING'}")
        lbl = self.font_body.render(text, True, cfg.TEXT_PRIMARY)
        surf.blit(lbl, (rx + 10, ry + 7))

    # ── Pause overlay ───────────────────────────────────────────────

    def _draw_pause_overlay(self, surf):
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surf.blit(overlay, (0, 0))

        label = self.font_big.render("PAUSED", True, cfg.TEXT_PRIMARY)
        surf.blit(label, (self.screen_w // 2 - label.get_width() // 2,
                          self.screen_h // 2 - label.get_height() // 2))
        hint = self.font_body.render("Press SPACE to resume", True, cfg.TEXT_SECONDARY)
        surf.blit(hint, (self.screen_w // 2 - hint.get_width() // 2,
                          self.screen_h // 2 + 30))
