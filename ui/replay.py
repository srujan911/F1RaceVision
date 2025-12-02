import pygame
import math
from typing import Dict, List

from core.telemetry_loader import load_race_telemetry, DriverTrace
from core.track_loader import load_track_svg


WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
FPS = 60

LEFT_PANEL_WIDTH = 240
RIGHT_PANEL_WIDTH = 300


# ------------------------ TEAM COLORS ------------------------

TEAM_COLORS = {
    "VER": (30, 65, 255), "PER": (30, 65, 255),
    "LEC": (255, 0, 0), "SAI": (255, 0, 0),
    "HAM": (0, 210, 190), "RUS": (0, 210, 190),
    "NOR": (245, 130, 10), "PIA": (245, 130, 10),
    "ALO": (0, 111, 98), "STR": (0, 111, 98),
    "OCO": (0, 144, 255), "GAS": (0, 144, 255),
    "ALB": (0, 82, 150), "SAR": (0, 82, 150),
    "MAG": (180, 180, 180), "HUL": (180, 180, 180),
    "TSU": (155, 0, 220), "DEV": (155, 0, 220),
    "BOT": (0, 190, 0), "ZHO": (0, 190, 0)
}


# ------------------------ SCREEN MAPPING ------------------------

def world_to_screen(px, py):
    """SVG track maps are normalized (0–1). Convert to pygame coordinates."""
    margin_left = LEFT_PANEL_WIDTH + 30
    margin_right = 30
    margin_top = 150
    margin_bottom = 50

    usable_w = WINDOW_WIDTH - margin_left - margin_right
    usable_h = WINDOW_HEIGHT - margin_top - margin_bottom

    sx = margin_left + px * usable_w
    sy = WINDOW_HEIGHT - (margin_bottom + py * usable_h)

    return int(sx), int(sy)


def convert_points(pt_list):
    return [world_to_screen(x, y) for x, y in pt_list]


# ------------------------ DRAWING TRACK ------------------------

def draw_track(screen, track):
    center = convert_points(track["centerline"])
    left = convert_points(track["left_edge"])
    right = convert_points(track["right_edge"])

    # Sector boundaries
    s1 = track["s1_index"]
    s2 = track["s2_index"]

    def slice_seg(seg, i1, i2):
        return seg[i1:i2]

    # S1
    pygame.draw.lines(screen, (255, 200, 0), False, slice_seg(left, 0, s1), 3)
    pygame.draw.lines(screen, (255, 200, 0), False, slice_seg(right, 0, s1), 3)

    # S2
    pygame.draw.lines(screen, (0, 180, 255), False, slice_seg(left, s1, s2), 3)
    pygame.draw.lines(screen, (0, 180, 255), False, slice_seg(right, s1, s2), 3)

    # S3
    pygame.draw.lines(screen, (255, 120, 0), False, slice_seg(left, s2, len(left)), 3)
    pygame.draw.lines(screen, (255, 120, 0), False, slice_seg(right, s2, len(right)), 3)

    # DRS Zones
    for (d1, d2) in track["drs_zones"]:
        pts = center[d1:d2]
        if len(pts) > 1:
            pygame.draw.lines(screen, (0, 255, 0), False, pts, 4)

    # Start/finish line
    sf = track["sf_index"]
    if sf is not None and sf < len(center) - 1:
        p1 = center[sf]
        p2 = center[sf + 1]
        pygame.draw.line(screen, (255, 255, 255), p1, p2, 5)

    # Labels
    font = pygame.font.SysFont("Arial", 20, bold=True)
    sx, sy = center[s1]
    screen.blit(font.render("S1", True, (255, 255, 255)), (sx + 10, sy))
    sx, sy = center[s2]
    screen.blit(font.render("S2", True, (255, 255, 255)), (sx + 10, sy))


# ------------------------ LEADERBOARD ------------------------

def compute_progress(tr: DriverTrace, idx: int):
    if idx < 0:
        return 0
    return tr.times[idx]


def compute_ranking(traces, indices):
    ranked = sorted(traces.keys(),
                    key=lambda code: compute_progress(traces[code], indices[code]),
                    reverse=True)
    return ranked


