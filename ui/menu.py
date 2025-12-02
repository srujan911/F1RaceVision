import pygame

pygame.init()

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 650

FONT = pygame.font.SysFont("Arial", 26)
SMALL = pygame.font.SysFont("Arial", 22)

BG = (210, 210, 220)
BTN = (180, 180, 195)
BTN_HOVER = (160, 160, 180)
WHITE = (255, 255, 255)
YELLOW = (240, 200, 60)
TEXT = (40, 40, 60)

SCROLL_SPEED = 40        # pixels per mouse wheel event
DEBOUNCE_TIME = 150      # ms to prevent double input


def draw_button(screen, rect, text, hover=False):
    pygame.draw.rect(screen, BTN_HOVER if hover else BTN, rect, border_radius=8)
    label = FONT.render(text, True, WHITE)
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

        screen.fill(BG)

        # Title
        title = FONT.render("Select F1 Replay", True, YELLOW)
        screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 40))

        # Year label
        year_label = FONT.render(f"Year: {year}", True, TEXT)
        screen.blit(year_label, (60, 120))

        # Year change buttons
        minus_rect = pygame.Rect(350, 115, 50, 40)
        plus_rect = pygame.Rect(420, 115, 50, 40)

        draw_button(screen, minus_rect, "-", minus_rect.collidepoint(mouse))
        draw_button(screen, plus_rect, "+", plus_rect.collidepoint(mouse))

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
        list_top = 190
        list_area_height = WINDOW_HEIGHT - list_top - 40

        # Compute max scroll
        max_scroll = max(0, len(races) * 50 - list_area_height)

        # Clip scroll area
        scroll_offset = max(0, min(scroll_offset, max_scroll))

        # Draw each race button inside scroll area
        y = list_top - scroll_offset

        for rnd, name in races:
            rect = pygame.Rect(80, y, 440, 40)
            hovered = rect.collidepoint(mouse)

            pygame.draw.rect(screen, BTN_HOVER if hovered else BTN, rect, border_radius=8)

            label = SMALL.render(f"Round {rnd}: {name}", True, WHITE)
            screen.blit(label, (rect.x + 10, rect.y + 8))

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
