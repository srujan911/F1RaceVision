import math
from typing import Dict, List, Tuple
import threading

import pygame
import fastf1

from core.telemetry_loader import load_race_telemetry, DriverTrace


WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
FPS = 60

LEFT_PANEL_WIDTH = 240
RIGHT_PANEL_WIDTH = 300


# =========================
#   BASIC UTILS
# =========================

def compute_bounds(traces: Dict[str, DriverTrace]) -> Tuple[float, float, float, float]:
    xs, ys = [], []
    for tr in traces.values():
        for x, y in tr.positions:
            xs.append(x)
            ys.append(y)
    return min(xs), max(xs), min(ys), max(ys)


def world_to_screen(x: float, y: float, bounds) -> Tuple[int, int]:
    min_x, max_x, min_y, max_y = bounds

    if max_x == min_x:
        max_x += 1.0
    if max_y == min_y:
        max_y += 1.0

    nx = (x - min_x) / (max_x - min_x)
    ny = (y - min_y) / (max_y - min_y)

    margin_left = LEFT_PANEL_WIDTH + 30
    margin_right = 30
    margin_top = 80
    margin_bottom = 50

    usable_w = WINDOW_WIDTH - margin_left - margin_right
    usable_h = WINDOW_HEIGHT - margin_top - margin_bottom

    sx = margin_left + nx * usable_w
    sy = WINDOW_HEIGHT - (margin_bottom + ny * usable_h)

    return int(sx), int(sy)