def draw_leaderboard(screen, ranking, font, selected, traces, indices):
    panel = pygame.Rect(10, 60, LEFT_PANEL_WIDTH - 20, 650)
    pygame.draw.rect(screen, (20, 20, 40), panel, border_radius=10)

    y = 85
    pos = 1

    for code in ranking:
        tr = traces[code]
        idx = indices[code]

        # Highlight selected driver
        if code == selected:
            pygame.draw.rect(screen, (60, 60, 120),
                             (14, y - 4, LEFT_PANEL_WIDTH - 28, 28), border_radius=6)

        # Position + code
        screen.blit(font.render(f"{pos:>2}. {code}", True, (255, 255, 255)), (25, y))

        pos += 1
        y += 30


# ------------------------ DRIVER PANELS ------------------------

def draw_driver_info(screen, tr, idx, font):
    x = WINDOW_WIDTH - RIGHT_PANEL_WIDTH - 10
    y = 60
    pygame.draw.rect(screen, (20, 20, 40), (x, y, RIGHT_PANEL_WIDTH, 200), border_radius=10)

    screen.blit(font.render("Driver Info", True, (255, 255, 0)), (x + 10, y + 10))
    screen.blit(font.render(f"Driver: {tr.driver_code}", True, (255, 255, 255)), (x + 10, y + 50))
    screen.blit(font.render(f"Speed: {tr.speeds[idx]:.1f} km/h", True, (255, 255, 255)), (x + 10, y + 80))
    screen.blit(font.render(f"Gear: {tr.gears[idx]}", True, (255, 255, 255)), (x + 10, y + 110))

    drson = tr.drs[idx] >= 8
    color = (0, 255, 0) if drson else (255, 70, 70)
    screen.blit(font.render(f"DRS: {'ON' if drson else 'OFF'}", True, color), (x + 10, y + 140))


def draw_lap_info(screen, tr, idx, font):
    lap = tr.lap_numbers[idx]
    total = max(tr.lap_numbers)

    x = WINDOW_WIDTH // 2 - 200
    screen.blit(font.render(f"LAP {lap}/{total}", True, (255, 255, 255)), (x, 40))


# ------------------------ MAIN REPLAY LOOP ------------------------

def run_replay(year, round_number, gp_name, circuit_name):
    pygame.init()

    # -------- Load Telemetry --------
    traces = load_race_telemetry(year, round_number)
    if not traces:
        print("Telemetry missing.")
        return

    # -------- Load Track SVG --------
    svg_path = f"assets/tracks/{year}_{gp_name}_{circuit_name}.svg"
    track = load_track_svg(svg_path)

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(f"F1 Replay – {gp_name}")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 22)

    # Time progression
    t = 0
    speed = 1.0
    dt = 0.20
    paused = False

    indices = {c: 0 for c in traces}
    selected = next(iter(traces))  # default selected

    running = True
    while running:
        ranking = compute_ranking(traces, indices)

        # -------- Handle Input --------
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_UP:
                    speed = min(speed + 0.5, 5)
                elif e.key == pygame.K_DOWN:
                    speed = max(speed - 0.5, 0.1)
                elif e.key == pygame.K_RIGHTBRACKET:
                    selected = ranking[(ranking.index(selected)+1) % len(ranking)]
                elif e.key == pygame.K_LEFTBRACKET:
                    selected = ranking[(ranking.index(selected)-1) % len(ranking)]

        # -------- Update Time --------
        if not paused:
            t += dt * speed
            for code, tr in traces.items():
                idx = indices[code]
                while idx + 1 < len(tr.times) and tr.times[idx] < t:
                    idx += 1
                indices[code] = idx

        # -------- DRAW EVERYTHING --------
        screen.fill((10, 10, 20))

        # Track
        draw_track(screen, track)

        # Drivers
        for code, tr in traces.items():
            idx = indices[code]
            px, py = tr.positions[idx]
            x, y = world_to_screen(px, py)

            col = TEAM_COLORS.get(code, (230, 230, 230))
            pygame.draw.circle(screen, col, (x, y), 5)

        # Panels
        draw_leaderboard(screen, ranking, font, selected, traces, indices)
        draw_driver_info(screen, traces[selected], indices[selected], font)
        draw_lap_info(screen, traces[selected], indices[selected], font)

        # GP Name on top
        gp_text = font.render(f"{gp_name.upper()}", True, (255, 255, 255))
        c_text = font.render(f"{circuit_name.upper()}", True, (200, 200, 200))

        screen.blit(gp_text, ((WINDOW_WIDTH - gp_text.get_width())//2, 5))
        screen.blit(c_text, ((WINDOW_WIDTH - c_text.get_width())//2, 35))

        # -------- Flip --------
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
