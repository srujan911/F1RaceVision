import pygame

pygame.init()

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 700

FONT = pygame.font.SysFont("Arial", 24, bold=True)
SMALL_FONT = pygame.font.SysFont("Arial", 20)

# --- F1 Themed Colors ---
C_BG = (15, 15, 22)          # Dark charcoal
C_TEXT = (240, 240, 240)     # Off-white
C_BTN = (35, 35, 45)         # Darker button
C_BTN_HOVER = (55, 55, 65)   # Lighter button on hover
C_ACCENT_RED = (225, 6, 0)   # F1 Red
C_BORDER = (80, 80, 90)      # Border for list items

SCROLL_SPEED = 40        # pixels per mouse wheel event
DEBOUNCE_TIME = 150      # ms to prevent double input


def draw_button(screen, rect, text, hover=False):
    """Draws a styled button, changing color on hover."""
    color = C_BTN_HOVER if hover else C_BTN
    pygame.draw.rect(screen, color, rect, border_radius=8)
    label = FONT.render(text, True, C_TEXT)
    screen.blit(label, (
        rect.x + (rect.width - label.get_width()) // 2,
        rect.y + (rect.height - label.get_height()) // 2
    ))


def menu_screen(races_by_year, default_year=None):
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("F1 Replay – Select Race")
    clock = pygame.time.Clock()

    # Prevent double year changes
    year_cooldown = 0

    # Extract available years
    years = sorted(races_by_year.keys())
    if not years:
        return None, None, None

    if default_year is None:
        default_year = years[-1]

    year_index = years.index(default_year) if default_year in years else 0
    year = years[year_index]

    # Scroll state
    scroll_offset = 0
    max_scroll = 0

    running = True
    while running:
        dt = clock.tick(60)
        year_cooldown = max(0, year_cooldown - dt)

        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]

        screen.fill(C_BG)

        # Title
        title = FONT.render("SELECT A RACE", True, C_TEXT)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 50))
        pygame.draw.line(screen, C_ACCENT_RED, (200, 90), (400, 90), 3)

        # Year label
        year_label = FONT.render(str(year), True, C_TEXT)
        screen.blit(year_label, (WINDOW_WIDTH // 2 - year_label.get_width() // 2, 130))

        # Year change buttons
        minus_rect = pygame.Rect(WINDOW_WIDTH // 2 - 100, 125, 50, 40)
        plus_rect = pygame.Rect(WINDOW_WIDTH // 2 + 50, 125, 50, 40)

        draw_button(screen, minus_rect, "<", minus_rect.collidepoint(mouse))
        draw_button(screen, plus_rect, ">", plus_rect.collidepoint(mouse))

        # YEAR CHANGE — with cooldown to avoid double increments
        if click and minus_rect.collidepoint(mouse) and year_cooldown == 0:
            year_index = max(0, year_index - 1)
            year = years[year_index]
            scroll_offset = 0
            year_cooldown = DEBOUNCE_TIME

        if click and plus_rect.collidepoint(mouse) and year_cooldown == 0:
            year_index = min(len(years) - 1, year_index + 1)
            year = years[year_index]
            scroll_offset = 0
            year_cooldown = DEBOUNCE_TIME

        # ========== RACE LIST WITH SCROLLING ==========
        races = races_by_year.get(year, [])
        list_top = 200
        list_area_height = WINDOW_HEIGHT - list_top - 50

        # Compute max scroll
        max_scroll = max(0, len(races) * 50 - list_area_height)

        # Clip scroll area
        scroll_offset = max(0, min(scroll_offset, max_scroll))

        # Draw each race button inside scroll area
        y = list_top - scroll_offset

        for rnd, name in races:
            rect = pygame.Rect(60, y, WINDOW_WIDTH - 120, 40)
            hovered = rect.collidepoint(mouse)

            # Draw list item with a red border on hover
            pygame.draw.rect(screen, C_BTN, rect, border_radius=6)
            if hovered:
                pygame.draw.rect(screen, C_ACCENT_RED, rect, 2, border_radius=6)

            label = SMALL_FONT.render(f"R{rnd:02d}  |  {name}", True, C_TEXT)
            screen.blit(label, (rect.x + 15, rect.y + 9))

            if hovered and click:
                pygame.time.wait(120)
                return year, rnd, name

            y += 50

        # ========== EVENT HANDLING ==========
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Scroll with mouse wheel
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset -= event.y * SCROLL_SPEED

            # Keyboard scrolling
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    scroll_offset -= SCROLL_SPEED
                elif event.key == pygame.K_DOWN:
                    scroll_offset += SCROLL_SPEED

        pygame.display.flip()

    pygame.quit()
    return None, None, None
