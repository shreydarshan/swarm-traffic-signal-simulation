import pygame, sys, random, math

class Config:
    FPS = 30
    SCREEN_W = 700
    SCREEN_H = 700
    GRID_ROWS = 2
    GRID_COLS = 2

    VEHICLE_LENGTH = 14
    VEHICLE_WIDTH = 10

    BASE_SPEED_MIN = 90
    BASE_SPEED_MAX = 120
    EMERGENCY_SPEED_MULT = 1.5

    MIN_GREEN = 0.6
    YELLOW_TIME = 0.4
    MAX_GREEN = 4.0

    PREEMPT_RADIUS = 220
    SPAWN_INTERVAL = 0.8
    MAX_VEHICLES = 120
    STOP_DISTANCE = 50

    ROAD_HALF = 40
    LANE_OFFSET = 24

    VIP_PROBABILITY = 0.15

    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (200, 200, 200)
    RED = (220, 50, 50)
    GREEN = (50, 200, 50)
    YELLOW = (240, 200, 0)
    BLUE = (50, 50, 220)
    ORANGE = (255, 140, 0)
    SIREN = (0, 120, 255)
    ROAD = (60, 60, 60)


class Vehicle:
    def __init__(self):
        self.active = False

    def reset(self, pos, direction, speed, emergency, lane_center):
        self.x, self.y = pos
        self.dir = direction
        self.speed = speed * (Config.EMERGENCY_SPEED_MULT if emergency else 1.0)
        self.is_emergency = emergency
        self.lane_center = lane_center
        self.stopped = False
        self.wait_time = 0
        self.active = True

    def deactivate(self):
        self.active = False

    def update(self, dt):
        if self.stopped:
            self.wait_time += dt
            return

        step = self.speed * dt

        if self.dir == 'N':
            self.y -= step
            self.x = self.lane_center
        elif self.dir == 'S':
            self.y += step
            self.x = self.lane_center
        elif self.dir == 'E':
            self.x += step
            self.y = self.lane_center
        elif self.dir == 'W':
            self.x -= step
            self.y = self.lane_center

    def draw(self, surf, t):
        if not self.active:
            return
        w = Config.VEHICLE_WIDTH + 3 if self.is_emergency else Config.VEHICLE_WIDTH
        rect = pygame.Rect(0, 0, Config.VEHICLE_LENGTH, w)
        rect.center = (int(self.x), int(self.y))
        color = Config.ORANGE if self.is_emergency else Config.BLUE
        pygame.draw.rect(surf, color, rect)
        pygame.draw.rect(surf, Config.BLACK, rect, 1)
        if self.is_emergency:
            c = Config.SIREN if int(t * 6) % 2 == 0 else Config.WHITE
            pygame.draw.rect(surf, c, (rect.centerx - 3, rect.top - 3, 6, 2))


class Intersection:
    def __init__(self, center):
        self.center = center
        self.phase = 'NS'
        self.phase_start = 0
        self.yellow = False
        self.yellow_start = 0
        self.preempt_until = 0

    def decide(self, t, pressure):
        if t < self.preempt_until:
            return

        if self.yellow:
            if t - self.yellow_start >= Config.YELLOW_TIME:
                self.yellow = False
                self.phase = 'EW' if self.phase == 'NS' else 'NS'
                self.phase_start = t
            return

        if t - self.phase_start < Config.MIN_GREEN:
            return

        if pressure > 3 or t - self.phase_start > Config.MAX_GREEN:
            self.yellow = True
            self.yellow_start = t

    def preempt(self, t, direction, duration=4.0):
        axis = 'NS' if direction in ('N', 'S') else 'EW'
        self.phase = axis
        self.phase_start = t
        self.preempt_until = t + duration

    def draw(self, surf):
        x, y = self.center
        pygame.draw.rect(surf, Config.GRAY, (x - 20, y - 20, 40, 40))
        offs = {'N': (0, -28), 'S': (0, 28), 'E': (28, 0), 'W': (-28, 0)}
        for d, o in offs.items():
            cx, cy = x + o[0], y + o[1]
            axis = 'NS' if d in ('N', 'S') else 'EW'
            if self.phase == axis and not self.yellow:
                c = Config.GREEN
            elif self.yellow and self.phase == axis:
                c = Config.YELLOW
            else:
                c = Config.RED
            pygame.draw.circle(surf, c, (cx, cy), 6)


