import math
from typing import Dict, List, Tuple
import threading
import pygame
import fastf1
import os
import pandas
import bisect
from concurrent.futures import ThreadPoolExecutor
from core.telemetry_loader import DriverTrace

# ============================================================
#                      CONSTANTS & COLORS
# ============================================================

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
FPS = 60
LEFT_PANEL_WIDTH = 240
RIGHT_PANEL_WIDTH = 300

C_BLACK = (12, 12, 20)
C_WHITE = (255, 255, 255)
C_YELLOW = (255, 220, 0)
C_CYAN = (0, 200, 255)
C_ORANGE = (255, 120, 0)
C_GREY = (200, 200, 200)
C_DRS_ON = (0, 255, 0)
C_DRS_OFF = (255, 70, 70)

TYRE_COLORS = {
    "SOFT": (255, 60, 60),
    "MEDIUM": (255, 220, 0),
    "HARD": (255, 255, 255),
    "INTERMEDIATE": (0, 255, 0),
    "WET": (100, 150, 255),
    "UNKNOWN": (180, 180, 180)
}

# ============================================================
#                   UTILITY FUNCTIONS (TRACK OK)
# ============================================================

def compute_bounds(traces: Dict[str, DriverTrace]) -> Tuple[float, float, float, float]:
    xs, ys = [], []
    for tr in traces.values():
        xs.extend([p[0] for p in tr.positions])
        ys.extend([p[1] for p in tr.positions])
    return min(xs), max(xs), min(ys), max(ys)


def world_to_screen(x: float, y: float, bounds) -> Tuple[int, int]:
    min_x, max_x, min_y, max_y = bounds
    range_x = max_x - min_x if max_x != min_x else 1.0
    range_y = max_y - min_y if max_y != min_y else 1.0

    nx = (x - min_x) / range_x
    ny = (y - min_y) / range_y

    margin_left = LEFT_PANEL_WIDTH + 50
    margin_right = RIGHT_PANEL_WIDTH + 50
    margin_top = 50
    margin_bottom = 50

    usable_w = WINDOW_WIDTH - margin_left - margin_right
    usable_h = WINDOW_HEIGHT - margin_top - margin_bottom

    sx = margin_left + nx * usable_w
    sy = WINDOW_HEIGHT - (margin_bottom + ny * usable_h)
    return int(sx), int(sy)