def downsample(points: List[Tuple[float, float]], target: int = 800):
    if len(points) <= target:
        return points
    step = max(1, len(points) // target)
    return points[::step]


def build_track_edges(traces: Dict[str, DriverTrace], bounds, track_width: float = 12.0):
    """
    Builds two polylines for the track edges by offsetting the centerline.
    """
    first_driver = next(iter(traces.values()))
    centerline_world = first_driver.positions
    centerline_world = downsample(centerline_world, 900)

    if len(centerline_world) < 3:
        return [], [], {}

    left_edge, right_edge = [], []

    # Calculate screen-space track width
    # We transform two points that are `track_width` apart in world space
    # to see how many pixels that corresponds to on screen.
    p1_screen = world_to_screen(0, 0, bounds)
    p2_screen = world_to_screen(track_width, 0, bounds)
    width_pixels = math.hypot(p2_screen[0] - p1_screen[0], p2_screen[1] - p1_screen[1])

    centerline_screen = [world_to_screen(x, y, bounds) for (x, y) in centerline_world]

    for i in range(len(centerline_screen)):
        p_prev = centerline_screen[i - 1]
        p_curr = centerline_screen[i]
        p_next = centerline_screen[(i + 1) % len(centerline_screen)]

        # Get tangent vector (direction of the track)
        dx = p_next[0] - p_prev[0]
        dy = p_next[1] - p_prev[1]

        # Get normal vector (perpendicular to the track)
        mag = math.hypot(dx, dy)
        if mag == 0: continue
        nx, ny = -dy / mag, dx / mag

        left_edge.append((p_curr[0] + nx * width_pixels, p_curr[1] + ny * width_pixels))
        right_edge.append((p_curr[0] - nx * width_pixels, p_curr[1] - ny * width_pixels))

    # --- Calculate marker positions ---
    n = len(centerline_screen)
    s2_idx = n // 3
    s3_idx = (2 * n) // 3

    # The SF line is the line between the first point of the left and right edges
    sf_line = (left_edge[0], right_edge[0])

    # The centerline is needed for the dashed line effect
    track_markers = {
        "sf_line": sf_line,
        "s2_pos": centerline_screen[s2_idx],
        "s3_pos": centerline_screen[s3_idx],
        "centerline": centerline_screen,
    }
    return left_edge, right_edge, track_markers
# =========================
#   TRACK FROM TELEMETRY
# =========================

# =========================
#   LEADERBOARD
# =========================

def get_progress(tr: DriverTrace, idx: int) -> Tuple[int, float]:
    """Returns a tuple of (lap_number, distance_into_lap) for accurate ranking."""
    if not tr.lap_numbers or not tr.distances or idx >= len(tr.lap_numbers):
        return (0, 0.0)
    return (tr.lap_numbers[idx], tr.distances[idx])


def compute_ranking(traces: Dict[str, DriverTrace], indices: Dict[str, int]) -> List[str]:
    ranking = []
    for code, tr in traces.items():
        idx = indices.get(code, 0)
        progress = get_progress(tr, idx) # This now returns (lap, distance)
        ranking.append((progress, code))
    ranking.sort(reverse=True)  # leader first
    return [code for _, code in ranking]


def draw_leaderboard(surface, ranking, font, selected_code, traces, indices):
    """A fresh, clean implementation of the leaderboard draw function."""
    surface.fill((12, 12, 20)) # Clear the surface

    # Define colors for tyre compounds
    TYRE_COLORS = {
        "S": (255, 60, 60), "M": (255, 220, 0), "H": (255, 255, 255),
        "I": (0, 255, 0), "W": (100, 150, 255), "?": (180, 180, 180)
    }

    y_pos = 60
    for i, driver_code in enumerate(ranking):
        position = i + 1
        trace = traces.get(driver_code)
        if not trace: continue

        # --- Highlight selected driver ---
        if driver_code == selected_code:
            team_color_hex = trace.team_color
            highlight_color = pygame.Color(f"#{team_color_hex}") if team_color_hex else (60, 60, 120)
            highlight_rect = pygame.Rect(10, y_pos - 2, LEFT_PANEL_WIDTH - 20, 28)
            pygame.draw.rect(surface, highlight_color, highlight_rect, border_radius=6)

        # --- Position Number ---
        pos_text = font.render(f"{position}", True, (200, 200, 200))
        surface.blit(pos_text, (20, y_pos))

        # --- Driver Code ---
        code_text = font.render(driver_code, True, (255, 255, 255))
        surface.blit(code_text, (55, y_pos))

        # --- Tyre Compound ---
        idx = indices.get(driver_code, 0)
        tyre_char = "?"
        if trace.tyres and idx < len(trace.tyres):
            tyre_char = trace.tyres[idx][0] if trace.tyres[idx] else "?"
        
        tyre_color = TYRE_COLORS.get(tyre_char, TYRE_COLORS["?"])
        tyre_text = font.render(tyre_char, True, tyre_color)
        surface.blit(tyre_text, (190, y_pos))

        y_pos += 30


# =========================
#   DRIVER INFO + LAP INFO
# =========================

def draw_driver_info(screen, tr: DriverTrace, idx: int, font):
    x = WINDOW_WIDTH - RIGHT_PANEL_WIDTH - 10
    y = 60
    pygame.draw.rect(screen, (20, 20, 40), (x, y, RIGHT_PANEL_WIDTH, 200), border_radius=10)

    screen.blit(font.render("Driver Info", True, (255, 255, 0)), (x + 10, y + 10))
    screen.blit(font.render(f"Driver: {tr.driver_code}", True, (255, 255, 255)), (x + 10, y + 50))

    speed = tr.speeds[idx] if tr.speeds else 0.0
    gear = tr.gears[idx] if tr.gears else 0
    drs_val = tr.drs[idx] if tr.drs else 0

    screen.blit(font.render(f"Speed: {speed:.1f} km/h", True, (255, 255, 255)), (x + 10, y + 80))
    screen.blit(font.render(f"Gear: {gear}", True, (255, 255, 255)), (x + 10, y + 110))

    drs_on = drs_val >= 8
    drs_colour = (0, 255, 0) if drs_on else (255, 70, 70)
    screen.blit(font.render(f"DRS: {'ON' if drs_on else 'OFF'}", True, drs_colour), (x + 10, y + 140))


def draw_lap_info(screen, tr: DriverTrace, idx: int, font):
    lap = tr.lap_numbers[idx] if tr.lap_numbers else 0
    total = max(tr.lap_numbers) if tr.lap_numbers else 0

    s1, s2, s3 = tr.sectors[idx] if tr.sectors else (0.0, 0.0, 0.0)

    x = WINDOW_WIDTH // 2 - 200
    screen.blit(font.render(f"LAP {lap}/{total}", True, (255, 255, 255)), (x, 40))
    screen.blit(font.render(f"S1: {s1:.3f}", True, (255, 220, 0)), (x, 70))
    screen.blit(font.render(f"S2: {s2:.3f}", True, (0, 200, 255)), (x + 150, 70))
    screen.blit(font.render(f"S3: {s3:.3f}", True, (255, 120, 0)), (x + 300, 70))


# =========================
#   MAIN REPLAY LOOP
# =========================

def draw_loading_screen(screen, font, gp_name, year, round_number):
    title = f"F1 Replay {year} R{round_number}"
    if gp_name:
        title += f" – {gp_name}"
    pygame.display.set_caption(title)

    font = pygame.font.SysFont("Arial", 22)
    
    # --- Pulsating text effect ---
    base_alpha = 100
    pulse_speed = 2.0
    
    def draw_pulsating_text(elapsed_time):
        screen.fill((12, 12, 20))
        
        # Calculate alpha for pulsing effect
        pulse = (math.sin(elapsed_time * pulse_speed) + 1) / 2  # Varies between 0 and 1
        alpha = base_alpha + (255 - base_alpha) * pulse
        
        loading_text = font.render(f"Loading telemetry for {gp_name}...", True, (255, 255, 255))
        loading_text.set_alpha(alpha)
        
        screen.blit(
            loading_text,
            (
                WINDOW_WIDTH // 2 - loading_text.get_width() // 2,
                WINDOW_HEIGHT // 2 - loading_text.get_height() // 2,
            ),
        )
        pygame.display.flip()


def run_replay(year=2025, round_number=1, gp_name: str = "", circuit_name: str = ""):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    font = pygame.font.SysFont("Arial", 22)
    clock = pygame.time.Clock()

    # --- Loading Phase ---
    # The draw_loading_screen function is now integrated into the main loading loop.

    telemetry_data = {"traces": None}

    def load_data_thread():
        print(f"Loading telemetry for {year} round {round_number}...")
        telemetry_data["traces"] = load_race_telemetry(year, round_number)

    loader_thread = threading.Thread(target=load_data_thread)
    loader_thread.start()

    # Fetch team colors while telemetry loads
    team_colors = {}
    try:
        session = fastf1.get_session(year, round_number, 'R')
        session.load(telemetry=False, weather=False, messages=False)
        for drv in session.drivers:
            driver_info = session.get_driver(drv)
            team_colors[driver_info['Abbreviation']] = driver_info['TeamColor']
    except Exception as e:
        print(f"[WARNING] Could not load team colors: {e}")
        # Fallback colors will be used if this fails

    # --- Pulsating text effect for loading screen ---
    base_alpha = 100
    pulse_speed = 2.0

    def draw_pulsating_text(elapsed_time):
        screen.fill((12, 12, 20))

        # Calculate alpha for pulsing effect
        pulse = (math.sin(elapsed_time * pulse_speed) + 1) / 2  # Varies between 0 and 1
        alpha = base_alpha + (255 - base_alpha) * pulse

        loading_text = font.render(f"Loading telemetry for {gp_name}...", True, (255, 255, 255))
        loading_text.set_alpha(alpha)

        screen.blit(
            loading_text,
            (
                WINDOW_WIDTH // 2 - loading_text.get_width() // 2,
                WINDOW_HEIGHT // 2 - loading_text.get_height() // 2,
            ),
        )
        pygame.display.flip()

    loading_start_time = pygame.time.get_ticks()
    while loader_thread.is_alive():
        elapsed_time = (pygame.time.get_ticks() - loading_start_time) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        
        # Draw the animated loading screen
        draw_pulsating_text(elapsed_time)
        clock.tick(10)

    traces = telemetry_data["traces"]
    if not traces:
        print("No telemetry found or loading was cancelled.")
        return

    # Add team colors to traces
    for code, color in team_colors.items():
        if code in traces:
            traces[code].team_color = color

    # --- Replay Phase ---
    bounds = compute_bounds(traces)

    # Build track polyline (for drawing only)
    # outline, s1_poly, s2_poly, s3_poly = build_track_polyline(traces, bounds)
    left_edge, right_edge, track_markers = build_track_edges(traces, bounds)

    # --- Re-draw the screen once after loading is complete ---
    # This clears the loading text before the replay starts.
    screen.fill((12, 12, 20))
    pygame.display.flip()

    indices = {code: 0 for code in traces.keys()}
    current_time = 0.0
    playback_speed = 1.0
    base_step = 0.2
    paused = False

    selected_driver = next(iter(traces.keys()))

    title = f"F1 Replay {year} R{round_number}"
    if gp_name:
        title += f" – {gp_name}"
    pygame.display.set_caption(title)

    leaderboard_surface = pygame.Surface((LEFT_PANEL_WIDTH, WINDOW_HEIGHT))
    leaderboard_dirty = True

    running = True
    while running:
        # --- Event Handling & State Update ---
        dt = clock.tick(FPS) / 1000.0  # Delta time in seconds


        last_ranking = ranking if 'ranking' in locals() else None
        ranking = compute_ranking(traces, indices)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    playback_speed = min(playback_speed + 0.5, 5.0)
                elif event.key == pygame.K_DOWN:
                    playback_speed = max(playback_speed - 0.5, 0.1)
                elif event.key == pygame.K_1:
                    playback_speed = 0.5
                elif event.key == pygame.K_2:
                    playback_speed = 1.0
                elif event.key == pygame.K_3:
                    playback_speed = 2.0
                elif event.key == pygame.K_4:
                    playback_speed = 4.0
                elif event.key == pygame.K_RIGHTBRACKET:
                    # next driver
                    if ranking:
                        i = ranking.index(selected_driver)
                        selected_driver = ranking[(i + 1) % len(ranking)]
                elif event.key == pygame.K_LEFTBRACKET:
                    # previous driver
                    if ranking:
                        i = ranking.index(selected_driver)
                        selected_driver = ranking[(i - 1) % len(ranking)]

        if not paused:
            current_time += (base_step * playback_speed) * (dt * FPS) # Frame-rate independent update
            for code, tr in traces.items():
                idx = indices[code]
                times = tr.times
                while idx + 1 < len(times) and times[idx] < current_time:
                    idx += 1
                indices[code] = idx

        # ========== DRAW ==========
        screen.fill((12, 12, 20))

        # --- Draw Track ---
        if left_edge and right_edge:
            # 1. Create a single polygon for the filled track area
            track_surface_poly = left_edge + right_edge[::-1]
            pygame.draw.polygon(screen, (40, 40, 45), track_surface_poly)

            # 2. Draw the white edge lines (borders)
            pygame.draw.lines(screen, (255, 255, 255), True, left_edge, 2)
            pygame.draw.lines(screen, (255, 255, 255), True, right_edge, 2)

            # 3. Draw a dashed centerline
            centerline = track_markers.get("centerline")
            if centerline:
                for i in range(0, len(centerline) - 1, 2): # Draw every other segment
                    pygame.draw.line(screen, (255, 220, 0), centerline[i], centerline[i+1], 1)

        # Draw Track Markers (SF Line, Sector Labels)
        if track_markers:
            # Start/Finish Line
            sf_line = track_markers.get("sf_line")
            if sf_line:
                pygame.draw.line(screen, (255, 255, 255), sf_line[0], sf_line[1], 3)

            # Sector Labels
            s2_pos = track_markers.get("s2_pos")
            s3_pos = track_markers.get("s3_pos")
            sector_font = pygame.font.SysFont("Arial", 16, bold=True)
            
            s1_label = sector_font.render("S1", True, (255, 220, 0))
            s2_label = sector_font.render("S2", True, (0, 200, 255))
            s3_label = sector_font.render("S3", True, (255, 120, 0))
            screen.blit(s1_label, (sf_line[0][0] + 10, sf_line[0][1]))
            screen.blit(s2_label, (s2_pos[0] + 10, s2_pos[1]))
            screen.blit(s3_label, (s3_pos[0] + 10, s3_pos[1]))

        # Cars
        for code, tr in traces.items():
            idx = indices[code]
            idx = max(0, min(idx, len(tr.positions) - 1))
            x, y = tr.positions[idx]
            sx, sy = world_to_screen(x, y, bounds)

            # Use team color for the dot
            team_color_hex = tr.team_color
            if team_color_hex:
                colour = pygame.Color(f"#{team_color_hex}")
            else:
                colour = (230, 230, 230) # Fallback grey

            pygame.draw.circle(screen, (0, 0, 0), (sx, sy), 6)
            pygame.draw.circle(screen, colour, (sx, sy), 5)

        # --- Leaderboard Optimization ---
        if ranking != last_ranking:
            leaderboard_dirty = True

        if leaderboard_dirty:
            draw_leaderboard(leaderboard_surface, ranking, font, selected_driver, traces, indices)
            leaderboard_dirty = False
        screen.blit(leaderboard_surface, (0, 0))

        # Driver + lap info
        tr_sel = traces[selected_driver]
        idx_sel = indices[selected_driver]
        draw_driver_info(screen, tr_sel, idx_sel, font)
        draw_lap_info(screen, tr_sel, idx_sel, font)

        # HUD
        hud_text = font.render(
            f"{'PAUSED' if paused else 'PLAYING'} | t={current_time:.1f}s | {playback_speed:.1f}x  [ / ] change driver",
            True,
            (255, 255, 255),
        )
        screen.blit(hud_text, (LEFT_PANEL_WIDTH + 30, 10))

        # Circuit / GP name at top centre
        title_y = 35
        if circuit_name:
            gp_label = font.render(circuit_name, True, (255, 255, 255))
            screen.blit(
                gp_label,
                (WINDOW_WIDTH // 2 - gp_label.get_width() // 2, title_y),
            )

        pygame.display.flip()

    pygame.quit()
