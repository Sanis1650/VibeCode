import colorsys
import math
import sys
import time
import pygame


def hsv_to_rgb(hue: float, saturation: float, value: float) -> tuple[int, int, int]:
    """Переводит HSV (hue — любое вещественное число, s и v в [0, 1]) в RGB (0..255)."""
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, max(0.0, min(1.0, saturation)), max(0.0, min(1.0, value)))
    return int(r * 255), int(g * 255), int(b * 255)


def init_fullscreen() -> tuple[pygame.Surface, int, int]:
    """Открывает окно сразу на весь экран под текущее разрешение дисплея."""
    info = pygame.display.Info()
    width = info.current_w if info.current_w > 0 else 1920
    height = info.current_h if info.current_h > 0 else 1080
    screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
    pygame.display.set_caption("Плавная бесконечная иллюзия")
    return screen, width, height


def draw_waves_and_rings(
    surface: pygame.Surface,
    cx: int,
    cy: int,
    max_radius: float,
    elapsed: float,
    ring_count: int = 48,
) -> None:
    """
    Рисует концентрические кольца с плавной бегущей волной и противофазным дыханием.
    Нет резких скачков — движение идёт непрерывно во времени.
    """
    step = max_radius / ring_count

    for idx in range(ring_count, 0, -1):
        # Плавная бегущая волна по радиусу (без резкого сброса назад)
        traveling_wave = math.sin(idx * 0.35 - elapsed * 2.4) * (step * 0.45)

        # Противофазное дыхание чётных и нечётных колец
        parity = 1.0 if idx % 2 == 0 else -1.0
        breathing = math.cos(elapsed * 1.6 + idx * 0.22) * parity * (step * 0.28)

        radius = idx * step + traveling_wave + breathing
        if radius <= 4.0:
            continue

        # Медленный плавный перелив оттенков без разрывов
        hue = (elapsed * 0.045 + idx * 0.018 + 0.04 * math.sin(elapsed * 0.5 + idx * 0.1)) % 1.0
        saturation = 0.82 + 0.14 * math.sin(elapsed * 0.9 + idx * 0.25)
        value = 0.88 + 0.10 * math.cos(elapsed * 1.1 - idx * 0.2)
        color = hsv_to_rgb(hue, saturation, value)

        thickness = max(2, int(step * 0.36 + math.sin(elapsed * 2.0 + idx * 0.4) * 1.2))
        width_arg = 0 if thickness >= int(radius) else thickness
        pygame.draw.circle(surface, color, (cx, cy), int(round(radius)), width_arg)


def draw_rotating_arcs(
    surface: pygame.Surface,
    cx: int,
    cy: int,
    max_radius: float,
    elapsed: float,
    arc_rings: int = 7,
) -> None:
    """Добавляет плавно вращающиеся дуги для усиления эффекта перелива и глубины."""
    for k in range(1, arc_rings + 1):
        ratio = k / (arc_rings + 1)
        radius = int(max_radius * (0.18 + ratio * 0.72) + math.sin(elapsed * 1.4 + k) * 10.0)
        if radius < 16:
            continue

        arc_span = math.pi * 0.55
        direction = 1.0 if k % 2 == 0 else -1.0
        start_angle = elapsed * (0.35 + k * 0.07) * direction + k * 0.8
        end_angle = start_angle + arc_span

        hue = (elapsed * 0.06 + ratio * 0.7) % 1.0
        color = hsv_to_rgb(hue, 0.9, 0.98)

        rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        pygame.draw.arc(surface, color, rect, start_angle, end_angle, 3)


def draw_center_anchor(surface: pygame.Surface, cx: int, cy: int, elapsed: float) -> None:
    """Рисует спокойную пульсирующую точку в центре для фиксации взгляда."""
    pulse = math.sin(elapsed * 2.8)
    outer_r = max(8, int(round(18 + pulse * 3)))
    inner_r = max(4, int(round(9 + pulse * 1.5)))

    outer_color = hsv_to_rgb((elapsed * 0.08 + 0.3) % 1.0, 0.5, 0.95)
    inner_color = hsv_to_rgb((elapsed * 0.12 + 0.7) % 1.0, 0.2, 1.0)

    pygame.draw.circle(surface, outer_color, (cx, cy), outer_r, 2)
    pygame.draw.circle(surface, inner_color, (cx, cy), inner_r)


def main() -> None:
    pygame.init()
    screen, width, height = init_fullscreen()
    clock = pygame.time.Clock()

    cx = width // 2
    cy = height // 2
    max_radius = math.hypot(cx, cy) * 1.08

    elapsed = 0.0
    paused = False
    last_time = time.perf_counter()

    try:
        while True:
            now = time.perf_counter()
            # Реальная разница во времени с защитой от скачка при переключении окон
            real_dt = min(now - last_time, 0.05)
            last_time = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_SPACE:
                        paused = not paused

            if not paused:
                elapsed += real_dt

            screen.fill((7, 7, 11))
            draw_waves_and_rings(screen, cx, cy, max_radius, elapsed)
            draw_rotating_arcs(screen, cx, cy, max_radius, elapsed)
            draw_center_anchor(screen, cx, cy, elapsed)

            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()