def build_track_geometry(traces: Dict[str, DriverTrace], bounds):
    first_driver = next(iter(traces.values()))
    centerline_world_source = first_driver.positions

    if hasattr(first_driver, 'lap_numbers') and first_driver.lap_numbers:
        laps = first_driver.lap_numbers
        lap_to_use = next((lap for lap in [2, 3, 1] if lap in laps), None)
        if lap_to_use is not None:
            lap_positions = [first_driver.positions[i]
                             for i in range(len(laps)) if laps[i] == lap_to_use]
            if lap_positions:
                centerline_world_source = lap_positions

    step = max(1, len(centerline_world_source) // 1000)
    centerline_world = centerline_world_source[::step]

    if len(centerline_world) < 3:
        return [], {}

    centerline_screen = [world_to_screen(x, y, bounds) for (x, y) in centerline_world]

    n = len(centerline_screen)
    s2_idx = n // 3
    s3_idx = 2 * n // 3

    markers = {
        "s1_line": centerline_screen[0],
        "s2_line": centerline_screen[s2_idx],
        "s3_line": centerline_screen[s3_idx],
        "s1_label_pos": (centerline_screen[0][0] - 50, centerline_screen[0][1] - 10),
        "s2_label_pos": (centerline_screen[s2_idx][0] + 20, centerline_screen[s2_idx][1]),
        "s3_label_pos": (centerline_screen[s3_idx][0] + 20, centerline_screen[s3_idx][1]),
    }

    return centerline_screen, markers

# ============================================================
#                   DATA PROCESSING (FIXED)
# ============================================================

def compute_ranking_data(traces: Dict[str, DriverTrace], indices: Dict[str, int]) -> List[Dict]:
    ranking = []
    for code, tr in traces.items():
        idx = indices.get(code, 0)
        if idx >= len(tr.distances):
            continue
        ranking.append({
            "code": code,
            "progress": tr.distances[idx],
            "lap": tr.lap_numbers[idx],
            "current_tyre": tr.tyres[idx],
            "speed": tr.speeds[idx],
            "trace": tr
        })

    ranking.sort(key=lambda x: x["progress"], reverse=True)

    if not ranking:
        return []

    out = []
    out.append({
        "position": 1,
        "code": ranking[0]["code"],
        "gap_to_ahead": "",
        "current_tyre": ranking[0]["current_tyre"],
        "trace": ranking[0]["trace"]
    })

    for i in range(1, len(ranking)):
        ahead = ranking[i - 1]
        cur = ranking[i]
        dgap = ahead["progress"] - cur["progress"]
        speed_mps = max(10, ahead["speed"] / 3.6)
        tgap = dgap / speed_mps
        out.append({
            "position": i + 1,
            "code": cur["code"],
            "gap_to_ahead": f"+{tgap:.2f}",
            "current_tyre": cur["current_tyre"],
            "trace": cur["trace"]
        })

    return out


def process_driver(session, driver_number):
    try:
        info = session.get_driver(driver_number)
        code = info["Abbreviation"]
        team_color = info["TeamColor"]

        laps = session.laps.pick_drivers([driver_number])
        if laps.empty:
            return None, None, None

        merged_all = []

        # ----------------------------------------------------
        # PROCESS EACH LAP SEPARATELY (car_data + pos_data)
        # ----------------------------------------------------
        for _, lap in laps.iterlaps():
            car = lap.get_car_data()
            pos = lap.get_pos_data()

            if car.empty or pos.empty:
                continue

            # Ensure both have timedelta SessionTime
            car["SessionTime"] = pandas.to_timedelta(car["SessionTime"], errors="coerce")
            pos["SessionTime"] = pandas.to_timedelta(pos["SessionTime"], errors="coerce")

            car = car.sort_values("SessionTime")
            pos = pos.sort_values("SessionTime")

            # merge_asof gives best alignment for real-time telemetry
            tel = pandas.merge_asof(
                car,
                pos,
                on="SessionTime",
                direction="nearest",
                tolerance=pandas.Timedelta("100ms")
            )

            # Drop rows where X/Y is missing
            tel.dropna(subset=["X", "Y"], inplace=True)

            # Assign lap number to each row
            tel["LapNumber"] = lap["LapNumber"]

            merged_all.append(tel)

        if not merged_all:
            print(f"[WARNING] No valid telemetry for driver {code}")
            return None, None, None

        # ----------------------------------------------------
        # CONCATENATE ALL LAP TELEMETRY
        # ----------------------------------------------------
        tel = pandas.concat(merged_all, ignore_index=True)
        tel = tel.sort_values("SessionTime").reset_index(drop=True)

        # ----------------------------------------------------
        # EXTRACT CONTINUOUS TIME
        # ----------------------------------------------------
        times = tel["SessionTime"].dt.total_seconds().tolist()

        # ----------------------------------------------------
        # CONTINUOUS DISTANCE FROM X/Y
        # ----------------------------------------------------
        distances = [0.0]
        for i in range(1, len(tel)):
            x1, y1 = tel["X"].iloc[i - 1], tel["Y"].iloc[i - 1]
            x2, y2 = tel["X"].iloc[i], tel["Y"].iloc[i]
            d = math.dist((x1, y1), (x2, y2))
            distances.append(distances[-1] + d)

        # ----------------------------------------------------
        # SECTOR TIMES PER LAP
        # ----------------------------------------------------
        s1 = []
        s2 = []
        s3 = []

        for lapnum in tel["LapNumber"]:
            lap = laps[laps["LapNumber"] == lapnum]
            if lap.empty:
                s1.append(0); s2.append(0); s3.append(0)
                continue

            lp = lap.iloc[0]
            s1_val = lp["Sector1Time"].total_seconds() if lp["Sector1Time"] else 0
            s2_val = lp["Sector2Time"].total_seconds() if lp["Sector2Time"] else 0
            s3_val = lp["Sector3Time"].total_seconds() if lp["Sector3Time"] else 0
            s1.append(s1_val)
            s2.append(s2_val)
            s3.append(s3_val)

        sectors = list(zip(s1, s2, s3))

        # ----------------------------------------------------
        # TYRES PER LAP → expand to full telemetry length
        # ----------------------------------------------------
        tyre_map = laps.set_index("LapNumber")["Compound"].fillna("UNKNOWN").to_dict()
        tyres = [tyre_map.get(lapnum, "UNKNOWN") for lapnum in tel["LapNumber"]]

        # ----------------------------------------------------
        # BUILD TRACE OBJECT
        # ----------------------------------------------------
        tr = DriverTrace(
            driver_code=code,
            positions=list(zip(tel["X"], tel["Y"])),
            times=times,
            speeds=tel["Speed"].fillna(0).tolist(),
            gears=tel["nGear"].fillna(0).astype(int).tolist(),
            drs=tel["DRS"].fillna(0).tolist(),
            tyres=tyres,
            distances=distances,
            sectors=sectors,
            lap_numbers=tel["LapNumber"].astype(int).tolist(),
            pit_status=tel["Status"].fillna("OnTrack").tolist()
        )

        return code, tr, team_color

    except Exception as e:
        print(f"[ERROR] Failed driver {driver_number}: {e}")
        return None, None, None




# ============================================================
#                    UI DRAWING FUNCTIONS
# ============================================================

def draw_leaderboard(surface, ranked_data, font, selected):
    surface.fill(C_BLACK)
    y = 60

    for item in ranked_data:
        pos = item["position"]
        code = item["code"]
        gap = item["gap_to_ahead"]
        tr = item["trace"]

        if code == selected:
            col = pygame.Color(f"#{tr.team_color}") if tr.team_color else (80, 80, 80)
            pygame.draw.rect(surface, col, (10, y - 2, LEFT_PANEL_WIDTH - 20, 26), border_radius=6)

        surface.blit(font.render(f"{pos}", True, C_GREY), (20, y))
        t = code + (f" {gap}" if pos > 1 else "")
        surface.blit(font.render(t, True, C_WHITE), (55, y))

        tyre = item["current_tyre"]
        tcol = TYRE_COLORS.get(tyre, TYRE_COLORS["UNKNOWN"])
        surface.blit(font.render(tyre[0], True, tcol), (190, y))

        y += 30


def draw_driver_info(screen, font, tr, idx):
    x = WINDOW_WIDTH - RIGHT_PANEL_WIDTH + 10
    y = 60

    color = pygame.Color(f"#{tr.team_color}") if tr.team_color else (80, 80, 80)
    pygame.draw.rect(screen, color, (x, y, RIGHT_PANEL_WIDTH - 20, 40), border_radius=6)

    title = pygame.font.SysFont("Arial", 24, bold=True)
    screen.blit(title.render(tr.driver_code, True, C_WHITE), (x + 10, y + 5))

    y += 60

    speed = tr.speeds[idx]
    gear = tr.gears[idx]
    drs_on = tr.drs[idx] >= 10

    screen.blit(font.render(f"Speed: {int(speed)} km/h", True, C_WHITE), (x, y))
    screen.blit(font.render(f"Gear: {gear}", True, C_WHITE), (x, y + 30))

    screen.blit(
        font.render("DRS: ON" if drs_on else "DRS: OFF",
                    True, C_DRS_ON if drs_on else C_DRS_OFF),
        (x, y + 60)
    )


def draw_lap_info(screen, font, tr, idx, total_laps):
    x = LEFT_PANEL_WIDTH + 40
    y = WINDOW_HEIGHT - 40

    lap = tr.lap_numbers[idx]
    s1, s2, s3 = tr.sectors[idx]

    screen.blit(font.render(f"LAP {lap}/{total_laps}", True, C_WHITE), (x, y))
    screen.blit(font.render(f"S1: {s1:.3f}", True, C_YELLOW), (x + 150, y))
    screen.blit(font.render(f"S2: {s2:.3f}", True, C_CYAN), (x + 300, y))
    screen.blit(font.render(f"S3: {s3:.3f}", True, C_ORANGE), (x + 450, y))


def draw_hud(screen, font, time, speed, paused, gp, circuit):
    status = "PAUSED" if paused else f"{speed:.1f}x"
    screen.blit(font.render(f"Time: {time:.1f}s | Speed: {status}", True, C_WHITE),
                (LEFT_PANEL_WIDTH + 40, 20))

    tfont = pygame.font.SysFont("Arial", 22, bold=True)
    text = tfont.render(f"{gp}: {circuit}", True, C_WHITE)
    screen.blit(text, (WINDOW_WIDTH / 2 - text.get_width() / 2, 20))


def draw_track_and_cars(screen, centerline, markers, traces, indices, bounds):
    pygame.draw.aalines(screen, C_WHITE, True, centerline, 2)

    f = pygame.font.SysFont("Arial", 16, bold=True)
    pygame.draw.circle(screen, C_YELLOW, markers["s1_line"], 8)
    pygame.draw.circle(screen, C_CYAN, markers["s2_line"], 8)
    pygame.draw.circle(screen, C_ORANGE, markers["s3_line"], 8)

    screen.blit(f.render("S1", True, C_YELLOW), markers["s1_label_pos"])
    screen.blit(f.render("S2", True, C_CYAN), markers["s2_label_pos"])
    screen.blit(f.render("S3", True, C_ORANGE), markers["s3_label_pos"])

    for code, tr in traces.items():
        idx = indices[code]
        x, y = tr.positions[idx]
        sx, sy = world_to_screen(x, y, bounds)

        color = pygame.Color(f"#{tr.team_color}") if tr.team_color else C_GREY
        pygame.draw.circle(screen, (0, 0, 0), (sx, sy), 6)
        pygame.draw.circle(screen, color, (sx, sy), 5)


def draw_loading(screen, font, msg):
    screen.fill(C_BLACK)
    t = font.render(msg, True, C_WHITE)
    screen.blit(t, (WINDOW_WIDTH // 2 - t.get_width() // 2,
                    WINDOW_HEIGHT // 2 - t.get_height() // 2))
    pygame.display.flip()

# ============================================================
#                   MAIN REPLAY FUNCTION
# ============================================================

def run_replay(year=2025, round_number=1, gp_name="", circuit_name=""):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(f"F1 Replay: {year} {gp_name}")

    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    draw_loading(screen, font, f"Loading telemetry for {gp_name}...")

    try:
        os.makedirs("f1_cache", exist_ok=True)
        fastf1.Cache.enable_cache("f1_cache")
    except:
        pass

    data = {"traces": None, "colors": {}, "total_laps": 0}

    def loader():
        try:
            session = fastf1.get_session(year, round_number, "R")
            session.load(laps=True, telemetry=True)

            data["total_laps"] = int(session.laps["LapNumber"].max())

            drivers = session.drivers
            traces = {}
            colors = {}

            with ThreadPoolExecutor() as pool:
                for code, tr, col in pool.map(lambda d: process_driver(session, d), drivers):
                    if code and tr:
                        traces[code] = tr
                        colors[code] = col

            data["traces"] = traces
            data["colors"] = colors

        except Exception as e:
            print("[CRITICAL]", e)

    th = threading.Thread(target=loader)
    th.start()

    while th.is_alive():
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
        clock.tick(10)

    traces = data["traces"]
    if not traces:
        draw_loading(screen, font, "Failed to load telemetry!")
        pygame.time.wait(3000)
        return

    for code, col in data["colors"].items():
        if code in traces:
            traces[code].team_color = col

    bounds = compute_bounds(traces)
    centerline, markers = build_track_geometry(traces, bounds)

    min_time = min(tr.times[0] for tr in traces.values() if tr.times)
    max_time = max(tr.times[-1] for tr in traces.values() if tr.times)

    indices = {code: 0 for code in traces}
    current_time = min_time
    speed = 1.0
    paused = False

    order = compute_ranking_data(traces, indices)
    selected = order[0]["code"] if order else next(iter(traces))

    lb_surface = pygame.Surface((LEFT_PANEL_WIDTH, WINDOW_HEIGHT))

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            if ev.type == pygame.KEYDOWN:

                if ev.key == pygame.K_SPACE:
                    paused = not paused

                elif ev.key == pygame.K_UP:
                    speed = min(8, speed * 1.5)

                elif ev.key == pygame.K_DOWN:
                    speed = max(0.25, speed / 1.5)

                elif ev.key == pygame.K_RIGHT:
                    current_time = min(max_time, current_time + 5)

                elif ev.key == pygame.K_LEFT:
                    current_time = max(min_time, current_time - 5)

                elif ev.key == pygame.K_LEFTBRACKET:
                    rank = compute_ranking_data(traces, indices)
                    arr = [d["code"] for d in rank]
                    if selected in arr:
                        i = arr.index(selected)
                        selected = arr[(i - 1) % len(arr)]

                elif ev.key == pygame.K_RIGHTBRACKET:
                    rank = compute_ranking_data(traces, indices)
                    arr = [d["code"] for d in rank]
                    if selected in arr:
                        i = arr.index(selected)
                        selected = arr[(i + 1) % len(arr)]

        if not paused:
            current_time += dt * speed
            if current_time >= max_time:
                current_time = max_time
                paused = True

        for code, tr in traces.items():
            idx = bisect.bisect_right(tr.times, current_time)
            indices[code] = max(0, idx - 1)

        screen.fill(C_BLACK)

        draw_track_and_cars(screen, centerline, markers, traces, indices, bounds)

        ranking = compute_ranking_data(traces, indices)
        draw_leaderboard(lb_surface, ranking, font, selected)
        screen.blit(lb_surface, (0, 0))

        tr = traces[selected]
        idx = indices[selected]

        draw_driver_info(screen, font, tr, idx)
        draw_lap_info(screen, font, tr, idx, data["total_laps"])

        draw_hud(screen, font, current_time - min_time, speed, paused, gp_name, circuit_name)

        pygame.display.flip()

    pygame.quit()
