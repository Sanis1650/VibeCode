import json
import os
import random
import sys
import tkinter as tk

CELL_SIZE = 24
COLS = 26
ROWS = 20
BASE_DELAY_MS = 130
MIN_DELAY_MS = 45
MAX_DELAY_MS = 180
BONUS_INTERVAL_MS = 10_000
HIGHSCORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "snake_highscore.json",
)

try:
    import winsound

    HAS_WINSOUND = sys.platform == "win32"
except ImportError:
    HAS_WINSOUND = False


def beep(freq: int, duration_ms: int):
    if HAS_WINSOUND:
        try:
            winsound.Beep(freq, duration_ms)
        except RuntimeError:
            pass


class SnakeProGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Змейка PRO")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        self.wrap_walls = False
        self.highscore = self.load_highscore()
        self.after_id = None
        self.bonus_spawn_id = None

        self.build_ui()
        self.bind_events()
        self.reset_game()

    def load_highscore(self) -> int:
        try:
            with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("highscore", 0))
        except (OSError, ValueError, TypeError):
            return 0

    def save_highscore(self):
        try:
            with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"highscore": self.highscore},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError:
            pass

    def build_ui(self):
        top_bar = tk.Frame(self.root, bg="#1e293b", padx=10, pady=8)
        top_bar.pack(fill=tk.X)

        label_style = {
            "bg": "#1e293b",
            "fg": "#f8fafc",
            "font": ("Segoe UI", 11, "bold"),
        }
        self.score_lbl = tk.Label(top_bar, text="Счёт: 0", **label_style)
        self.score_lbl.pack(side=tk.LEFT, padx=(0, 14))

        self.best_lbl = tk.Label(
            top_bar,
            text=f"Рекорд: {self.highscore}",
            fg="#fbbf24",
            bg="#1e293b",
            font=("Segoe UI", 11, "bold"),
        )
        self.best_lbl.pack(side=tk.LEFT, padx=(0, 14))

        self.level_lbl = tk.Label(
            top_bar,
            text="Скорость: 1",
            fg="#38bdf8",
            bg="#1e293b",
            font=("Segoe UI", 11, "bold"),
        )
        self.level_lbl.pack(side=tk.LEFT)

        btn_style = {
            "bg": "#334155",
            "fg": "#f8fafc",
            "activebackground": "#475569",
            "activeforeground": "#ffffff",
            "relief": tk.FLAT,
            "padx": 8,
            "pady": 3,
            "font": ("Segoe UI", 9, "bold"),
            "cursor": "hand2",
        }

        self.wall_btn = tk.Button(
            top_bar,
            text="Стены: Смерть",
            command=self.toggle_walls,
            **btn_style,
        )
        self.wall_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.pause_btn = tk.Button(
            top_bar,
            text="Пауза",
            command=self.toggle_pause,
            **btn_style,
        )
        self.pause_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.canvas = tk.Canvas(
            self.root,
            width=COLS * CELL_SIZE,
            height=ROWS * CELL_SIZE,
            bg="#0b1120",
            highlightthickness=2,
            highlightbackground="#334155",
        )
        self.canvas.pack(padx=10, pady=(4, 6))

        hint = tk.Label(
            self.root,
            text="W A S D — движение  •  Space — пауза / рестарт  •  Esc — выход",
            bg="#0f172a",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        )
        hint.pack(pady=(0, 8))

    def bind_events(self):
        self.root.bind("<KeyPress>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_game)

    def quit_game(self):
        self.cancel_timers()
        self.save_highscore()
        self.root.destroy()

    def cancel_timers(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.bonus_spawn_id is not None:
            self.root.after_cancel(self.bonus_spawn_id)
            self.bonus_spawn_id = None

    def schedule_next_tick(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.after_id = self.root.after(self.current_delay_ms(), self.tick)

    def schedule_bonus_spawn(self):
        if self.bonus_spawn_id is not None:
            self.root.after_cancel(self.bonus_spawn_id)
        self.bonus_spawn_id = self.root.after(
            BONUS_INTERVAL_MS, self.on_bonus_timer
        )

    def on_bonus_timer(self):
        self.bonus_spawn_id = None
        if self.paused or self.game_over:
            return
        self.spawn_single_bonus()
        self.schedule_bonus_spawn()

    def toggle_walls(self):
        self.wrap_walls = not self.wrap_walls
        self.wall_btn.config(
            text="Стены: Сквозные" if self.wrap_walls else "Стены: Смерть"
        )
        self.draw()

    def toggle_pause(self):
        if self.game_over:
            return
        self.paused = not self.paused
        self.pause_btn.config(text="Продолжить" if self.paused else "Пауза")
        if self.paused:
            self.cancel_timers()
        else:
            self.schedule_next_tick()
            self.schedule_bonus_spawn()
        self.draw()

    def reset_game(self):
        self.cancel_timers()
        self.direction = "Right"
        self.input_queue = []
        self.score = 0
        self.blue_speed_bonus = 0
        self.game_over = False
        self.paused = False
        self.pause_btn.config(text="Пауза")

        mid_x, mid_y = COLS // 2, ROWS // 2
        self.snake = [(mid_x, mid_y), (mid_x - 1, mid_y), (mid_x - 2, mid_y)]
        self.particles = []
        self.food = self.spawn_free_cell()
        self.bonus_food = None

        self.update_hud()
        self.draw()
        self.schedule_next_tick()
        self.schedule_bonus_spawn()

    def spawn_free_cell(self, extra_blocked=None):
        blocked = set(self.snake)
        if extra_blocked:
            blocked.update(extra_blocked)
        free = [
            (x, y)
            for x in range(COLS)
            for y in range(ROWS)
            if (x, y) not in blocked
        ]
        return random.choice(free) if free else None

    def spawn_single_bonus(self):
        blocked = set()
        if self.food:
            blocked.add(self.food)
        if self.bonus_food:
            blocked.add(self.bonus_food["pos"])

        pos = self.spawn_free_cell(blocked)
        if not pos:
            return

        kind = random.choice(["gold", "blue"])
        self.bonus_food = {
            "pos": pos,
            "kind": kind,
        }
        self.draw()

    def spawn_particles(self, cell_pos, color):
        cx = (cell_pos[0] + 0.5) * CELL_SIZE
        cy = (cell_pos[1] + 0.5) * CELL_SIZE
        for _ in range(10):
            vx = random.uniform(-3.5, 3.5)
            vy = random.uniform(-3.5, 3.5)
            life = random.randint(8, 15)
            self.particles.append({
                "x": cx,
                "y": cy,
                "vx": vx,
                "vy": vy,
                "life": life,
                "color": color,
            })

    def update_particles(self):
        next_particles = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] > 0:
                next_particles.append(p)
        self.particles = next_particles

    def current_speed_level(self) -> int:
        # Единственный источник прибавки скорости — съеденные синие яблоки (+1 за каждое)
        return 1 + self.blue_speed_bonus

    def current_delay_ms(self) -> int:
        steps_above_one = self.current_speed_level() - 1
        raw = BASE_DELAY_MS - steps_above_one * 9
        return max(MIN_DELAY_MS, min(MAX_DELAY_MS, raw))

    def update_hud(self):
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore()
        self.score_lbl.config(text=f"Счёт: {self.score}")
        self.best_lbl.config(text=f"Рекорд: {self.highscore}")
        self.level_lbl.config(text=f"Скорость: {self.current_speed_level()}")

    def on_key(self, event: tk.Event):
        key = event.keysym
        char_lower = (event.char or "").lower()

        if key == "Escape":
            self.quit_game()
            return

        if key == "space":
            if self.game_over:
                self.reset_game()
            else:
                self.toggle_pause()
            return

        wasd_map = {
            "w": "Up",
            "ц": "Up",
            "s": "Down",
            "ы": "Down",
            "a": "Left",
            "ф": "Left",
            "d": "Right",
            "в": "Right",
        }
        opposites = {
            "Up": "Down",
            "Down": "Up",
            "Left": "Right",
            "Right": "Left",
        }

        mapped_dir = wasd_map.get(key.lower()) or wasd_map.get(char_lower)
        if mapped_dir and not self.paused and not self.game_over:
            last_dir = self.input_queue[-1] if self.input_queue else self.direction
            if (
                mapped_dir != last_dir
                and opposites[mapped_dir] != last_dir
                and len(self.input_queue) < 2
            ):
                self.input_queue.append(mapped_dir)

    def tick(self):
        self.after_id = None
        if self.paused or self.game_over:
            return

        if self.input_queue:
            self.direction = self.input_queue.pop(0)

        head_x, head_y = self.snake[0]
        deltas = {
            "Up": (0, -1),
            "Down": (0, 1),
            "Left": (-1, 0),
            "Right": (1, 0),
        }
        dx, dy = deltas[self.direction]
        nx, ny = head_x + dx, head_y + dy

        if self.wrap_walls:
            nx %= COLS
            ny %= ROWS
        else:
            if not (0 <= nx < COLS and 0 <= ny < ROWS):
                self.trigger_game_over()
                return

        new_head = (nx, ny)
        will_eat_red = new_head == self.food
        will_eat_bonus = (
            self.bonus_food is not None and new_head == self.bonus_food["pos"]
        )
        body_to_check = (
            self.snake if (will_eat_red or will_eat_bonus) else self.snake[:-1]
        )

        if new_head in body_to_check:
            self.trigger_game_over()
            return

        self.snake.insert(0, new_head)

        if will_eat_red:
            self.score += 1
            self.spawn_particles(new_head, "#f87171")
            beep(660, 45)
            blocked = {self.bonus_food["pos"]} if self.bonus_food else None
            self.food = self.spawn_free_cell(blocked)
            self.update_hud()
        elif will_eat_bonus:
            kind = self.bonus_food["kind"]
            if kind == "gold":
                self.score += 3
                self.spawn_particles(new_head, "#facc15")
                beep(880, 70)
            else:
                self.blue_speed_bonus += 1
                self.spawn_particles(new_head, "#38bdf8")
                beep(780, 70)
            self.bonus_food = None
            self.update_hud()
        else:
            self.snake.pop()

        self.update_particles()
        self.draw()
        self.schedule_next_tick()

    def trigger_game_over(self):
        self.game_over = True
        self.cancel_timers()
        self.update_hud()
        beep(220, 180)
        self.draw()

    def draw_bonus_item(self):
        if not self.bonus_food:
            return
        sx, sy = self.bonus_food["pos"]
        is_gold = self.bonus_food["kind"] == "gold"
        fill_col = "#facc15" if is_gold else "#38bdf8"
        out_col = "#fef08a" if is_gold else "#bae6fd"

        self.canvas.create_oval(
            sx * CELL_SIZE + 2,
            sy * CELL_SIZE + 2,
            (sx + 1) * CELL_SIZE - 2,
            (sy + 1) * CELL_SIZE - 2,
            fill=fill_col,
            outline=out_col,
            width=2,
        )

    def draw(self):
        self.canvas.delete("all")

        for c in range(1, COLS):
            x = c * CELL_SIZE
            self.canvas.create_line(x, 0, x, ROWS * CELL_SIZE, fill="#111b2e")
        for r in range(1, ROWS):
            y = r * CELL_SIZE
            self.canvas.create_line(0, y, COLS * CELL_SIZE, y, fill="#111b2e")

        if self.food:
            fx, fy = self.food
            pad = 3
            self.canvas.create_oval(
                fx * CELL_SIZE + pad,
                fy * CELL_SIZE + pad,
                (fx + 1) * CELL_SIZE - pad,
                (fy + 1) * CELL_SIZE - pad,
                fill="#ef4444",
                outline="#fca5a5",
                width=1,
            )

        self.draw_bonus_item()

        for idx, (x, y) in enumerate(self.snake):
            x0 = x * CELL_SIZE + 1
            y0 = y * CELL_SIZE + 1
            x1 = (x + 1) * CELL_SIZE - 1
            y1 = (y + 1) * CELL_SIZE - 1

            if idx == 0:
                color = "#4ade80"
            else:
                shade = max(110, 215 - idx * 3)
                color = f"#16{shade:02x}4a" if shade <= 255 else "#22c55e"

            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=color,
                outline="#052e16" if idx == 0 else "",
                width=1 if idx == 0 else 0,
            )

            if idx == 0:
                self.draw_eyes(x, y)

        for p in self.particles:
            r = max(2, p["life"] // 3)
            self.canvas.create_oval(
                p["x"] - r,
                p["y"] - r,
                p["x"] + r,
                p["y"] + r,
                fill=p["color"],
                outline="",
            )

        w = COLS * CELL_SIZE
        h = ROWS * CELL_SIZE
        if self.paused and not self.game_over:
            self.canvas.create_rectangle(
                0, 0, w, h, fill="#020617", stipple="gray50", outline=""
            )
            self.canvas.create_text(
                w // 2,
                h // 2 - 10,
                text="ПАУЗА",
                fill="#f8fafc",
                font=("Segoe UI", 22, "bold"),
            )
            self.canvas.create_text(
                w // 2,
                h // 2 + 18,
                text="Нажмите пробел для продолжения",
                fill="#cbd5e1",
                font=("Segoe UI", 11),
            )

        if self.game_over:
            self.canvas.create_rectangle(
                0, 0, w, h, fill="#020617", stipple="gray50", outline=""
            )
            self.canvas.create_text(
                w // 2,
                h // 2 - 24,
                text="ИГРА ОКОНЧЕНА",
                fill="#f87171",
                font=("Segoe UI", 22, "bold"),
            )
            self.canvas.create_text(
                w // 2,
                h // 2 + 6,
                text=f"Счёт: {self.score}   •   Рекорд: {self.highscore}",
                fill="#f8fafc",
                font=("Segoe UI", 13, "bold"),
            )
            self.canvas.create_text(
                w // 2,
                h // 2 + 34,
                text="Нажмите пробел для рестарта или Esc для выхода",
                fill="#cbd5e1",
                font=("Segoe UI", 10),
            )

    def draw_eyes(self, x: int, y: int):
        bx = x * CELL_SIZE
        by = y * CELL_SIZE
        offsets = {
            "Right": [(15, 6), (15, 15)],
            "Left": [(6, 6), (6, 15)],
            "Up": [(6, 6), (15, 6)],
            "Down": [(6, 15), (15, 15)],
        }
        for ex, ey in offsets.get(self.direction, [(15, 6), (15, 15)]):
            self.canvas.create_oval(
                bx + ex - 2,
                by + ey - 2,
                bx + ex + 2,
                by + ey + 2,
                fill="#052e16",
                outline="",
            )


if __name__ == "__main__":
    root = tk.Tk()
    SnakeProGame(root)
    root.mainloop()