class World:
    def __init__(self):
        self.time = 0
        self.vehicles = []
        self.pool = [Vehicle() for _ in range(Config.MAX_VEHICLES)]
        self.spawn_timer = 0

        self.intersections = []
        self.lane_centers_v = []
        self.lane_centers_h = []

        sx = Config.SCREEN_W // (Config.GRID_COLS + 1)
        sy = Config.SCREEN_H // (Config.GRID_ROWS + 1)

        for r in range(Config.GRID_ROWS):
            for c in range(Config.GRID_COLS):
                cx = sx * (c + 1)
                cy = sy * (r + 1)
                self.intersections.append(Intersection((cx, cy)))
                self.lane_centers_v += [cx - Config.LANE_OFFSET, cx + Config.LANE_OFFSET]
                self.lane_centers_h += [cy - Config.LANE_OFFSET, cy + Config.LANE_OFFSET]

    def get_vehicle(self):
        for v in self.pool:
            if not v.active:
                return v
        return None

    def spawn_vehicle(self, forced=False):
        if len(self.vehicles) >= Config.MAX_VEHICLES:
            return

        margin = 20
        side = random.choice(['N', 'S', 'E', 'W'])

        if side == 'N':
            x = min(self.lane_centers_v)
            y = -margin
            d = 'S'
        elif side == 'S':
            x = max(self.lane_centers_v)
            y = Config.SCREEN_H + margin
            d = 'N'
        elif side == 'E':
            x = Config.SCREEN_W + margin
            y = max(self.lane_centers_h)
            d = 'W'
        else:
            x = -margin
            y = min(self.lane_centers_h)
            d = 'E'

        v = self.get_vehicle()
        if not v:
            return

        emergency = forced or random.random() < Config.VIP_PROBABILITY
        speed = random.uniform(Config.BASE_SPEED_MIN, Config.BASE_SPEED_MAX)
        lane_center = x if d in ('N', 'S') else y

        v.reset((x, y), d, speed, emergency, lane_center)
        self.vehicles.append(v)

    def find_intersection(self, v):
        best, bestd = None, 1e9
        for inter in self.intersections:
            ix, iy = inter.center
            if v.dir == 'N' and iy < v.y and abs(ix - v.x) < Config.ROAD_HALF:
                d = v.y - iy
            elif v.dir == 'S' and iy > v.y and abs(ix - v.x) < Config.ROAD_HALF:
                d = iy - v.y
            elif v.dir == 'E' and ix > v.x and abs(iy - v.y) < Config.ROAD_HALF:
                d = ix - v.x
            elif v.dir == 'W' and ix < v.x and abs(iy - v.y) < Config.ROAD_HALF:
                d = v.x - ix
            else:
                continue
            if d < bestd:
                best, bestd = inter, d
        return best, bestd

    def update(self, dt):
        self.time += dt
        self.spawn_timer += dt

        if self.spawn_timer >= Config.SPAWN_INTERVAL:
            self.spawn_timer = 0
            self.spawn_vehicle()

        for v in list(self.vehicles):
            if v.x < -200 or v.x > Config.SCREEN_W + 200 or v.y < -200 or v.y > Config.SCREEN_H + 200:
                v.deactivate()
                self.vehicles.remove(v)
                continue

            inter, dist = self.find_intersection(v)
            must_stop = False

            if inter and dist < Config.STOP_DISTANCE and not v.is_emergency:
                axis = 'NS' if v.dir in ('N', 'S') else 'EW'
                if inter.phase != axis or inter.yellow:
                    must_stop = True

            if v.is_emergency and inter and dist < Config.PREEMPT_RADIUS:
                inter.preempt(self.time, v.dir)

            v.stopped = must_stop
            v.update(dt)

        for inter in self.intersections:
            nearby = [v for v in self.vehicles
                      if math.hypot(v.x - inter.center[0], v.y - inter.center[1]) < 80]
            inter.decide(self.time, len(nearby))

    def draw(self, surf):
        surf.fill(Config.WHITE)

        for inter in self.intersections:
            cx, cy = inter.center
            pygame.draw.rect(surf, Config.ROAD,
                             (cx - Config.ROAD_HALF, 0,
                              Config.ROAD_HALF * 2, Config.SCREEN_H))
            pygame.draw.rect(surf, Config.ROAD,
                             (0, cy - Config.ROAD_HALF,
                              Config.SCREEN_W, Config.ROAD_HALF * 2))

        for x in self.lane_centers_v:
            pygame.draw.line(surf, Config.WHITE, (x, 0), (x, Config.SCREEN_H), 2)
        for y in self.lane_centers_h:
            pygame.draw.line(surf, Config.WHITE, (0, y), (Config.SCREEN_W, y), 2)

        for inter in self.intersections:
            inter.draw(surf)

        for v in self.vehicles:
            v.draw(surf, self.time)


