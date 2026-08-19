"""
main.py — Entry point for Swarm-Based Traffic Signal Simulation.

Orchestrates the game loop, state management, and event handling.
All logic is delegated to specialised modules:
  - traffic_manager.py  (simulation world)
  - signal_controller.py (signal FSM)
  - swarm_controller.py  (PSO optimisation)
  - emergency_controller.py (emergency priority)
  - metrics.py           (real-time stats)
  - ui.py                (dashboard rendering)
  - config.py            (all constants)
  - models.py            (data models)

Original project preserved in backup_original/ and swarm_light.py.
"""

import pygame
import sys
import config as cfg
from traffic_manager import TrafficManager
from ui import DashboardUI

# ── Application states ──────────────────────────────────────────────
STATE_MENU = 0
STATE_INSTRUCTIONS = 1
STATE_RUNNING = 2


def main():
    pygame.init()

    screen = pygame.display.set_mode(
        (cfg.INITIAL_WIDTH, cfg.INITIAL_HEIGHT),
        pygame.RESIZABLE
    )
    pygame.display.set_caption("Swarm Traffic Control — Adaptive Signal Simulation")
    clock = pygame.time.Clock()

    ui = DashboardUI(cfg.INITIAL_WIDTH, cfg.INITIAL_HEIGHT)
    world = None
    state = STATE_MENU
    speed_index = cfg.DEFAULT_SPEED_INDEX

    running = True
    while running:
        dt = clock.tick(cfg.FPS) / 1000.0

        # ── Event handling ──────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.VIDEORESIZE:
                w = max(cfg.MIN_WIDTH, event.w)
                h = max(cfg.MIN_HEIGHT, event.h)
                screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                ui.resize(w, h)
                if world:
                    ra = ui.road_area()
                    world.update_layout(ra[2], ra[3])

            if event.type == pygame.KEYDOWN:
                if state == STATE_RUNNING and world:
                    if event.key == pygame.K_SPACE:
                        world.paused = not world.paused

                    elif event.key == pygame.K_e:
                        world.spawn_vehicle(emergency=True)

                    elif event.key == pygame.K_s:
                        world.swarm_ctrl.active = not world.swarm_ctrl.active

                    elif event.key == pygame.K_r:
                        world.reset()

                    elif event.key == pygame.K_1:
                        world.set_scenario("LOW")
                    elif event.key == pygame.K_2:
                        world.set_scenario("NORMAL")
                    elif event.key == pygame.K_3:
                        world.set_scenario("HIGH")
                    elif event.key == pygame.K_4:
                        world.set_scenario("PEAK")

                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        speed_index = min(speed_index + 1, len(cfg.SPEED_OPTIONS) - 1)
                        world.set_speed(cfg.SPEED_OPTIONS[speed_index])
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        speed_index = max(speed_index - 1, 0)
                        world.set_speed(cfg.SPEED_OPTIONS[speed_index])

                    elif event.key == pygame.K_ESCAPE:
                        state = STATE_MENU

                elif state == STATE_INSTRUCTIONS:
                    if event.key == pygame.K_ESCAPE:
                        state = STATE_MENU

                elif state == STATE_MENU:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            if event.type == pygame.MOUSEBUTTONDOWN and state == STATE_MENU:
                mx, my = pygame.mouse.get_pos()
                buttons = ui.draw_menu(screen)
                for label, rect in buttons:
                    if rect.collidepoint(mx, my):
                        if "START" in label:
                            world = TrafficManager()
                            ra = ui.road_area()
                            world.update_layout(ra[2], ra[3])
                            speed_index = cfg.DEFAULT_SPEED_INDEX
                            state = STATE_RUNNING
                        elif "INSTRUCTION" in label:
                            state = STATE_INSTRUCTIONS
                        elif "EXIT" in label:
                            running = False

        if not running:
            break

        # ── Update & render ─────────────────────────────────────────
        if state == STATE_MENU:
            ui.draw_menu(screen)

        elif state == STATE_INSTRUCTIONS:
            ui.draw_instructions(screen)

        elif state == STATE_RUNNING and world:
            world.update(dt)
            ui.draw_simulation(screen, world, world.time)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()