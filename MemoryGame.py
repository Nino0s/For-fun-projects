"""
Memory Match  -  Normal mode, Challenge mode, settings, combos, generated card
art and a custom background.

Project folder layout (everything optional):
    MemoryGame.py
    images (2).jpg      <- used as the background (falls back to background.* / bg.*)
    images/             <- optional: drop your own pictures here to use them as cards

JPG/JPEG/WEBP backgrounds need Pillow:   pip install pillow
(Without Pillow only PNG/GIF backgrounds work and a gradient is drawn otherwise.)

NORMAL MODE
    No timer. Combos carry on from board to board (the multiplier is uncapped)
    and the boards keep getting bigger. Hit the score limit (10,000,000 by
    default, changeable in Settings) to win. MISS_LIMIT mismatches in a row
    without a single match ends the game; a prompt counts the moves left.

CHALLENGE MODE
    15 timed rounds. To clear a round you need BOTH the target score (1000 in
    round 1, +2000 every round) AND every card on the board matched. Each round
    gives you more time than the last, but the board is bigger, the target is
    higher, mismatched cards are shown for less time and every miss costs points.
    If you clear a board before reaching the target you get a fresh board.
    MISS_LIMIT misses in a row also ends a Challenge run, as does running out of time.

PAUSE
    The MENU button (top right) or Esc pauses the game, shows a short notice for
    3 seconds, then returns to the main menu. Your progress is kept (while the
    game window stays open): the mode's menu button then says "resume".

SETTINGS
    Font size, volume (High / Medium / Low / Vibrate / Mute) and the Normal-mode
    score limit. They are saved in settings.json.

Controls: click cards / buttons, Space = continue, Esc or MENU button = pause,
Esc on the main menu = quit.
"""
import copy
import json
import math
import os
import random
import shutil
import struct
import subprocess
import tempfile
import time
import tkinter as tk
import wave

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")
SCORE_FILE = os.path.join(BASE_DIR, "highscores.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

W, H = 900, 720
HUD_H = 95

# ---- tunables -------------------------------------------------------------
BG_NAME = "images (2)"          # background file name (without extension)
BG_DIM = 0.30                   # 0 = untouched, 1 = black; keeps cards readable

DEFAULT_SCORE_LIMIT = 10_000_000
SCORE_LIMITS = [100_000, 1_000_000, 10_000_000]
MISS_LIMIT = 10                 # Normal mode: mismatches in a row before game over
CHALLENGE_MAX_MULT = 8          # Challenge combo multiplier cap (Normal is uncapped)
BOARD_CLEAR_BONUS = 500         # bonus for a board / round cleared with no misses

MAX_ROUNDS = 15                 # Challenge mode length
ROUND_TARGET_START = 1000       # round 1 needs 1000 points ...
ROUND_TARGET_STEP = 2000        # ... and every round adds 2000 more (round 15 = 29,000)
MISS_PENALTY_STEP = 10          # round n: each miss costs 10 * (n - 1) points

# first round on which each board size is used in Challenge mode
ROUND_LAYOUT_STARTS = [(1, (2, 4)), (3, (3, 4)), (5, (4, 4)), (7, (4, 5)), (10, (4, 6))]
# Normal mode: board size per cleared board (the last one repeats)
BOARD_LAYOUTS = [(2, 4), (3, 4), (4, 4), (4, 5), (4, 6)]

FONT_ORDER = ["small", "medium", "large"]
FONT_SIZES = {"small": ("Small", 0.85), "medium": ("Medium", 1.0), "large": ("Large", 1.2)}
VOLUME_ORDER = ["high", "medium", "low", "vibrate", "mute"]
VOLUMES = {"high": ("High", 0.80), "medium": ("Medium", 0.40), "low": ("Low", 0.15),
           "vibrate": ("Vibrate", 0.0), "mute": ("Mute", 0.0)}

# (shape, color) - 12 distinct cards, enough for the biggest board (4x6)
SYMBOLS = [
    ("circle", "#E74C3C"), ("square", "#3498DB"), ("triangle", "#F1C40F"),
    ("diamond", "#9B59B6"), ("star", "#F39C12"), ("heart", "#E91E63"),
    ("plus", "#2ECC71"), ("hexagon", "#1ABC9C"), ("pentagon", "#E67E22"),
    ("ring", "#2980B9"), ("bolt", "#D4AC0D"), ("octagon", "#8E44AD"),
]

# sound effects: list of (frequency Hz, length ms)
SOUNDS = {
    "click": [(520, 30)],
    "flip": [(700, 40)],
    "match": [(660, 70), (880, 110)],
    "combo": [(784, 60), (988, 60), (1175, 130)],
    "miss": [(190, 150), (140, 220)],
    "clear": [(523, 90), (659, 90), (784, 90), (1047, 240)],
    "win": [(523, 90), (659, 90), (784, 90), (1047, 90), (1319, 320)],
    "over": [(392, 170), (330, 170), (262, 340)],
}


def regular_poly(cx, cy, r, n, rot=-90):
    pts = []
    for k in range(n):
        a = math.radians(rot + k * 360 / n)
        pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def layout_for_round(r):
    chosen = ROUND_LAYOUT_STARTS[0][1]
    for start, lay in ROUND_LAYOUT_STARTS:
        if r >= start:
            chosen = lay
    return chosen


def round_target(r):
    """Score needed to clear round r (the board must also be fully matched)."""
    return ROUND_TARGET_START + ROUND_TARGET_STEP * (r - 1)


def round_time(r):
    """Time grows every round: 40s, 46s, 52s ... 124s."""
    return 40 + 6 * (r - 1)


class MemoryGame:
    def __init__(self, root):
        self.root = root
        root.title("Memory Match")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg="#1b2a49")
        self.canvas.pack()

        self.settings = self.load_settings()
        self.sfx_dir = tempfile.mkdtemp(prefix="memory_sfx_")
        self.sfx = {}
        self.build_sounds()
        self.shaking = False

        self.custom_files = self.find_custom_images()
        self.photos = []
        self.bg_img = None
        self.bg_hint = None
        self.draw_background()

        self.scores = self.load_scores()
        self.mode = None            # None (menu) | "normal" | "challenge"
        self.state = "menu"         # menu | play | clearing | between | over
        self.screen = "menu"        # menu | settings (only meaningful when state == "menu")
        self.gen = 0                # bumped to cancel pending animations/callbacks
        self.round = 1
        self.board_no = 0
        self.score = 0
        self.round_score = 0
        self.target = ROUND_TARGET_START
        self.target_notified = False
        self.combo = 0
        self.best_combo = 0
        self.miss_streak = 0
        self.round_misses = 0
        self.board_misses = 0
        self.pairs = 0
        self.matched = 0
        self.cards = []
        self.selected = []
        self.lock = False
        self.time_left = 1
        self.time_limit = 1
        self.last = time.time()
        self.rows = self.cols = 0
        self.cs = 100
        self.btn_rects = []
        self.pause_rect = None
        self.photo_paths = []
        self.saved = {"normal": None, "challenge": None}   # paused sessions (in memory)

        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<space>", lambda e: self.advance())
        root.bind("<Escape>", self.on_escape)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.go_menu()
        self.tick()

    def on_close(self):
        shutil.rmtree(self.sfx_dir, ignore_errors=True)
        self.root.destroy()

    # ------------------------------------------------------------ settings
    @property
    def fs(self):
        return FONT_SIZES[self.settings["font"]][1]

    @property
    def score_limit(self):
        return self.settings["limit"]

    @property
    def volume(self):
        return self.settings["volume"]

    def F(self, size, weight="bold"):
        """Font tuple scaled by the font-size setting."""
        return ("Helvetica", max(7, int(round(size * self.fs))), weight)

    def load_settings(self):
        data = {"font": "medium", "volume": "high", "limit": DEFAULT_SCORE_LIMIT}
        try:
            with open(SETTINGS_FILE) as fh:
                loaded = json.load(fh)
            if loaded.get("font") in FONT_SIZES:
                data["font"] = loaded["font"]
            if loaded.get("volume") in VOLUMES:
                data["volume"] = loaded["volume"]
            if loaded.get("limit") in SCORE_LIMITS:
                data["limit"] = loaded["limit"]
        except (OSError, ValueError, AttributeError):
            pass
        return data

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as fh:
                json.dump(self.settings, fh)
        except OSError:
            pass

    def cycle_font(self):
        i = FONT_ORDER.index(self.settings["font"])
        self.settings["font"] = FONT_ORDER[(i + 1) % len(FONT_ORDER)]
        self.save_settings()
        self.show_settings()

    def cycle_volume(self):
        i = VOLUME_ORDER.index(self.settings["volume"])
        self.settings["volume"] = VOLUME_ORDER[(i + 1) % len(VOLUME_ORDER)]
        self.save_settings()
        self.build_sounds()
        self.show_settings()
        self.play("match")      # audible preview (silent for Vibrate / Mute)
        self.shake(6, 8)        # vibrate preview (does nothing unless Vibrate)

    def cycle_limit(self):
        i = SCORE_LIMITS.index(self.settings["limit"])
        self.settings["limit"] = SCORE_LIMITS[(i + 1) % len(SCORE_LIMITS)]
        self.save_settings()
        self.show_settings()

    # ------------------------------------------------------------ sound / vibrate
    def build_sounds(self):
        """(Re)generate the tiny WAV files at the current volume level."""
        amp = VOLUMES[self.volume][1]
        self.sfx = {}
        if amp <= 0:
            return
        rate = 22050
        for key, notes in SOUNDS.items():
            frames = bytearray()
            for freq, ms in notes:
                n = int(rate * ms / 1000)
                for i in range(n):
                    env = min(1.0, i / (0.004 * rate), (n - i) / (0.02 * rate))
                    v = math.sin(2 * math.pi * freq * i / rate)
                    frames += struct.pack("<h", int(32767 * amp * env * v))
            path = os.path.join(self.sfx_dir, key + ".wav")
            try:
                with wave.open(path, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(rate)
                    w.writeframes(bytes(frames))
                self.sfx[key] = path
            except OSError:
                pass

    def play(self, key):
        path = self.sfx.get(key)
        if not path or VOLUMES[self.volume][1] <= 0:
            return
        try:
            if HAS_WINSOUND:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            for cmd in (["afplay"], ["aplay", "-q"], ["paplay"]):
                if shutil.which(cmd[0]):
                    subprocess.Popen(cmd + [path], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return
            self.root.bell()
        except Exception:
            pass

    def shake(self, strength=6, steps=8):
        """'Vibrate' mode: jiggle the window instead of playing a sound."""
        if self.volume != "vibrate" or self.shaking:
            return
        try:
            x, y = self.root.winfo_x(), self.root.winfo_y()
        except Exception:
            return
        self.shaking = True
        offs = [(random.randint(-strength, strength), random.randint(-strength, strength))
                for _ in range(steps)]

        def step(k=0):
            try:
                if k >= len(offs):
                    self.root.geometry(f"+{x}+{y}")
                    self.shaking = False
                    return
                dx, dy = offs[k]
                self.root.geometry(f"+{x + dx}+{y + dy}")
                self.root.after(25, lambda: step(k + 1))
            except Exception:
                self.shaking = False
        step()

    # ------------------------------------------------------------ assets
    def find_custom_images(self):
        if not HAS_PIL or not os.path.isdir(IMAGES_DIR):
            return []
        ok = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
        return sorted(os.path.join(IMAGES_DIR, f) for f in os.listdir(IMAGES_DIR)
                      if f.lower().endswith(ok))

    def find_background_file(self):
        ok = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
        files = sorted(os.listdir(BASE_DIR))
        for f in files:                                   # 1) 'images (2).*'
            name, ext = os.path.splitext(f.lower())
            if ext in ok and name == BG_NAME:
                return os.path.join(BASE_DIR, f)
        for f in files:                                   # 2) background.* / bg.*
            name, ext = os.path.splitext(f.lower())
            if ext in ok and (name.startswith("background") or name.startswith("bg")):
                return os.path.join(BASE_DIR, f)
        return None

    def draw_background(self):
        path = self.find_background_file()
        try:
            if path and HAS_PIL:
                img = Image.open(path).convert("RGB")
                scale = max(W / img.width, H / img.height)  # "cover" fit
                img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
                left, top = (img.width - W) // 2, (img.height - H) // 2
                img = img.crop((left, top, left + W, top + H))
                if BG_DIM > 0:
                    img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), BG_DIM)
                self.bg_img = ImageTk.PhotoImage(img)
            elif path and path.lower().endswith((".png", ".gif")):
                self.bg_img = tk.PhotoImage(file=path)
            elif path:
                self.bg_hint = "Install Pillow to show %s:  pip install pillow" % os.path.basename(path)
        except Exception as exc:  # unreadable file -> fall back to gradient
            print("Could not load background:", exc)
            self.bg_img = None
            self.bg_hint = "Could not load %s" % os.path.basename(path)

        if self.bg_img:
            self.canvas.create_image(0, 0, image=self.bg_img, anchor="nw", tags="bg")
        else:
            top, bottom = (27, 42, 73), (74, 31, 94)
            for y in range(H):
                t = y / H
                col = "#%02x%02x%02x" % tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
                self.canvas.create_line(0, y, W, y, fill=col, tags="bg")
        self.canvas.tag_lower("bg")

    # ------------------------------------------------------------ high scores
    def load_scores(self):
        data = {"normal": 0, "challenge": 0}
        try:
            with open(SCORE_FILE) as fh:
                loaded = json.load(fh)
            for k in data:
                data[k] = int(loaded.get(k, 0))
        except (OSError, ValueError, AttributeError):
            pass
        return data

    def save_high_score(self):
        if self.mode and self.score > self.scores[self.mode]:
            self.scores[self.mode] = self.score
            try:
                with open(SCORE_FILE, "w") as fh:
                    json.dump(self.scores, fh)
            except OSError:
                pass

    def best_score(self):
        return max(self.scores.get(self.mode, 0), self.score)

    # ------------------------------------------------------------ menu / flow
    def reset_screen(self):
        self.gen += 1
        for tag in ("card", "popup", "banner", "overlay"):
            self.canvas.delete(tag)
        self.cards = []
        self.selected = []
        self.mode = None
        self.state = "menu"
        self.update_hud()

    def go_menu(self):
        self.reset_screen()
        self.screen = "menu"
        sn, sc = self.saved["normal"], self.saved["challenge"]
        n_label = "NORMAL MODE" + (f"   (resume: {sn['fields']['score']:,})" if sn else "")
        c_label = "CHALLENGE MODE" + (f"   (resume: round {sc['fields']['round']})" if sc else "")
        self.show_overlay(
            "MEMORY MATCH", [],
            [(n_label, lambda: self.enter_mode("normal"), True,
              f"Dare to hit {self.score_limit:,} points"),
             (c_label, lambda: self.enter_mode("challenge"), True,
              "Hit as many rounds as you can!"),
             ("SETTINGS", self.show_settings, False, "Font size, volume, score limit")])
        if self.bg_hint:
            self.canvas.create_text(W / 2, H - 14, text=self.bg_hint, fill="#F39C12",
                                    font=self.F(10, "normal"), tags="overlay")

    def show_settings(self):
        self.reset_screen()
        self.screen = "settings"
        font_name = FONT_SIZES[self.settings["font"]][0]
        vol_name = VOLUMES[self.volume][0]
        paused = [name for name, key in (("Normal", "normal"), ("Challenge", "challenge"))
                  if self.saved[key]]
        self.show_overlay(
            "SETTINGS", [],
            [(f"Font size:  {font_name}", self.cycle_font, False,
              "Small / Medium / Large"),
             (f"Volume:  {vol_name}", self.cycle_volume, False,
              "High / Medium / Low / Vibrate / Mute"),
             (f"Normal score limit:  {self.score_limit:,}", self.cycle_limit, False,
              "100,000 / 1,000,000 / 10,000,000"),
             ("Discard paused games", self.discard_saved, False,
              ("Paused: " + ", ".join(paused)) if paused else "No paused games"),
             ("BACK", self.go_menu, True, None)])

    def on_escape(self, event=None):
        if self.state == "paused":
            return                      # the 3-second pause notice can't be skipped
        if self.state == "play":
            self.pause_game()
        elif self.state == "between":
            self.leave_between()
        elif self.state == "menu" and self.screen == "menu":
            self.on_close()
        else:
            self.go_menu()

    # ---- pause / resume
    SAVE_FIELDS = ("score", "round", "board_no", "round_score", "target", "target_notified",
                   "combo", "best_combo", "miss_streak", "round_misses", "board_misses",
                   "pairs", "matched", "rows", "cols", "cs", "time_left", "time_limit")

    def pause_game(self):
        """Save the game, show the pause notice for 3 seconds, then open the main menu."""
        if self.state != "play":
            return
        for c in self.cards:                    # unmatched face-up cards go back down
            if not c["matched"]:
                c["face"] = False
        self.selected = []
        self.lock = False
        self.gen += 1                           # cancels pending flips / match checks
        self.saved[self.mode] = {
            "fields": {k: getattr(self, k) for k in self.SAVE_FIELDS},
            "cards": copy.deepcopy(self.cards),
            "photo_paths": list(self.photo_paths),
        }
        self.state = "paused"
        for tag in ("popup", "banner"):
            self.canvas.delete(tag)
        for i in range(len(self.cards)):
            self.draw_card(i)
        self.show_overlay(
            "GAME PAUSED",
            ["Game paused.", "Score will be retained when you",
             "return to the game mode.", "", "Returning to the main menu..."],
            [])
        gen = self.gen

        def to_menu():
            if gen == self.gen and self.state == "paused":
                self.go_menu()
        self.root.after(3200, to_menu)

    def enter_mode(self, mode):
        if self.saved[mode]:
            self.resume_game(mode)
        else:
            self.start_game(mode)

    def resume_game(self, mode):
        snap = self.saved[mode]
        self.saved[mode] = None
        self.mode = mode
        for k, v in snap["fields"].items():
            setattr(self, k, v)
        if snap.get("next_round"):              # left from the 'round cleared' screen
            self.combo = self.best_combo = self.miss_streak = 0
            self.begin_round()
            return
        self.gen += 1
        self.cards = copy.deepcopy(snap["cards"])
        self.photo_paths = list(snap["photo_paths"])
        self.photos = []
        if HAS_PIL and self.photo_paths:
            size = int(self.cs * 0.78)
            for path in self.photo_paths:
                img = Image.open(path).convert("RGBA")
                img.thumbnail((size, size))
                self.photos.append(ImageTk.PhotoImage(img))
        self.selected = []
        self.lock = False
        self.btn_rects = []
        for tag in ("card", "overlay", "popup", "banner"):
            self.canvas.delete(tag)
        for i in range(len(self.cards)):
            self.draw_card(i)
        self.state = "play"
        self.last = time.time()
        self.update_hud()
        self.banner("Welcome back!", "#FFFFFF", ms=1500)

    def leave_between(self):
        """MAIN MENU from the 'round cleared' screen: keep progress for the next round."""
        self.saved["challenge"] = {
            "fields": {"score": self.score, "round": self.round + 1},
            "next_round": True,
        }
        self.go_menu()

    def discard_saved(self):
        self.saved = {"normal": None, "challenge": None}
        self.show_settings()

    def start_game(self, mode):
        self.saved[mode] = None
        self.mode = mode
        self.score = 0
        self.round = 1
        self.board_no = 0
        self.combo = 0
        self.best_combo = 0
        self.miss_streak = 0
        self.round_misses = 0
        self.round_score = 0
        self.time_limit = self.time_left = 1
        if mode == "challenge":
            self.begin_round()
        else:
            self.start_board()

    def advance(self):
        if self.state == "between":
            self.round += 1
            self.begin_round()
        elif self.state == "over" and self.mode:
            self.start_game(self.mode)

    # ------------------------------------------------------------ rounds & boards
    def begin_round(self):
        """Challenge mode: set up a new round."""
        self.round_score = 0
        self.round_misses = 0
        self.best_combo = 0
        self.combo = 0
        self.target = round_target(self.round)
        self.target_notified = False
        self.miss_streak = 0
        self.time_limit = round_time(self.round)
        self.time_left = self.time_limit
        self.start_board()
        self.banner(f"Round {self.round}: reach {self.target:,} + clear all cards",
                    "#FFFFFF", ms=2800)

    def reveal_ms(self):
        """How long a mismatched pair stays face up (shrinks in Challenge mode)."""
        if self.mode == "challenge":
            return max(400, 650 - 18 * (self.round - 1))
        return 650

    def compute_layout(self):
        gap = 12
        top_pad, bottom_pad = 44, 24      # room for the banner above the board
        avail_w = W - 60
        avail_h = H - HUD_H - top_pad - bottom_pad
        cs = min((avail_w - (self.cols - 1) * gap) / self.cols,
                 (avail_h - (self.rows - 1) * gap) / self.rows, 150)
        self.cs = int(cs)
        total_w = self.cols * self.cs + (self.cols - 1) * gap
        total_h = self.rows * self.cs + (self.rows - 1) * gap
        x0 = (W - total_w) / 2
        y0 = HUD_H + top_pad + (avail_h - total_h) / 2
        return gap, x0, y0

    def start_board(self):
        self.gen += 1
        if self.mode == "challenge":
            self.rows, self.cols = layout_for_round(self.round)
        else:
            self.rows, self.cols = BOARD_LAYOUTS[min(self.board_no, len(BOARD_LAYOUTS) - 1)]
        self.pairs = self.rows * self.cols // 2
        self.matched = 0
        self.board_misses = 0
        self.selected = []
        self.lock = False
        self.btn_rects = []
        for tag in ("card", "overlay", "popup", "banner"):
            self.canvas.delete(tag)

        gap, x0, y0 = self.compute_layout()

        # card art: user images if enough, else generated shapes
        self.photos = []
        self.photo_paths = []
        if HAS_PIL and len(self.custom_files) >= self.pairs:
            size = int(self.cs * 0.78)
            self.photo_paths = random.sample(self.custom_files, self.pairs)
            for path in self.photo_paths:
                img = Image.open(path).convert("RGBA")
                img.thumbnail((size, size))
                self.photos.append(ImageTk.PhotoImage(img))
            kinds = list(range(self.pairs))
        else:
            kinds = random.sample(range(len(SYMBOLS)), self.pairs)

        deck = kinds * 2
        random.shuffle(deck)
        self.cards = []
        for idx, kind in enumerate(deck):
            r, c = divmod(idx, self.cols)
            self.cards.append({
                "kind": kind, "face": False, "matched": False,
                "cx": x0 + c * (self.cs + gap) + self.cs / 2,
                "cy": y0 + r * (self.cs + gap) + self.cs / 2,
            })
        for i in range(len(self.cards)):
            self.draw_card(i)

        self.state = "play"
        self.last = time.time()
        self.update_hud()

    # ------------------------------------------------------------ drawing
    def rounded_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def draw_symbol(self, kind, cx, cy, r, tags):
        shape, color = SYMBOLS[kind]
        kw = dict(fill=color, outline="#2C3E50", width=2, tags=tags)
        cv = self.canvas
        if shape == "circle":
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, **kw)
        elif shape == "square":
            cv.create_rectangle(cx - r * .85, cy - r * .85, cx + r * .85, cy + r * .85, **kw)
        elif shape == "triangle":
            cv.create_polygon(cx, cy - r, cx + r * .95, cy + r * .75, cx - r * .95, cy + r * .75, **kw)
        elif shape == "diamond":
            cv.create_polygon(cx, cy - r, cx + r * .75, cy, cx, cy + r, cx - r * .75, cy, **kw)
        elif shape == "star":
            pts = []
            for k in range(10):
                a = math.radians(-90 + k * 36)
                rad = r if k % 2 == 0 else r * .45
                pts += [cx + rad * math.cos(a), cy + rad * math.sin(a)]
            cv.create_polygon(pts, **kw)
        elif shape == "heart":
            pts = []
            for k in range(40):
                t = k / 40 * 2 * math.pi
                x = 16 * math.sin(t) ** 3
                y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
                pts += [cx + x * r / 17, cy - y * r / 17 - r * .05]
            cv.create_polygon(pts, **kw)
        elif shape == "plus":
            t = r * .36
            pts = [-t, -r, t, -r, t, -t, r, -t, r, t, t, t, t, r, -t, r, -t, t, -r, t, -r, -t, -t, -t]
            cv.create_polygon([cx + v if i % 2 == 0 else cy + v for i, v in enumerate(pts)], **kw)
        elif shape == "hexagon":
            cv.create_polygon(regular_poly(cx, cy, r, 6, 0), **kw)
        elif shape == "pentagon":
            cv.create_polygon(regular_poly(cx, cy, r, 5), **kw)
        elif shape == "octagon":
            cv.create_polygon(regular_poly(cx, cy, r, 8, 22.5), **kw)
        elif shape == "ring":
            cv.create_oval(cx - r * .8, cy - r * .8, cx + r * .8, cy + r * .8,
                           outline=color, width=max(3, int(r * .35)), tags=tags)
        elif shape == "bolt":
            pts = [.25, -1, -.55, .15, -.05, .15, -.25, 1, .55, -.2, .05, -.2]
            cv.create_polygon([cx + v * r if i % 2 == 0 else cy + v * r for i, v in enumerate(pts)], **kw)

    def draw_card(self, i, scale=1.0, face=None):
        c = self.cards[i]
        tags = ("card", f"card{i}")
        self.canvas.delete(f"card{i}")
        face = c["face"] if face is None else face
        half = self.cs / 2
        sx = max(2, half * scale)
        x1, x2 = c["cx"] - sx, c["cx"] + sx
        y1, y2 = c["cy"] - half, c["cy"] + half
        radius = min(14, sx * .9)
        if c["matched"]:
            fill, outline = "#CFF5DD", "#2ECC71"
        elif face:
            fill, outline = "#ECF0F1", "#BDC3C7"
        else:
            fill, outline = "#2C3E50", "#5D7A99"
        self.rounded_rect(x1, y1, x2, y2, radius, fill=fill, outline=outline, width=3, tags=tags)
        if face:
            if self.photos:
                if scale > .9:
                    self.canvas.create_image(c["cx"], c["cy"], image=self.photos[c["kind"]], tags=tags)
            elif scale > .45:
                self.draw_symbol(c["kind"], c["cx"], c["cy"], self.cs * .3 * scale, tags)
        elif scale > .5:
            self.canvas.create_text(c["cx"], c["cy"], text="?", fill="#8FB4D9",
                                    font=("Helvetica", int(self.cs * .38), "bold"), tags=tags)

    def flip(self, i, to_face):
        gen = self.gen
        card = self.cards[i]
        old = card["face"]
        seq = [(.75, old), (.5, old), (.25, old), (.1, old),
               (.1, to_face), (.25, to_face), (.5, to_face), (.75, to_face)]

        def step(k=0):
            if gen != self.gen:
                return
            if k >= len(seq):
                card["face"] = to_face
                self.draw_card(i)
                return
            s, f = seq[k]
            self.draw_card(i, s, f)
            self.root.after(20, lambda: step(k + 1))
        step()

    def max_mult(self):
        return float("inf") if self.mode == "normal" else CHALLENGE_MAX_MULT

    def moves_left(self):
        return MISS_LIMIT - self.miss_streak

    def update_hud(self):
        cv = self.canvas
        cv.delete("hud")
        if self.mode is None:
            self.pause_rect = None
            return
        cv.create_rectangle(0, 0, W, HUD_H, fill="#0B1426", stipple="gray50", outline="", tags="hud")
        lab = self.F(10)
        big = self.F(22)

        def stat(x, label, value, color="white", anchor="w"):
            cv.create_text(x, 22, text=label, fill="#8FB4D9", font=lab, anchor=anchor, tags="hud")
            cv.create_text(x, 52, text=value, fill=color, font=big, anchor=anchor, tags="hud")

        mult = min(self.combo, self.max_mult())
        if self.mode == "normal":
            stat(30, "CARDS", str(self.pairs * 2))
            stat(125, "SCORE", f"{self.score:,}")
            stat(320, "BEST", f"{self.best_score():,}", "#F1C40F")
            combo_x = 530
            left = self.moves_left()
            stat(W - 125, "MOVES LEFT", str(left), "#E74C3C" if left <= 3 else "white", "e")
            frac = left / MISS_LIMIT
        else:
            stat(30, "ROUND", f"{self.round}/{MAX_ROUNDS}")
            stat(135, "SCORE", f"{self.score:,}")
            hit = self.round_score >= self.target
            stat(300, "TARGET", f"{min(self.round_score, self.target)}/{self.target}",
                 "#2ECC71" if hit else "white")
            combo_x = 520
            stat(W - 125, "TIME", f"{max(0, int(math.ceil(self.time_left)))}s", "white", "e")
            frac = max(0, min(1, self.time_left / self.time_limit)) if self.time_limit else 0

        cv.create_text(combo_x, 22, text="COMBO", fill="#8FB4D9", font=lab, anchor="w", tags="hud")
        cv.create_text(combo_x, 52, text=f"x{mult}" if mult else "-",
                       fill="#FF9F43" if mult >= 2 else "white", font=big, anchor="w", tags="hud")
        for k in range(8):  # combo meter pips
            cv.create_rectangle(combo_x + 75 + k * 12, 46, combo_x + 84 + k * 12, 58,
                                fill="#FF9F43" if k < mult else "#34495E", outline="", tags="hud")

        color = "#2ECC71" if frac > .5 else "#F39C12" if frac > .25 else "#E74C3C"
        cv.create_rectangle(30, 80, W - 30, 88, fill="#34495E", outline="", tags="hud")
        cv.create_rectangle(30, 80, 30 + (W - 60) * max(0, min(1, frac)), 88,
                            fill=color, outline="", tags="hud")

        # pause / main-menu button, top right corner
        x1, y1, x2, y2 = W - 108, 8, W - 16, 40
        self.pause_rect = (x1, y1, x2, y2)
        self.rounded_rect(x1, y1, x2, y2, 8, fill="#34495E", outline="#8FB4D9",
                          width=2, tags="hud")
        cv.create_rectangle(x1 + 12, y1 + 9, x1 + 17, y2 - 9, fill="white", outline="", tags="hud")
        cv.create_rectangle(x1 + 22, y1 + 9, x1 + 27, y2 - 9, fill="white", outline="", tags="hud")
        cv.create_text(x1 + 36, (y1 + y2) / 2, text="MENU", fill="white",
                       font=self.F(11), anchor="w", tags="hud")

    def popup(self, text, x, y, color="#F1C40F"):
        item = self.canvas.create_text(x, y, text=text, fill=color,
                                       font=self.F(22), tags="popup")

        def rise(n=0):
            if n >= 22:
                self.canvas.delete(item)
                return
            self.canvas.move(item, 0, -2)
            self.root.after(25, lambda: rise(n + 1))
        rise()

    def banner(self, text, color="#F1C40F", ms=1300):
        """Prompt shown just above the board (e.g. '6 moves remaining')."""
        cv = self.canvas
        cv.delete("banner")
        x, y = W / 2, HUD_H + 22
        ids = [
            cv.create_text(x + 2, y + 2, text=text, fill="black",
                           font=self.F(20), tags="banner"),
            cv.create_text(x, y, text=text, fill=color,
                           font=self.F(20), tags="banner"),
        ]
        self.root.after(ms, lambda: cv.delete(*ids))

    def banner_clear(self):
        self.canvas.delete("banner")

    def show_overlay(self, title, lines, buttons):
        """buttons: list of (label, callback, primary, subtitle_or_None)"""
        cv = self.canvas
        cv.delete("overlay")
        self.btn_rects = []
        fs = max(1.0, self.fs)
        line_h = int(26 * self.fs)
        gap = 14
        heights = [int((60 if b[3] else 46) * fs) for b in buttons]
        content = (len(lines) * line_h + (10 if lines else 0)
                   + sum(heights) + gap * max(0, len(buttons) - 1))
        panel_h = min(H - HUD_H - 10, 100 + content + 30)
        cx, cy = W / 2, HUD_H + (H - HUD_H) / 2
        top, bottom = cy - panel_h / 2, cy + panel_h / 2

        cv.create_rectangle(0, HUD_H, W, H, fill="black", stipple="gray50", outline="", tags="overlay")
        self.rounded_rect(cx - 310, top, cx + 310, bottom, 24, fill="#1B2A49",
                          outline="#F1C40F", width=3, tags="overlay")
        cv.create_text(cx, top + 52, text=title, fill="#F1C40F",
                       font=self.F(30), tags="overlay")
        for k, line in enumerate(lines):
            cv.create_text(cx, top + 105 + k * line_h, text=line, fill="white",
                           font=self.F(13, "normal"), tags="overlay")
        y = top + 100 + len(lines) * line_h + (10 if lines else 0)
        for (label, cb, primary, sub), h in zip(buttons, heights):
            x1, y1, x2, y2 = cx - 260, y, cx + 260, y + h
            by = (y1 + y2) / 2
            self.rounded_rect(x1, y1, x2, y2, 14,
                              fill="#F1C40F" if primary else "#34495E",
                              outline="", tags="overlay")
            fg = "#1B2A49" if primary else "white"
            sub_fg = "#34495E" if primary else "#BFD3E6"
            if sub:
                cv.create_text(cx, by - 11 * self.fs, text=label, fill=fg,
                               font=self.F(15), tags="overlay")
                cv.create_text(cx, by + 13 * self.fs, text=sub, fill=sub_fg,
                               font=self.F(11, "normal"), tags="overlay")
            else:
                cv.create_text(cx, by, text=label, fill=fg,
                               font=self.F(15), tags="overlay")
            self.btn_rects.append((x1, y1, x2, y2, cb))
            y += h + gap

    def show_end_prompt(self, title, message, stats, retry_cb):
        """Game-over prompt: the message, TOTAL SCORE on the right, and on the left
        a RETRY button with MAIN MENU directly below it."""
        cv = self.canvas
        cv.delete("overlay")
        self.btn_rects = []
        fs = max(1.0, self.fs)
        bh = int(54 * fs)
        gap = 14
        stat_h = int(24 * self.fs)
        left_h = 2 * bh + gap
        right_h = int(10 + 70 * self.fs + len(stats) * stat_h)
        body_h = max(left_h, right_h)
        panel_h = min(H - HUD_H - 10, 130 + body_h + 30)
        cx, cy = W / 2, HUD_H + (H - HUD_H) / 2
        top, bottom = cy - panel_h / 2, cy + panel_h / 2

        cv.create_rectangle(0, HUD_H, W, H, fill="black", stipple="gray50", outline="", tags="overlay")
        self.rounded_rect(cx - 330, top, cx + 330, bottom, 24, fill="#1B2A49",
                          outline="#F1C40F", width=3, tags="overlay")
        cv.create_text(cx, top + 48, text=title, fill="#F1C40F", font=self.F(28), tags="overlay")
        cv.create_text(cx, top + 92, text=message, fill="white",
                       font=self.F(14, "normal"), tags="overlay")

        y = top + 130
        x1, x2 = cx - 300, cx - 40
        for label, cb, primary in (("RETRY", retry_cb, True), ("MAIN MENU", self.go_menu, False)):
            self.rounded_rect(x1, y, x2, y + bh, 14, fill="#F1C40F" if primary else "#34495E",
                              outline="", tags="overlay")
            cv.create_text((x1 + x2) / 2, y + bh / 2, text=label,
                           fill="#1B2A49" if primary else "white", font=self.F(15), tags="overlay")
            self.btn_rects.append((x1, y, x2, y + bh, cb))
            y += bh + gap

        cv.create_line(cx - 15, top + 130, cx - 15, top + 130 + body_h,
                       fill="#34495E", width=2, tags="overlay")
        rx = cx + 150
        ty = top + 142
        cv.create_text(rx, ty, text="TOTAL SCORE", fill="#8FB4D9", font=self.F(11), tags="overlay")
        vy = ty + int(34 * self.fs)
        cv.create_text(rx, vy, text=f"{self.score:,}", fill="white", font=self.F(28), tags="overlay")
        for k, line in enumerate(stats):
            cv.create_text(rx, vy + int(36 * self.fs) + k * stat_h, text=line, fill="#BFD3E6",
                           font=self.F(12, "normal"), tags="overlay")

    # ------------------------------------------------------------ gameplay
    def card_at(self, x, y):
        half = self.cs / 2
        for i, c in enumerate(self.cards):
            if abs(x - c["cx"]) <= half and abs(y - c["cy"]) <= half:
                return i
        return None

    def on_click(self, event):
        if self.state != "play":
            for x1, y1, x2, y2, cb in self.btn_rects:
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    self.play("click")
                    cb()
                    return
            return
        if self.pause_rect:
            x1, y1, x2, y2 = self.pause_rect
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.play("click")
                self.pause_game()
                return
        if self.lock:
            return
        i = self.card_at(event.x, event.y)
        if i is None:
            return
        card = self.cards[i]
        if card["matched"] or card["face"] or i in self.selected:
            return
        self.selected.append(i)
        self.play("flip")
        self.flip(i, True)
        if len(self.selected) == 2:
            self.lock = True
            gen = self.gen
            self.root.after(self.reveal_ms(), lambda: self.check_match(gen))

    def check_match(self, gen):
        if gen != self.gen or self.state != "play":
            return
        a, b = self.selected
        ca, cb = self.cards[a], self.cards[b]
        if ca["kind"] == cb["kind"]:
            self.on_match(a, b, ca, cb)
        else:
            self.on_miss(a, b)

    def on_match(self, a, b, ca, cb):
        for i, c in ((a, ca), (b, cb)):
            c["matched"] = True
            c["face"] = True
            self.draw_card(i)
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        self.miss_streak = 0
        mult = min(self.combo, self.max_mult())
        pts = 100 * mult
        self.score += pts
        self.round_score += pts
        self.matched += 1
        mx, my = (ca["cx"] + cb["cx"]) / 2, (ca["cy"] + cb["cy"]) / 2
        label = f"+{pts:,}" + (f"  COMBO x{mult}!" if mult >= 2 else "")
        self.popup(label, mx, my, "#FF9F43" if mult >= 2 else "#F1C40F")
        self.play("combo" if mult >= 3 else "match")
        if mult >= 5:
            self.shake(3, 6)
        self.selected = []
        self.lock = False
        self.banner_clear()
        self.update_hud()

        if self.mode == "normal" and self.score >= self.score_limit:
            self.score = self.score_limit
            self.finish_normal(won=True)
        elif self.matched == self.pairs:
            self.board_clear()      # challenge: clears the round only if the target is met too
        elif (self.mode == "challenge" and self.round_score >= self.target
              and not self.target_notified):
            self.target_notified = True
            self.banner("Target reached! Now clear the remaining cards", "#2ECC71", ms=2200)

    def on_miss(self, a, b):
        self.combo = 0
        self.board_misses += 1
        self.round_misses += 1
        self.flip(a, False)
        self.flip(b, False)
        self.selected = []
        self.lock = False
        self.play("miss")
        self.shake(6, 8)
        self.miss_streak += 1
        left = self.moves_left()
        if self.mode == "challenge":
            pen = MISS_PENALTY_STEP * (self.round - 1)
            if pen:
                lost = min(pen, self.score)
                self.score -= lost
                self.round_score = max(0, self.round_score - pen)
                ca, cb = self.cards[a], self.cards[b]
                self.popup(f"-{lost}", (ca["cx"] + cb["cx"]) / 2,
                           (ca["cy"] + cb["cy"]) / 2, "#E74C3C")
        self.update_hud()
        if left <= 0:                       # max missed limit hit
            if self.mode == "normal":
                self.finish_normal(won=False)
            else:
                self.end_challenge("misses")
            return
        word = "move" if left == 1 else "moves"
        self.banner(f"{left} {word} remaining", "#E74C3C" if left <= 3 else "#F39C12")

    def board_clear(self):
        """Every pair on the board found (before the mode's own goal was met)."""
        self.state = "clearing"
        bonus = BOARD_CLEAR_BONUS if self.board_misses == 0 else 0
        if bonus:
            self.score += bonus
            self.round_score += bonus
        if self.mode == "challenge" and self.round_score < self.target:
            msg = (f"Board cleared, but only {self.round_score}/{self.target} - new board!")
        else:
            msg = f"Perfect board! +{bonus}" if bonus else "Board cleared!"
        self.banner(msg, "#2ECC71", ms=900)
        self.update_hud()
        gen = self.gen

        if self.mode == "normal" and self.score >= self.score_limit:
            self.score = self.score_limit
            self.finish_normal(won=True)
            return
        if self.mode == "challenge" and self.round_score >= self.target:
            self.round_clear()
            return

        def nxt():
            if gen != self.gen:
                return
            if self.mode == "normal":
                self.board_no += 1       # normal mode: boards keep getting bigger
            self.start_board()           # challenge: fresh board, same size
        self.root.after(800, nxt)

    # ---- challenge: round clear / game over
    def round_clear(self):
        self.state = "clearing"
        time_bonus = int(self.time_left) * 10
        perfect = BOARD_CLEAR_BONUS if self.round_misses == 0 else 0
        self.score += time_bonus + perfect
        self.save_high_score()
        self.update_hud()
        self.play("clear")
        self.shake(4, 8)
        gen = self.gen

        def show():
            if gen != self.gen:
                return
            lines = [f"Time bonus:  +{time_bonus}",
                     f"Perfect round bonus:  +{perfect}" if perfect
                     else f"Misses:  {self.round_misses}",
                     f"Best combo:  x{min(self.best_combo, self.max_mult())}",
                     f"Score:  {self.score:,}"]
            if self.round >= MAX_ROUNDS:
                self.end_challenge("complete")
                return
            self.state = "between"
            nxt = self.round + 1
            rows, cols = layout_for_round(nxt)
            self.show_overlay(
                f"ROUND {self.round} CLEARED!", lines,
                [(f"NEXT ROUND  ({nxt}/{MAX_ROUNDS})", self.advance, True,
                  f"{rows * cols} cards  -  {round_time(nxt)}s  -  target {round_target(nxt):,}"),
                 ("MAIN MENU", self.leave_between, False, None)])
        self.root.after(500, show)

    def time_up(self):
        self.end_challenge("time")

    def end_challenge(self, reason):
        """reason: 'time' (ran out of time) | 'misses' (max missed limit) | 'complete'"""
        self.state = "over"
        self.gen += 1  # cancels pending animations / callbacks
        self.saved["challenge"] = None
        self.save_high_score()
        self.update_hud()
        best = f"Best score: {self.scores['challenge']:,}"
        if reason == "complete":
            title, msg = "CHALLENGE COMPLETE!", f"All {MAX_ROUNDS} rounds cleared. Amazing!"
            stats = [f"{MAX_ROUNDS} of {MAX_ROUNDS} rounds", best]
            self.play("win")
        else:
            stats = [f"Round {self.round} of {MAX_ROUNDS}",
                     f"Round score {self.round_score:,} / {self.target:,}", best]
            if reason == "time":
                title, msg = "TIME'S UP!", "You ran out of time."
            else:
                title = "LIMIT HIT"
                msg = f"You hit the max missed limit - {MISS_LIMIT} misses in a row."
            self.play("over")
            self.shake(10, 12)
        self.show_end_prompt(title, msg, stats, self.advance)

    # ---- normal: game over / win
    def finish_normal(self, won):
        self.state = "over"
        self.gen += 1
        self.saved["normal"] = None
        self.save_high_score()
        self.update_hud()
        stats = [f"Best combo: x{self.best_combo}",
                 f"Board: {self.pairs * 2} cards",
                 f"Best score: {self.scores['normal']:,}"]
        if won:
            self.play("win")
            title = "SCORE LIMIT REACHED!"
            msg = f"You hit {self.score_limit:,} points. Incredible!"
        else:
            self.play("over")
            self.shake(10, 12)
            title = "LIMIT HIT"
            msg = f"You hit the max missed limit - {MISS_LIMIT} misses in a row."
        self.show_end_prompt(title, msg, stats, self.advance)

    def tick(self):
        now = time.time()
        if self.state == "play" and self.mode == "challenge":
            self.time_left -= now - self.last
            if self.time_left <= 0:
                self.time_left = 0
                self.time_up()
            else:
                self.update_hud()
        self.last = now
        self.root.after(100, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    MemoryGame(root)
    root.mainloop()