MENU, INSTRUCTIONS, RUNNING = 0, 1, 2

pygame.init()
screen = pygame.display.set_mode((Config.SCREEN_W, Config.SCREEN_H))
pygame.display.set_caption("Swarm Traffic Simulation — Direction Locked Lanes")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
bigfont = pygame.font.SysFont(None, 44)


def draw_button(surf, txt, rect, base, hover, is_hover):
    color = hover if is_hover else base
    pygame.draw.rect(surf, color, rect, border_radius=10)
    label = bigfont.render(txt, True, Config.WHITE)
    surf.blit(label, (rect.x + (rect.w - label.get_width()) // 2,
                      rect.y + (rect.h - label.get_height()) // 2))


def draw_menu():
    screen.fill((235, 240, 250))
    title = bigfont.render("Swarm Traffic Simulation", True, (20, 40, 80))
    screen.blit(title, (Config.SCREEN_W // 2 - title.get_width() // 2, 140))
    mx, my = pygame.mouse.get_pos()
    buttons = [
        ("Start Simulation", pygame.Rect(Config.SCREEN_W // 2 - 170, 300, 340, 60), (40, 160, 80), (70, 190, 110)),
        ("Instructions", pygame.Rect(Config.SCREEN_W // 2 - 170, 380, 340, 60), (60, 120, 200), (100, 150, 240)),
        ("Exit", pygame.Rect(Config.SCREEN_W // 2 - 170, 460, 340, 60), (200, 60, 60), (240, 120, 120))
    ]
    for label, rect, base, hover in buttons:
        draw_button(screen, label, rect, base, hover, rect.collidepoint((mx, my)))
    return buttons


def draw_instructions():
    screen.fill((250, 250, 240))
    lines = [
        "Instructions:",
        "SPACE - Pause / Resume",
        "E - Spawn VIP Vehicle",
        "ESC - Return to Menu",
        "",
        "Each road has one incoming and one outgoing lane."
    ]
    y = 160
    for line in lines:
        screen.blit(font.render(line, True, (20, 30, 60)), (160, y))
        y += 36


def main():
    state = MENU
    world = None
    paused = False

    while True:
        dt = clock.tick(Config.FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN:
                if state == RUNNING:
                    if e.key == pygame.K_SPACE:
                        paused = not paused
                    elif e.key == pygame.K_e:
                        world.spawn_vehicle(True)
                    elif e.key == pygame.K_ESCAPE:
                        state = MENU
                elif state == INSTRUCTIONS and e.key == pygame.K_ESCAPE:
                    state = MENU

            if e.type == pygame.MOUSEBUTTONDOWN and state == MENU:
                mx, my = pygame.mouse.get_pos()
                buttons = draw_menu()
                if buttons[0][1].collidepoint((mx, my)):
                    world = World()
                    paused = False
                    state = RUNNING
                elif buttons[1][1].collidepoint((mx, my)):
                    state = INSTRUCTIONS
                elif buttons[2][1].collidepoint((mx, my)):
                    pygame.quit()
                    sys.exit()

        if state == MENU:
            draw_menu()
        elif state == INSTRUCTIONS:
            draw_instructions()
        elif state == RUNNING:
            if not paused:
                world.update(dt)
            world.draw(screen)
            screen.blit(font.render("SPACE: Pause | E: VIP | ESC: Menu",
                                     True, Config.BLACK),
                        (Config.SCREEN_W - 320, 10))

        pygame.display.flip()


if __name__ == "__main__":
    main()
    