#!/usr/bin/env python3
"""
D A T A   B R E A C H - A Pygame Hacker Game
==============================================
You are AGENT CIPHER. Complete 3 security protocols to redact a classified
file, then input the intel to stop a terrorist attack. Beat the clock.

Controls: Arrow keys, ENTER, SPACE, ESC. Type answers in intel phase.
Requires: Python 3, pygame (pip install pygame)
"""

import pygame
import sys
import os
import json
import random
import math
import time
import asyncio

# --- DEBUG MODE (F1=skip minigame, F2=add 60s, F3=jump to intel) ---------
DEBUG = "--debug" in sys.argv

# --- INIT --------------------------------------------------------------------
pygame.init()

WIDTH, HEIGHT = 1024, 768
FPS = 60

# Left-hand sidebar dimensions (timer + redaction file panel).
# The active minigame draws into the right-hand "game area" alongside it.
SIDEBAR_X = 16
SIDEBAR_W = 280
SIDEBAR_INNER_PAD = 14
GAME_AREA_X = SIDEBAR_X + SIDEBAR_W + 16
GAME_AREA_W = WIDTH - GAME_AREA_X - 16
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DATA BREACH")
clock = pygame.time.Clock()

# --- COLORS ------------------------------------------------------------------
BLACK       = (5, 5, 5)
GREEN       = (0, 230, 0)
GREEN_DIM   = (0, 140, 0)
GREEN_BRIGHT= (50, 255, 50)
WHITE       = (240, 240, 240)
RED         = (230, 30, 30)
RED_BRIGHT  = (255, 80, 80)
YELLOW      = (230, 230, 0)
CYAN        = (0, 230, 230)
CYAN_BRIGHT = (50, 255, 255)
DARK_GREEN  = (0, 60, 0)

# --- FONTS -------------------------------------------------------------------
MONO_NAMES = ["Consolas", "Courier New", "Courier", "monospace", "Liberation Mono"]
def _get_mono_font(size):
    for name in MONO_NAMES:
        f = pygame.font.SysFont(name, size)
        if f:
            return f
    return pygame.font.Font(None, size)

FONT_SM = _get_mono_font(20)
FONT_MD = _get_mono_font(26)
FONT_LG = _get_mono_font(36)
FONT_XL = _get_mono_font(52)
FONT_TITLE = _get_mono_font(68)
FONT_HUGE = _get_mono_font(96)

# --- SOUND (disabled - placeholder stubs) ------------------------------------
def play_sound(snd):
    pass

# --- PIXEL FONT FOR TITLE -----------------------------------------------------
# Each letter is a 5-wide x 7-tall grid of 0/1
PIXEL_FONT = {
    'D': [
        "1111 ",
        "1  11",
        "1   1",
        "1   1",
        "1   1",
        "1  11",
        "1111 ",
    ],
    'A': [
        " 111 ",
        "1   1",
        "1   1",
        "11111",
        "1   1",
        "1   1",
        "1   1",
    ],
    'T': [
        "11111",
        "  1  ",
        "  1  ",
        "  1  ",
        "  1  ",
        "  1  ",
        "  1  ",
    ],
    'B': [
        "1111 ",
        "1   1",
        "1   1",
        "1111 ",
        "1   1",
        "1   1",
        "1111 ",
    ],
    'R': [
        "1111 ",
        "1   1",
        "1   1",
        "1111 ",
        "1 1  ",
        "1  1 ",
        "1   1",
    ],
    'E': [
        "11111",
        "1    ",
        "1    ",
        "1111 ",
        "1    ",
        "1    ",
        "11111",
    ],
    'C': [
        " 1111",
        "1    ",
        "1    ",
        "1    ",
        "1    ",
        "1    ",
        " 1111",
    ],
    'H': [
        "1   1",
        "1   1",
        "1   1",
        "11111",
        "1   1",
        "1   1",
        "1   1",
    ],
    ' ': [
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
    ],
}

def draw_pixel_text(surface, text, start_x, start_y, pixel_size, color, glow_color=None):
    """Draw text using pixel block font. Returns total width drawn."""
    cx = start_x
    for ch in text:
        glyph = PIXEL_FONT.get(ch.upper(), PIXEL_FONT[' '])
        for row_i, row in enumerate(glyph):
            for col_i, cell in enumerate(row):
                if cell == '1':
                    bx = cx + col_i * pixel_size
                    by = start_y + row_i * pixel_size
                    if glow_color:
                        # Draw a slightly larger glow behind
                        pygame.draw.rect(surface, glow_color,
                            (bx - 1, by - 1, pixel_size + 2, pixel_size + 2))
                    pygame.draw.rect(surface, color,
                        (bx, by, pixel_size, pixel_size))
        cx += (len(glyph[0]) + 1) * pixel_size  # +1 for spacing between letters
    return cx - start_x

def draw_pixel_text_centered(surface, text, y, pixel_size, color, glow_color=None):
    """Draw pixel text centered horizontally."""
    # Calculate total width first
    total_w = 0
    for ch in text:
        glyph = PIXEL_FONT.get(ch.upper(), PIXEL_FONT[' '])
        total_w += (len(glyph[0]) + 1) * pixel_size
    total_w -= pixel_size  # Remove last spacing
    start_x = (surface.get_width() - total_w) // 2
    draw_pixel_text(surface, text, start_x, y, pixel_size, color, glow_color)

# --- SAVE FILE ---------------------------------------------------------------
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".databreach_save.json")

def load_save():
    try:
        with open(SAVE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"best": {}, "last_difficulty": "AGENT"}

def save_game(data):
    with open(SAVE_PATH, "w") as f:
        json.dump(data, f)

# --- DIFFICULTY --------------------------------------------------------------
DIFFICULTIES = {
    "RECRUIT": {
        "label": "RECRUIT",
        "description": "For first-time agents. Generous time, slow roulette.",
        "roulette_time": 60,
        "maze_time": 90,
        "connect_time": 90,
        "intel_time": 90,
        "roulette_digits": 3,
        "roulette_speed": (0.55, 0.75),
        "roulette_keep": True,
        "maze_size": (18, 12),
        "maze_fog": 0,
        "num_nodes": 5,
        "num_obstacles": 8,
        "num_gates": 1,
        "node_cross_mode": "none",
        "intel_attempts": 5,
        "event_cooldown": 25, "hack_cooldown": 30,
        "maze_guards": 0, "guard_speed": 2.5, "guard_vision": 3,
    },
    "AGENT": {
        "label": "AGENT",
        "description": "Standard field operation. Balanced challenge.",
        "roulette_time": 50,
        "maze_time": 75,
        "connect_time": 80,
        "intel_time": 60,
        "roulette_digits": 4,
        "roulette_speed": (0.35, 0.55),
        "roulette_keep": True,
        "maze_size": (24, 16),
        "maze_fog": 0,
        "num_nodes": 6,
        "num_obstacles": 12,
        "num_gates": 1,
        "node_cross_mode": "last",
        "intel_attempts": 3,
        "event_cooldown": 18, "hack_cooldown": 20,
        "maze_guards": 1, "guard_speed": 3.0, "guard_vision": 4,
    },
    "SHADOW": {
        "label": "SHADOW",
        "description": "Elite operatives only. Fog of war, full roulette reset.",
        "roulette_time": 45,
        "maze_time": 65,
        "connect_time": 65,
        "intel_time": 50,
        "roulette_digits": 5,
        "roulette_speed": (0.20, 0.35),
        "roulette_keep": False,
        "maze_size": (30, 20),
        "maze_fog": 6,
        "num_nodes": 8,
        "num_obstacles": 16,
        "num_gates": 2,
        "node_cross_mode": "full",
        "intel_attempts": 2,
        "event_cooldown": 12, "hack_cooldown": 14,
        "maze_guards": 3, "guard_speed": 3.5, "guard_vision": 5,
    },
    "GHOST": {
        "label": "GHOST",
        "description": "Impossible. Fog of war, no mercy. Prove yourself.",
        "roulette_time": 35,
        "maze_time": 50,
        "connect_time": 50,
        "intel_time": 35,
        "roulette_digits": 6,
        "roulette_speed": (0.12, 0.22),
        "roulette_keep": False,
        "maze_size": (36, 24),
        "maze_fog": 5,
        "num_nodes": 10,
        "num_obstacles": 20,
        "num_gates": 3,
        "node_cross_mode": "full",
        "intel_attempts": 1,
        "event_cooldown": 8, "hack_cooldown": 9,
        "maze_guards": 3, "guard_speed": 4.0, "guard_vision": 6,
    },
}
DIFFICULTY_ORDER = ["RECRUIT", "AGENT", "SHADOW", "GHOST"]
RANK_ORDER = ["CATASTROPHIC FAILURE", "POOR", "ADEQUATE", "EXCELLENT", "LEGENDARY"]

# --- DISRUPTION EVENTS -------------------------------------------------------
DISRUPTION_EVENTS = [
    {"name": "INTRUSION DETECTED",  "duration": 5.0, "effect": "invert_controls",
     "color": RED, "msg": ">> CONTROLS INVERTED <<"},
    {"name": "SIGNAL INTERFERENCE", "duration": 3.0, "effect": "static_overlay",
     "color": YELLOW, "msg": ">> VISUAL NOISE <<"},
    {"name": "FIREWALL BREACH",     "duration": 5.0, "effect": "fast_drain",
     "color": RED, "msg": ">> TIMER DRAIN 2x <<"},
    {"name": "SYSTEM OVERLOAD",     "duration": 3.0, "effect": "screen_dim",
     "color": YELLOW, "msg": ">> LOW POWER <<"},
    {"name": "CODE SCRAMBLE",       "duration": 1.5, "effect": "code_scramble",
     "color": RED, "msg": ">> TARGET CODE CHANGED <<"},
]

# --- COMMS CHATTER -----------------------------------------------------------
COMMS_GENERIC = [
    "HQ: Satellite link holding. Keep moving, Agent.",
    "HQ: We're tracking your signal. Stay focused.",
    "HQ: Remember your training, Cipher.",
    "HQ: Clock is ticking. No room for error.",
    "HQ: Enemy comms are active. They know we're in.",
    "HQ: Stay sharp. We've seen movement on their end.",
    "HQ: The Director is watching. Don't let us down.",
    "HQ: Keep your head down and finish the job.",
]
COMMS_TIME_LOW = [
    "HQ: You're running out of time!",
    "HQ: HURRY. Window is closing!",
    "HQ: We can't hold the uplink much longer!",
    "HQ: Move it, Agent! Clock is almost out!",
]
COMMS_SUCCESS = [
    "HQ: Protocol complete. Solid work, Agent.",
    "HQ: Good. Moving to next phase.",
    "HQ: File section decrypted. Keep going.",
    "HQ: Acknowledged. One step closer.",
]

# --- SCREEN HACK VISUALS ----------------------------------------------------
SKULL_ART = [
    "   xxxxxxx   ",
    "  x       x  ",
    " x  x   x  x ",
    " x         x ",
    " x   xxx   x ",
    "  x x   x x  ",
    "   xxxxxxx   ",
    "    x x x    ",
]

# --- GAME DATA (randomized each mission) -------------------------------------
INTEL_POOL = {
    "target": ["Grand Central", "Pentagon West", "Hoover Dam", "Wall Street",
               "LAX Terminal 4", "Capitol Hill", "Times Square", "Golden Gate"],
    "code": ["OMEGA-7", "DELTA-3", "SIGMA-9", "ALPHA-1", "ZULU-5", "ECHO-4"],
    "location": ["New York City", "Washington DC", "Los Angeles", "San Francisco",
                 "Chicago", "Houston", "Seattle", "Miami"],
    "date": ["03-27", "04-15", "05-02", "06-19", "07-04", "08-11", "09-30", "11-22"],
    "time": ["14:30", "06:00", "09:45", "12:00", "17:15", "21:30", "03:00", "08:30"],
    "operatives": ["VIPER", "JACKAL", "CONDOR", "SCORPION", "MANTIS", "FALCON"],
    "method": ["EMP device", "Chemical agent", "Cyber attack", "Dirty bomb",
               "Sabotage", "Signal jamming"],
    "funding": ["2.4M", "5.1M", "800K", "12M", "3.7M", "950K"],
    "source": ["PHANTOM LLC", "NEXUS GROUP", "IRON GATE LTD", "BLACK MESA INC",
               "CIPHER CORP", "SHADOW FUND"],
    "contact": ["RAVEN", "GHOST", "SPECTER", "ORACLE", "NOMAD", "BISHOP"],
}

def generate_intel():
    return {k: random.choice(v) for k, v in INTEL_POOL.items()}

# Default (will be re-rolled each mission)
INTEL = generate_intel()

FILE_HEADER = [
    "+----------------------------------------------------------+",
    "|  CLASSIFIED - OPERATION BLACKOUT - EYES ONLY            |",
    "|----------------------------------------------------------|",
]
FILE_FOOTER_SEP = "|----------------------------------------------------------|"
FILE_BOTTOM     = "+----------------------------------------------------------+"

FILE_REDACTED = [
    "|  TARGET: ##############  CODE: ########                 |",
    "|  LOCATION: ############################                 |",
    "|  DATE: ########  TIME: ########                        |",
    "|  OPERATIVES: ########                                   |",
    "|  METHOD: ##########################                     |",
    "|  FUNDING: $##########  SOURCE: ############            |",
    "|  CONTACTS: ################################             |",
]

def build_revealed(intel):
    return [
        f"|  TARGET: {intel['target']:<14s}  CODE: {intel['code']:<8s}                 |",
        f"|  LOCATION: {intel['location']:<28s}                 |",
        f"|  DATE: {intel['date']:<10s}TIME: {intel['time']:<8s}                        |",
        f"|  OPERATIVES: {intel['operatives']:<30s}              |",
        f"|  METHOD: {intel['method']:<26s}                     |",
        f"|  FUNDING: ${intel['funding']:<11s} SOURCE: {intel['source']:<12s}            |",
        f"|  CONTACTS: {intel['contact']:<32s}             |",
    ]

FILE_REVEALED = build_revealed(INTEL)
STAGE_LINES = [[0, 1], [2, 3, 4], [5, 6]]

DEBRIEF_QUESTIONS = [
    ("TARGET",     "target"),
    ("LOCATION",   "location"),
    ("CODE",       "code"),
    ("DATE",       "date"),
    ("TIME",       "time"),
    ("OPERATIVE",  "operatives"),
    ("METHOD",     "method"),
    ("CONTACT",    "contact"),
]
# Which mission stage unlocks each question (matches STAGE_LINES grouping):
QUESTION_STAGE = {
    "target": 0, "code": 0, "location": 0,
    "date": 1, "time": 1, "operatives": 1, "method": 1,
    "contact": 2,
}

# Vertical-list view of the redacted file — used by the briefing AND the intel
# phase so both screens look identical. (label, intel-key, unlock-stage)
INTEL_FIELDS = [
    ("TARGET",    "target",     0),
    ("LOCATION",  "location",   0),
    ("CODE",      "code",       0),
    ("DATE",      "date",       1),
    ("TIME",      "time",       1),
    ("OPERATIVE", "operatives", 1),
    ("METHOD",    "method",     1),
    ("FUNDING",   "funding",    2),
    ("SOURCE",    "source",     2),
    ("CONTACT",   "contact",    2),
]

MATRIX_CHARS = "01234567890ABCDEF!@#$%&*<>{}[]=/\\|~^;:.,?+-_abcdef"

# --- CRT EFFECTS -------------------------------------------------------------
def create_scanlines():
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 4):
        pygame.draw.line(s, (0, 0, 0, 15), (0, y), (WIDTH, y))
    return s

def create_vignette():
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_dist = math.sqrt(cx*cx + cy*cy)
    for r in range(int(max_dist), 0, -4):
        alpha = int(40 * (r / max_dist) ** 3)
        alpha = min(alpha, 40)
        pygame.draw.circle(s, (0, 0, 0, alpha), (cx, cy), r)
    return s

SCANLINES = create_scanlines()
VIGNETTE = create_vignette()

def apply_crt(surface):
    surface.blit(SCANLINES, (0, 0))
    surface.blit(VIGNETTE, (0, 0))


# --- MATRIX RAIN -------------------------------------------------------------
class MatrixRain:
    def __init__(self, speed_mult=1.0):
        self.col_w = 18
        self.num_cols = WIDTH // self.col_w + 1
        self.drops = []
        for c in range(self.num_cols):
            self.drops.append({
                "y": random.uniform(-HEIGHT, 0),
                "speed": random.uniform(150, 400) * speed_mult,
                "chars": [random.choice(MATRIX_CHARS) for _ in range(25)],
                "trail_len": random.randint(8, 20),
            })

    def update(self, dt):
        for d in self.drops:
            d["y"] += d["speed"] * dt
            if d["y"] > HEIGHT + d["trail_len"] * 18:
                d["y"] = random.uniform(-200, -50)
                d["speed"] = random.uniform(150, 400)
                d["trail_len"] = random.randint(8, 20)
            # Mutate random chars
            if random.random() < 0.05:
                idx = random.randint(0, len(d["chars"]) - 1)
                d["chars"][idx] = random.choice(MATRIX_CHARS)

    def draw(self, surface, color_override=None):
        for i, d in enumerate(self.drops):
            x = i * self.col_w
            head_y = int(d["y"])
            for j in range(d["trail_len"]):
                cy = head_y - j * 18
                if cy < -18 or cy > HEIGHT:
                    continue
                if color_override:
                    # Red rain or other color hack
                    fade = max(0.2, 1.0 - j / d["trail_len"])
                    color = (int(color_override[0] * fade),
                             int(color_override[1] * fade),
                             int(color_override[2] * fade))
                elif j == 0:
                    color = WHITE
                elif j < 3:
                    color = GREEN_BRIGHT
                else:
                    fade = max(0, 1.0 - j / d["trail_len"])
                    color = (0, int(200 * fade), 0)
                ch = d["chars"][j % len(d["chars"])]
                try:
                    ts = FONT_SM.render(ch, True, color)
                    surface.blit(ts, (x, cy))
                except:
                    pass


# --- UTILITY DRAWING ---------------------------------------------------------

def draw_text(surface, text, x, y, font=FONT_SM, color=GREEN):
    ts = font.render(text, True, color)
    surface.blit(ts, (x, y))
    return ts.get_width(), ts.get_height()

def draw_text_centered(surface, text, y, font=FONT_SM, color=GREEN):
    ts = font.render(text, True, color)
    surface.blit(ts, ((WIDTH - ts.get_width()) // 2, y))

def draw_timer_bar(surface, remaining, total, y=HEIGHT - 140):
    """Big numeric countdown in the top-right of the screen.
    Color shifts green → yellow under 10s → red under 5s (blinking).
    The y / total args are kept so existing callers don't break."""
    secs = max(0, int(remaining + 0.5))
    if remaining > 10:
        color = GREEN_BRIGHT
    elif remaining > 5:
        color = YELLOW
    else:
        color = RED_BRIGHT if int(time.time() * 4) % 2 else RED

    label_surf = FONT_SM.render("TIME LEFT", True, GREEN_DIM)
    timer_surf = FONT_HUGE.render(f"{secs:02d}", True, color)

    pad = 14
    box_w = max(label_surf.get_width(), timer_surf.get_width()) + pad * 2
    box_h = label_surf.get_height() + timer_surf.get_height() + pad
    box_x = WIDTH - box_w - 16
    box_y = 14

    bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 200))
    pygame.draw.rect(bg, color, (0, 0, box_w, box_h), 2)
    surface.blit(bg, (box_x, box_y))

    surface.blit(label_surf, (box_x + (box_w - label_surf.get_width()) // 2, box_y + 6))
    surface.blit(timer_surf, (box_x + (box_w - timer_surf.get_width()) // 2,
                              box_y + label_surf.get_height() + 4))

def draw_vertical_file(surface, x, y, stages_completed, font=FONT_LG,
                       active_key=None, intel=None):
    """Render the redacted file as a vertical list — one field per row.
    Each row reveals its value (cyan) when its stage is completed,
    otherwise shows a redacted bar.

    Used by the briefing AND the intel phase so they match.
    Returns the y of the row immediately below the list."""
    intel = intel if intel is not None else INTEL
    label_w = max(font.size(lbl)[0] for lbl, _k, _s in INTEL_FIELDS)
    bar_w = 480
    row_h = font.get_linesize() + 8
    total_w = label_w + 40 + bar_w

    for i, (lbl, key, stage_idx) in enumerate(INTEL_FIELDS):
        ry = y + i * row_h
        unlocked = stage_idx in stages_completed
        is_active = (active_key is not None and key == active_key)

        # Active row gets a pulsing yellow border
        if is_active:
            pulse = int(abs(math.sin(time.time() * 3)) * 60) + 160
            pygame.draw.rect(surface, (pulse, pulse, 0),
                             (x - 8, ry - 4, total_w + 16, row_h + 2), 2)

        # Label
        label_color = WHITE if is_active else GREEN_DIM
        label_surf = font.render(lbl, True, label_color)
        surface.blit(label_surf, (x, ry))
        # Colon
        colon_surf = font.render(":", True, GREEN_DIM)
        surface.blit(colon_surf, (x + label_w + 8, ry))
        # Value or redacted block
        bar_x = x + label_w + 40
        bar_h = font.get_height() - 4
        if unlocked:
            value = intel[key].upper()
            val_surf = font.render(value, True, CYAN)
            surface.blit(val_surf, (bar_x, ry))
        else:
            pygame.draw.rect(surface, (0, 40, 0), (bar_x, ry + 2, bar_w, bar_h))
            block = font.render("█" * 14, True, GREEN_DIM)
            surface.blit(block, (bar_x + 6, ry))

    return y + len(INTEL_FIELDS) * row_h

def draw_file_status(surface, x, y, stages_completed, font=FONT_SM):
    """stages_completed: set of completed stage indices, e.g. {0, 2}"""
    revealed = set()
    for s in stages_completed:
        for idx in STAGE_LINES[s]:
            revealed.add(idx)
    row_y = y
    lh = font.get_linesize() + 2
    for line in FILE_HEADER:
        draw_text(surface, line, x, row_y, font, GREEN)
        row_y += lh
    for i in range(len(FILE_REDACTED)):
        if i in revealed:
            draw_text(surface, FILE_REVEALED[i], x, row_y, font, CYAN)
        else:
            draw_text(surface, FILE_REDACTED[i], x, row_y, font, GREEN_DIM)
        row_y += lh
    draw_text(surface, FILE_FOOTER_SEP, x, row_y, font, GREEN)
    row_y += lh
    pct = int(len(stages_completed) / 3 * 100)
    status = f"|  STATUS: REDACTION {'COMPLETE' if pct == 100 else 'IN PROGRESS'} [{pct}%]"
    padlen = len(FILE_HEADER[0]) - len(status) - 1
    status += " " * max(0, padlen) + "|"
    draw_text(surface, status, x, row_y, font, CYAN if pct == 100 else GREEN)
    row_y += lh
    draw_text(surface, FILE_BOTTOM, x, row_y, font, GREEN)
    row_y += lh
    return row_y

def draw_sidebar(surface, remaining, total, stages_completed,
                 active_stage=None, intel=None):
    """Left-hand panel: timer on top + compact redaction file below.
    `active_stage` (0/1/2) highlights the field group the player is currently
    unredacting. Drawn so the timer is never obscured by the minigame."""
    intel = intel if intel is not None else INTEL
    x, y, w, h = SIDEBAR_X, 12, SIDEBAR_W, HEIGHT - 24

    # Outer panel
    pygame.draw.rect(surface, BLACK, (x, y, w, h))
    pygame.draw.rect(surface, GREEN, (x, y, w, h), 2)

    inner_x = x + SIDEBAR_INNER_PAD
    inner_w = w - SIDEBAR_INNER_PAD * 2

    # --- Timer block ---------------------------------------------------------
    secs = max(0, int(remaining + 0.5))
    if remaining > 30:
        t_color = GREEN_BRIGHT
    elif remaining > 10:
        t_color = YELLOW
    else:
        t_color = RED_BRIGHT if int(time.time() * 4) % 2 else RED

    label = FONT_SM.render("TIME LEFT", True, GREEN_DIM)
    timer = FONT_HUGE.render(f"{secs:02d}", True, t_color)
    block_pad = 10
    block_h = label.get_height() + timer.get_height() + block_pad * 2 + 14
    block_y = y + 12
    pygame.draw.rect(surface, t_color, (inner_x, block_y, inner_w, block_h), 2)
    surface.blit(label, (inner_x + (inner_w - label.get_width()) // 2,
                          block_y + block_pad))
    surface.blit(timer, (inner_x + (inner_w - timer.get_width()) // 2,
                          block_y + block_pad + label.get_height() + 2))

    # Thin progress bar at the bottom of the timer block
    bar_y = block_y + block_h - 8
    bar_w = inner_w - 8
    bar_x = inner_x + 4
    pygame.draw.rect(surface, (10, 30, 10), (bar_x, bar_y, bar_w, 4))
    if total > 0:
        fill = int(bar_w * max(0.0, min(1.0, remaining / total)))
        pygame.draw.rect(surface, t_color, (bar_x, bar_y, fill, 4))

    # --- File header ---------------------------------------------------------
    fy = block_y + block_h + 18
    head = FONT_SM.render("REDACTION FILE", True, CYAN)
    surface.blit(head, (inner_x + (inner_w - head.get_width()) // 2, fy))
    fy += head.get_height() + 4
    pct = int(len(stages_completed) / 3 * 100)
    pct_color = CYAN_BRIGHT if pct == 100 else GREEN_DIM
    pct_surf = FONT_SM.render(f"{pct}% UNREDACTED", True, pct_color)
    surface.blit(pct_surf, (inner_x + (inner_w - pct_surf.get_width()) // 2, fy))
    fy += pct_surf.get_height() + 12

    # --- Vertical file (compact) --------------------------------------------
    font = FONT_SM
    label_w = max(font.size(lbl)[0] for lbl, _k, _s in INTEL_FIELDS)
    val_x = inner_x + label_w + 10
    val_w = inner_x + inner_w - val_x
    row_h = font.get_linesize() + 4

    for lbl, key, stage_idx in INTEL_FIELDS:
        unlocked = stage_idx in stages_completed
        is_active = (stage_idx == active_stage) and not unlocked

        if is_active:
            pulse = int(abs(math.sin(time.time() * 3)) * 60) + 160
            pygame.draw.rect(surface, (pulse, pulse, 0),
                             (inner_x - 2, fy - 2, inner_w + 4, row_h + 2), 1)

        if unlocked:
            lbl_color = GREEN
        elif is_active:
            lbl_color = WHITE
        else:
            lbl_color = GREEN_DIM
        surface.blit(font.render(lbl, True, lbl_color), (inner_x, fy))

        if unlocked:
            value = intel[key].upper()
            while font.size(value)[0] > val_w and len(value) > 3:
                value = value[:-1]
            surface.blit(font.render(value, True, CYAN), (val_x, fy))
        else:
            block_h2 = font.get_height() - 4
            pygame.draw.rect(surface, (0, 40, 0),
                             (val_x, fy + 2, val_w, block_h2))
            num_blocks = max(2, val_w // 9)
            blocks = font.render("█" * num_blocks, True,
                                 GREEN if is_active else GREEN_DIM)
            # clip wider-than-cell blocks via subsurface trick (just blit)
            surface.blit(blocks, (val_x + 2, fy))
        fy += row_h


def draw_urgency_overlay(surface, remaining):
    """Subtle screen-wide urgency tint:
    ≤30s — soft yellow vignette
    ≤10s — gentle red flicker
    Kept low-alpha so it conveys urgency without getting in the way."""
    if remaining > 30:
        return
    if remaining > 10:
        # Yellow vignette: stronger at edges, faint in the middle.
        pulse = int((math.sin(time.time() * 2.2) + 1) * 8) + 12  # 12..28
        cache_key = ("urgency_yellow", pulse)
    else:
        # Red flicker: gentle pulsing alpha, never spikes too high.
        bright = (math.sin(time.time() * 6.0) + 1) * 0.5  # 0..1
        a = int(20 + bright * 28)  # 20..48
        cache_key = ("urgency_red", a)

    cache = draw_urgency_overlay._cache
    overlay = cache.get(cache_key)
    if overlay is None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy = WIDTH // 2, HEIGHT // 2
        max_d = math.hypot(cx, cy)
        if cache_key[0] == "urgency_yellow":
            base = (240, 200, 0)
            alpha_max = cache_key[1]
            for r in range(int(max_d), 0, -8):
                t = r / max_d
                a = int(alpha_max * (t ** 2))
                pygame.draw.circle(overlay, (*base, a), (cx, cy), r)
        else:
            overlay.fill((220, 20, 20, cache_key[1]))
        cache[cache_key] = overlay
        if len(cache) > 64:
            cache.clear()
            cache[cache_key] = overlay
    surface.blit(overlay, (0, 0))

draw_urgency_overlay._cache = {}


# --- MAZE GENERATION ---------------------------------------------------------

def generate_maze(mw, mh):
    visited = [[False]*mw for _ in range(mh)]
    walls = {}
    for r in range(mh):
        for c in range(mw):
            walls[(r,c)] = [True,True,True,True]
    stack = [(0,0)]
    visited[0][0] = True
    while stack:
        r,c = stack[-1]
        nbrs = []
        for dr,dc,ws,wn in [(-1,0,0,2),(0,1,1,3),(1,0,2,0),(0,-1,3,1)]:
            nr,nc = r+dr, c+dc
            if 0<=nr<mh and 0<=nc<mw and not visited[nr][nc]:
                nbrs.append((nr,nc,ws,wn))
        if nbrs:
            nr,nc,ws,wn = random.choice(nbrs)
            walls[(r,c)][ws] = False
            walls[(nr,nc)][wn] = False
            visited[nr][nc] = True
            stack.append((nr,nc))
        else:
            stack.pop()
    gh = mh*2+1
    gw = mw*2+1
    grid = [[1]*gw for _ in range(gh)]
    for r in range(mh):
        for c in range(mw):
            grid[r*2+1][c*2+1] = 0
            if not walls[(r,c)][0]: grid[r*2][c*2+1] = 0
            if not walls[(r,c)][1]: grid[r*2+1][c*2+2] = 0
            if not walls[(r,c)][2]: grid[(r+1)*2][c*2+1] = 0
            if not walls[(r,c)][3]: grid[r*2+1][c*2] = 0
    # Remove extra walls to create loops and branching paths
    extra = int(mw * mh * 0.55)
    for _ in range(extra):
        r = random.randint(1, gh - 2)
        c = random.randint(1, gw - 2)
        if grid[r][c] == 1:
            # Only remove if it connects two open cells (not on the border)
            open_neighbors = 0
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < gh and 0 <= nc < gw and grid[nr][nc] == 0:
                    open_neighbors += 1
            if open_neighbors >= 2:
                grid[r][c] = 0
    return grid


# --- SEGMENT INTERSECTION ----------------------------------------------------

def segments_intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False
    def on_seg(a, b, p):
        cross = (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])
        if cross != 0: return False
        return (min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and
                min(a[1],b[1])<=p[1]<=max(a[1],b[1]))
    if on_seg(p3, p4, p2):
        return True
    def ccw(A,B,C):
        return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])
    return (ccw(p1,p3,p4)!=ccw(p2,p3,p4)) and (ccw(p1,p2,p3)!=ccw(p1,p2,p4))


# --- GAME MANAGER ------------------------------------------------------------

# Keys polled each frame to synthesize KEYDOWN events. In pygbag (pygame-web)
# KEYDOWN events for arrow/menu keys can be swallowed by the browser before
# reaching pygame's event queue, so we rising-edge-detect them via
# pygame.key.get_pressed() and inject the missing events ourselves.
_MENU_POLL_KEYS = (
    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
    pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE,
    pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
    pygame.K_q, pygame.K_1, pygame.K_2, pygame.K_3,
    pygame.K_PAGEUP, pygame.K_PAGEDOWN,
)


class Game:
    def __init__(self):
        self.diff = DIFFICULTIES["AGENT"]
        self.stages_done = set()
        self.game_deadline = 0    # absolute time when current game expires
        self.game_total = 0       # total seconds for current game (for timer bar)
        self.state = "title"
        self.rain = MatrixRain()
        self.rain_timer = 0
        self.typewriter_lines = []
        self.tw_char_idx = 0
        self.tw_line_idx = 0
        self.tw_timer = 0
        self.tw_done = False
        self.flash_timer = 0
        self.flash_color = None

        # Edge-detection cache for synthetic KEYDOWN events (pygbag workaround).
        self._prev_keys = {}

        # Menu
        self.menu_cursor = 0
        self.selected_diff = load_save().get("last_difficulty", "AGENT")
        self.howto_scroll = 0
        self.howto_return_to = "menu"

        # Pause
        self.paused = False
        self.pause_cursor = 0
        self.pre_pause_state = ""
        self.pause_elapsed = 0  # time spent in pause (to add back)

        # Roulette
        self.rl_target = []
        self.rl_current = []
        self.rl_locked = []
        self.rl_lock_idx = 0
        self.rl_speeds = []
        self.rl_timers = []

        # Maze
        self.maze_grid = []
        self.maze_player = [0, 0]
        self.maze_key_pos = [0, 0]
        self.maze_exit_pos = [0, 0]
        self.maze_exit_open = False
        self.maze_has_key = False
        self.maze_gh = 0
        self.maze_gw = 0
        self.maze_cell_size = 0

        # Connect
        self.cn_nodes = []
        self.cn_player = [0, 0]
        self.cn_target = 1
        self.cn_connected = []
        self.cn_current_trail = []
        self.cn_locked_trails = []
        self.cn_warning = ""
        self.cn_warning_timer = 0

        # Intel
        self.intel_cursor = 0
        self.intel_answers = []
        self.intel_attempts = []
        self.intel_choices = []       # multiple choice options per question
        self.intel_choice_cursor = 0  # which option is highlighted
        self.intel_correct = 0

        # Debrief
        self.debrief_rank = ""

        # Transition
        self.trans_timer = 0
        self.trans_next = ""
        self.trans_label = ""
        self.trans_ready = False       # True = instructions shown, waiting for ENTER
        self.trans_pause_start = 0     # timestamp when we froze the timer

        # Result screen (between minigame end and transition)
        self.result_timer = 0          # lockout countdown
        self.result_success = False    # win or fail
        self.result_text = ""          # headline text
        self.result_next = ""          # next state for transition
        self.result_label = ""         # label for transition
        self.result_ready = False      # True = lockout expired, waiting for SPACE
        self.result_bg = None          # captured screen for dimmed overlay

        # Disruption events
        self.event_active = None       # current event dict or None
        self.event_timer = 0           # duration countdown
        self.event_cooldown = 5.0      # initial grace period
        self.event_warning = ""        # upcoming disruption name
        self.event_warning_timer = 0   # warning display countdown
        self._pending_event = None     # event dict waiting to fire after warning

        # Comms chatter
        self.comms_messages = []       # persistent dialogue log: [{text, color}]
        self.comms_text = ""
        self.comms_timer = 0           # display countdown (3s)
        self.comms_cooldown = 6.0      # time until first message
        self.comms_time_warned = False  # only warn about low time once per game

        # Screen hack events
        self.hack_type = ""            # "skull", "red_rain", "glitch"
        self.hack_timer = 0
        self.hack_cooldown = 10.0

        # Maze guards
        self.maze_guards = []
        self.maze_guard_alert = 0      # alert display timer

    def remaining_time(self):
        # When paused, freeze time at the moment we paused
        now = self.pause_elapsed if self.paused else time.time()
        # Also freeze during transition instruction screen
        if self.state == "transition" and self.trans_ready and self.trans_pause_start:
            now = self.trans_pause_start
        return max(0, self.game_deadline - now)

    # -- DISRUPTION EVENTS ------------------------------------------------
    def _update_events(self, dt):
        """Tick disruption event timers. Called for roulette/maze/connect only."""
        if self.paused:
            return
        # Active event countdown
        if self.event_active:
            self.event_timer -= dt
            # Fast drain effect: steal extra time
            if self.event_active["effect"] == "fast_drain":
                self.game_deadline -= dt  # double drain (normal + this)
            if self.event_timer <= 0:
                self.event_active = None
                self.event_timer = 0
            return  # don't trigger new event while one is active

        # Warning countdown — show warning BEFORE event fires
        if self.event_warning_timer > 0:
            self.event_warning_timer -= dt
            if self.event_warning_timer <= 0:
                # Warning expired — fire the event now
                ev = self._pending_event
                self.event_active = dict(ev)
                self.event_timer = ev["duration"]
                self.event_warning = ""
                self._pending_event = None
                if ev["effect"] == "code_scramble" and self.state == "roulette":
                    self._scramble_roulette_digit()
            return

        self.event_cooldown -= dt
        if self.event_cooldown <= 0:
            # Pick event and show warning first
            pool = DISRUPTION_EVENTS
            if self.state != "roulette":
                pool = [e for e in pool if e["effect"] != "code_scramble"]
            ev = random.choice(pool)
            self._pending_event = ev
            self.event_warning = ev["name"]
            self.event_warning_timer = 2.0
            self.event_cooldown = self.diff.get("event_cooldown", 20) * random.uniform(0.7, 1.3)

    def _draw_event_overlay(self):
        """Draw disruption event visuals."""
        if not self.event_active:
            return
        ev = self.event_active
        eff = ev["effect"]
        # Event name banner
        pulse = int(abs(math.sin(time.time() * 6)) * 55) + 200
        c = ev["color"]
        bc = (min(255, c[0] + pulse % 50), min(255, c[1]), min(255, c[2]))
        draw_text_centered(screen, ev["name"], 110, FONT_LG, bc)
        draw_text_centered(screen, ev["msg"], 145, FONT_SM, c)

        if eff == "static_overlay":
            noise = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(600):
                nx = random.randint(0, WIDTH - 1)
                ny = random.randint(0, HEIGHT - 1)
                noise.set_at((nx, ny), (200, 200, 200, random.randint(40, 100)))
            screen.blit(noise, (0, 0))
        elif eff == "screen_dim":
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 120))
            screen.blit(dim, (0, 0))
        elif eff == "fast_drain":
            # Red pulsing border
            alpha = int(abs(math.sin(time.time() * 8)) * 180)
            border = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(border, (255, 0, 0, alpha), (0, 0, WIDTH, HEIGHT), 6)
            screen.blit(border, (0, 0))
        elif eff == "invert_controls":
            draw_text(screen, "[!] UP<>DN  LEFT<>RIGHT", WIDTH - 280, HEIGHT - 25, FONT_SM, RED)

    def _is_controls_inverted(self):
        return (self.event_active is not None and
                self.event_active["effect"] == "invert_controls")

    # -- COMMS CHATTER ----------------------------------------------------
    def _add_comms_message(self, text, color=None):
        """Add a persistent message to the dialogue log."""
        self.comms_messages.append({"text": text, "color": color})

    def _update_comms(self, dt):
        """Tick comms cooldown and generate messages."""
        if self.paused:
            return

        # Context: low time warning (once per game)
        rem = self.remaining_time()
        if rem > 0 and rem < 15 and not self.comms_time_warned:
            self._add_comms_message(random.choice(COMMS_TIME_LOW), RED)
            self.comms_time_warned = True
            return

        # Random generic chatter
        self.comms_cooldown -= dt
        if self.comms_cooldown <= 0:
            if rem > 10:
                self._add_comms_message(random.choice(COMMS_GENERIC))
                self.comms_cooldown = random.uniform(8, 16)
            else:
                self._add_comms_message(random.choice(COMMS_TIME_LOW), YELLOW)
                self.comms_cooldown = random.uniform(4, 8)

    def _trigger_comms_success(self):
        """Show a success message when a protocol is completed."""
        self._add_comms_message(random.choice(COMMS_SUCCESS), CYAN)

    def _word_wrap(self, text, font, max_width):
        """Break text into lines that fit within max_width."""
        words = text.split(' ')
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_comms(self):
        """Draw bottom dialogue box with persistent scrolling messages."""
        # Box dimensions — full width, below timer bar
        box_x, box_w = 20, WIDTH - 40
        box_y = HEIGHT - 110
        box_h = 100
        pad = 6
        line_h = FONT_SM.get_linesize() + 2
        max_text_w = box_w - pad * 2

        rem = self.remaining_time()
        if rem <= 15:
            border_color = RED
        elif rem <= 30:
            border_color = YELLOW
        else:
            border_color = GREEN

        # Draw box background
        box_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box_surf.fill((0, 0, 0, 210))
        pygame.draw.rect(box_surf, border_color, (0, 0, box_w, box_h), 1)
        screen.blit(box_surf, (box_x, box_y))

        # Build all wrapped lines (oldest at top, newest at bottom)
        all_lines = []  # (text, color)

        # Comms messages (persistent log, chronological)
        for msg in self.comms_messages:
            c = msg["color"] if msg["color"] else GREEN
            wrapped = self._word_wrap(msg["text"], FONT_SM, max_text_w)
            for wl in wrapped:
                all_lines.append((wl, c))

        # Disruption warning/event at the very bottom (most recent)
        if self.event_warning and self.event_warning_timer > 0:
            pulse = int(abs(math.sin(time.time() * 6)) * 55) + 200
            warn_color = (min(255, pulse), min(255, pulse // 3), 0)
            all_lines.append((f"!! INCOMING: {self.event_warning} !!", warn_color))

        if self.event_active:
            all_lines.append((f">> {self.event_active['msg']} <<", self.event_active["color"]))

        display_lines = all_lines

        # Only show lines that fit in the box (scroll from bottom)
        max_visible = (box_h - pad * 2) // line_h
        visible = display_lines[-max_visible:] if len(display_lines) > max_visible else display_lines

        # Draw from bottom up
        ty = box_y + box_h - pad - line_h
        for text, color in reversed(visible):
            if text:
                draw_text(screen, text, box_x + pad, ty, FONT_SM, color)
            ty -= line_h

    # -- SCREEN HACK EVENTS -----------------------------------------------
    def _update_hack(self, dt):
        """Tick screen hack timers."""
        if self.paused:
            return
        if self.hack_timer > 0:
            self.hack_timer -= dt
            if self.hack_timer <= 0:
                self.hack_type = ""
            return

        self.hack_cooldown -= dt
        if self.hack_cooldown <= 0:
            self.hack_type = random.choice(["skull", "red_rain", "glitch"])
            if self.hack_type == "skull":
                self.hack_timer = 0.8
            elif self.hack_type == "red_rain":
                self.hack_timer = 2.0
            else:
                self.hack_timer = 1.5
            self.hack_cooldown = self.diff.get("hack_cooldown", 20) * random.uniform(0.7, 1.3)

    def _draw_hack_overlay(self):
        """Draw screen hack visual effects."""
        if self.hack_timer <= 0:
            return
        if self.hack_type == "skull":
            sy = HEIGHT // 2 - len(SKULL_ART) * 10
            for i, row in enumerate(SKULL_ART):
                draw_text_centered(screen, row, sy + i * 20, FONT_MD, RED)
            draw_text_centered(screen, ">> YOU'VE BEEN DETECTED <<", sy + len(SKULL_ART) * 20 + 10, FONT_MD, RED)
        elif self.hack_type == "glitch":
            # Slice-and-shift: copy horizontal strips and offset them
            temp = screen.copy()
            for _ in range(8):
                sy = random.randint(0, HEIGHT - 40)
                sh = random.randint(10, 40)
                offset = random.randint(-30, 30)
                strip = temp.subsurface((0, sy, WIDTH, sh)).copy()
                screen.blit(strip, (offset, sy))
        elif self.hack_type == "red_rain":
            # Draw red matrix rain overlay
            self.rain.update(dt=0.016)  # approximate 1 frame
            rain_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            self.rain.draw(rain_surf, color_override=RED)
            rain_surf.set_alpha(100)
            screen.blit(rain_surf, (0, 0))
            # Red text warning
            draw_text_centered(screen, ">> SYSTEM COMPROMISED <<", HEIGHT // 2, FONT_LG, RED)

    def _inject_synth_keys(self, events):
        """Rising-edge-detect polled key state and append synthetic KEYDOWN
        events for any watched key that pygame didn't already emit. Menus rely
        on KEYDOWN; pygbag sometimes drops those while keeping polled state
        intact, which is why in-game controls (get_pressed) work while menus
        don't."""
        kp = pygame.key.get_pressed()
        real_down = {e.key for e in events if e.type == pygame.KEYDOWN}
        cur = {}
        mods = pygame.key.get_mods()
        for k in _MENU_POLL_KEYS:
            down = bool(kp[k])
            cur[k] = down
            if down and not self._prev_keys.get(k, False) and k not in real_down:
                events.append(pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": k, "mod": mods, "unicode": "", "scancode": 0},
                ))
        self._prev_keys = cur
        return events

    async def run(self):
        running = True
        while running:
            dt = clock.tick(FPS) / 1000.0
            await asyncio.sleep(0)
            events = pygame.event.get()
            events = self._inject_synth_keys(events)
            for e in events:
                if e.type == pygame.QUIT:
                    running = False
                    break

            if not running:
                break

            screen.fill(BLACK)

            # Debug controls: 1=skip, 2=+60s, 3=jump to intel
            if DEBUG:
                for e in events:
                    if e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_1:
                            # Skip current minigame
                            if self.state == "roulette":
                                self.stages_done.add(0)
                                self._start_transition("maze", "MAZE EXTRACTION")
                            elif self.state == "maze":
                                self.stages_done.add(1)
                                self._start_transition("connect", "NODE LINK")
                            elif self.state == "connect":
                                self.stages_done.add(2)
                                self._start_transition("intel", "INTEL REPORT")
                            elif self.state == "briefing":
                                self.stages_done = set()
                                self._start_transition("roulette", "ACCESS CODE ROULETTE")
                        elif e.key == pygame.K_2:
                            # Add 60 seconds
                            self.game_deadline += 60
                        elif e.key == pygame.K_3:
                            # Jump straight to intel (all stages done)
                            self.stages_done = {0, 1, 2}
                            self._start_transition("intel", "INTEL REPORT")

                # Show debug indicator
                draw_text(screen, "[DEBUG] 1=skip  2=+60s  3=intel", 10, HEIGHT - 18, FONT_SM, YELLOW)

            # Pause handler - ESC during gameplay
            gameplay_states = ("roulette", "maze", "connect", "intel", "transition")
            if not self.paused:
                for e in events:
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.state in gameplay_states:
                        self.paused = True
                        self.pause_cursor = 0
                        self.pre_pause_state = self.state
                        self.pause_elapsed = time.time()
                        events = []  # consume events
                        break

            if self.paused:
                self._update_pause(events, dt)
                self._draw_pause()
            elif self.state == "title":
                self._update_title(events, dt)
                self._draw_title()
            elif self.state == "menu":
                self._update_menu(events, dt)
                self._draw_menu()
            elif self.state == "howto":
                self._update_howto(events, dt)
                self._draw_howto()
            elif self.state == "briefing":
                self._update_briefing(events, dt)
                self._draw_briefing()
            elif self.state == "result":
                self._update_result(events, dt)
                self._draw_result()
            elif self.state == "transition":
                self._update_transition(events, dt)
                self._draw_transition()
            elif self.state == "roulette":
                self._update_roulette(events, dt)
                self._draw_roulette()
            elif self.state == "maze":
                self._update_maze(events, dt)
                self._draw_maze()
            elif self.state == "connect":
                self._update_connect(events, dt)
                self._draw_connect()
            elif self.state == "intel":
                self._update_intel(events, dt)
                self._draw_intel()
            elif self.state == "debrief":
                self._update_debrief(events, dt)
                self._draw_debrief()

            # Disruption events / comms / hacks disabled — playtesters found
            # the visual noise distracting. The functions remain but are no-ops.

            # Per-protocol urgency overlay: yellow ≤30s, red flicker ≤10s.
            # Subtle by design — meant to convey pressure, not block visibility.
            if self.state in ("roulette", "maze", "connect", "intel"):
                draw_urgency_overlay(screen, self.remaining_time())

            # Flash overlay
            if self.flash_timer > 0:
                self.flash_timer -= dt
                alpha = max(0, min(180, int(180 * (self.flash_timer / 0.3))))
                if alpha > 0:
                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    c = self.flash_color if self.flash_color else RED
                    overlay.fill((c[0], c[1], c[2], alpha))
                    screen.blit(overlay, (0, 0))

            apply_crt(screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # -- TITLE ------------------------------------------------------------
    def _update_title(self, events, dt):
        self.rain.update(dt)
        self.rain_timer += dt
        if self.rain_timer > 3.0:
            for e in events:
                if e.type == pygame.KEYDOWN:
                    self.state = "menu"
                    return
        if self.rain_timer > 6.0:
            self.state = "menu"

    def _draw_title(self):
        if self.rain_timer < 3.0:
            self.rain.draw(screen)
            return
        # Title art using pixel blocks
        draw_pixel_text_centered(screen, "DATA", 120, 8, GREEN_BRIGHT, DARK_GREEN)
        draw_pixel_text_centered(screen, "BREACH", 190, 8, GREEN_BRIGHT, DARK_GREEN)

        y = 260
        draw_text_centered(screen, "[ CLASSIFIED TERMINAL v2.049 ]", y + 30, FONT_MD, GREEN_DIM)

        # Blink "press any key"
        if int(self.rain_timer * 2) % 2 == 0:
            draw_text_centered(screen, ">>> PRESS ANY KEY TO CONNECT <<<", y + 80, FONT_LG, GREEN)

        # Highlight: keyboard-only — pulsing yellow border
        kbd_y = y + 160
        msg = "KEYBOARD ONLY  ·  NO MOUSE"
        sub = "Arrow keys · Enter · Space · Esc"
        msg_surf = FONT_LG.render(msg, True, YELLOW)
        sub_surf = FONT_MD.render(sub, True, GREEN_DIM)
        pad_x, pad_y = 30, 16
        box_w = max(msg_surf.get_width(), sub_surf.get_width()) + pad_x * 2
        box_h = msg_surf.get_height() + sub_surf.get_height() + pad_y * 2 + 8
        box_x = (WIDTH - box_w) // 2
        pulse = int(abs(math.sin(self.rain_timer * 3)) * 60) + 180
        border = (pulse, pulse, 0)
        pygame.draw.rect(screen, border, (box_x, kbd_y, box_w, box_h), 2)
        screen.blit(msg_surf, (box_x + (box_w - msg_surf.get_width()) // 2, kbd_y + pad_y))
        screen.blit(sub_surf, (box_x + (box_w - sub_surf.get_width()) // 2,
                               kbd_y + pad_y + msg_surf.get_height() + 6))

    # -- MENU -------------------------------------------------------------
    def _has_saved_progress(self):
        sd = load_save()
        return sd.get("in_progress") is not None

    def _get_menu_items(self):
        items = []
        if self._has_saved_progress():
            items.append(("CONTINUE", None))
        items.append(("NEW MISSION", None))
        items.append((f"DIFFICULTY: [ {self.selected_diff} ]", None))
        items.append(("HOW TO PLAY", None))
        items.append(("QUIT", None))
        return items

    def _update_menu(self, events, dt):
        self.rain.update(dt)
        menu_items = self._get_menu_items()
        num_items = len(menu_items)
        has_continue = self._has_saved_progress()

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP:
                    self.menu_cursor = (self.menu_cursor - 1) % num_items
                elif e.key == pygame.K_DOWN:
                    self.menu_cursor = (self.menu_cursor + 1) % num_items
                elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    idx = DIFFICULTY_ORDER.index(self.selected_diff)
                    idx = (idx + (1 if e.key == pygame.K_RIGHT else -1)) % len(DIFFICULTY_ORDER)
                    self.selected_diff = DIFFICULTY_ORDER[idx]
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    label = menu_items[self.menu_cursor][0]
                    if label == "CONTINUE":
                        if self._load_progress():
                            return
                    elif label == "NEW MISSION":
                        # Clear any saved progress when starting new
                        sd = load_save()
                        sd.pop("in_progress", None)
                        sd["last_difficulty"] = self.selected_diff
                        save_game(sd)
                        self.diff = DIFFICULTIES[self.selected_diff]
                        self._start_briefing()
                    elif label.startswith("DIFFICULTY"):
                        idx = DIFFICULTY_ORDER.index(self.selected_diff)
                        idx = (idx + 1) % len(DIFFICULTY_ORDER)
                        self.selected_diff = DIFFICULTY_ORDER[idx]
                    elif label == "HOW TO PLAY":
                        self.howto_return_to = "menu"
                        self.howto_scroll = 0
                        self.state = "howto"
                    elif label == "QUIT":
                        pygame.quit()
                        sys.exit()
                elif e.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

    def _draw_menu(self):
        # Dim rain background
        rain_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.rain.draw(rain_surf)
        rain_surf.set_alpha(40)
        screen.blit(rain_surf, (0, 0))

        pygame.draw.rect(screen, GREEN, (10, 10, WIDTH-20, HEIGHT-20), 1)

        # Title
        draw_pixel_text_centered(screen, "DATA", 24, 6, GREEN, DARK_GREEN)
        draw_pixel_text_centered(screen, "BREACH", 70, 6, GREEN, DARK_GREEN)
        y = 140

        # Saved progress (compact)
        sd_prog = load_save().get("in_progress")
        if sd_prog:
            rem = int(sd_prog.get("remaining", 0))
            stages = sd_prog.get("stages_done", set())
            stages_n = len(stages) if isinstance(stages, (set, list)) else stages
            draw_text_centered(screen,
                f"SAVED MISSION  ·  {sd_prog.get('difficulty', '?')}  ·  {stages_n}/3  ·  {rem}s left",
                y, FONT_MD, CYAN_BRIGHT)
            y += 36
        else:
            y += 10

        # Menu items
        menu_items = self._get_menu_items()
        for i, (label, _subtitle) in enumerate(menu_items):
            if i == self.menu_cursor:
                tw = FONT_LG.size(f"  >>  {label}  ")[0]
                bx = (WIDTH - tw) // 2 - 5
                pygame.draw.rect(screen, GREEN_DIM, (bx, y - 4, tw + 10, FONT_LG.get_linesize() + 6))
                draw_text_centered(screen, f"  >>  {label}  ", y, FONT_LG, GREEN_BRIGHT)
            else:
                color = CYAN if label == "CONTINUE" else GREEN
                draw_text_centered(screen, f"     {label}  ", y, FONT_LG, color)
            y += FONT_LG.get_linesize() + 4

        # Difficulty comparison panel — always visible so players can compare
        # the four levels at a glance. Highlight the selected one.
        y += 16
        panel_w = WIDTH - 80
        panel_x = 40
        panel_y = y
        col_w = panel_w // 5  # name col + 4 difficulty cols
        # header row
        draw_text(screen, "DIFFICULTY", panel_x + 14, panel_y, FONT_MD, GREEN_DIM)
        for ci, dk in enumerate(DIFFICULTY_ORDER):
            cx = panel_x + col_w * (ci + 1) + 8
            color = CYAN_BRIGHT if dk == self.selected_diff else GREEN_DIM
            draw_text(screen, dk, cx, panel_y, FONT_MD, color)
        py = panel_y + FONT_MD.get_linesize() + 6
        rows = [
            ("Total time", lambda d: f"{d['roulette_time']+d['maze_time']+d['connect_time']+d['intel_time']}s"),
            ("Code digits", lambda d: str(d["roulette_digits"])),
            ("Maze size",   lambda d: f"{d['maze_size'][0]}x{d['maze_size'][1]}"),
            ("Guards",      lambda d: str(d.get("maze_guards", 0))),
            ("Fog of war",  lambda d: "yes" if d.get("maze_fog", 0) > 0 else "no"),
            ("Nodes",       lambda d: str(d.get("num_nodes", 0))),
            ("Intel tries", lambda d: str(d.get("intel_attempts", 1))),
        ]
        for label, fn in rows:
            draw_text(screen, label, panel_x + 14, py, FONT_SM, GREEN)
            for ci, dk in enumerate(DIFFICULTY_ORDER):
                cx = panel_x + col_w * (ci + 1) + 8
                color = CYAN_BRIGHT if dk == self.selected_diff else GREEN_DIM
                draw_text(screen, fn(DIFFICULTIES[dk]), cx, py, FONT_SM, color)
            py += FONT_SM.get_linesize() + 2
        # frame around panel
        panel_h = py - panel_y + 6
        pygame.draw.rect(screen, GREEN_DIM, (panel_x, panel_y - 6, panel_w, panel_h), 1)

        # Bottom hint
        draw_text_centered(screen,
            "UP/DN  Select   ·   ENTER  Confirm   ·   LEFT/RIGHT  Change Difficulty",
            HEIGHT - 36, FONT_SM, GREEN_DIM)

    # -- PAUSE ----------------------------------------------------------------
    def _unpause(self):
        paused_duration = time.time() - self.pause_elapsed
        self.game_deadline += paused_duration
        self.paused = False

    def _save_progress(self):
        """Save current mission state so player can continue later."""
        sd = load_save()
        sd["in_progress"] = {
            "state": self.pre_pause_state,
            "difficulty": self.diff["label"],
            "stages_done": list(self.stages_done),
            "remaining": self.remaining_time(),
            "game_total": self.game_total,
            "intel": INTEL,
        }
        save_game(sd)
        self.cn_warning = "PROGRESS SAVED"
        self.cn_warning_timer = 1.0

    def _load_progress(self):
        """Load saved mission state."""
        sd = load_save()
        prog = sd.get("in_progress")
        if not prog:
            return False
        global INTEL, FILE_REVEALED
        INTEL = prog["intel"]
        FILE_REVEALED = build_revealed(INTEL)
        self.diff = DIFFICULTIES[prog["difficulty"]]
        self.selected_diff = prog["difficulty"]
        sd = prog["stages_done"]
        self.stages_done = set(sd) if isinstance(sd, list) else set()
        remaining = prog["remaining"]
        self.game_total = prog.get("game_total", remaining)
        self.game_deadline = time.time() + remaining
        # Jump to the right minigame
        state = prog["state"]
        if state == "intel":
            self._init_intel(restore=True)
            self.state = "intel"
        elif state == "roulette":
            self._init_roulette()
            self.state = "roulette"
        elif state == "maze":
            self._init_maze()
            self.state = "maze"
        elif state == "connect":
            self._init_connect()
            self.state = "connect"
        else:
            self._init_roulette()
            self.state = "roulette"
        # Clear saved progress
        sd.pop("in_progress", None)
        save_game(sd)
        return True

    def _update_pause(self, events, dt):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self._unpause()
                    return
                elif e.key == pygame.K_UP:
                    self.pause_cursor = (self.pause_cursor - 1) % 4
                elif e.key == pygame.K_DOWN:
                    self.pause_cursor = (self.pause_cursor + 1) % 4
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.pause_cursor == 0:  # RESUME
                        self._unpause()
                    elif self.pause_cursor == 1:  # HOW TO PLAY
                        self.howto_return_to = self.pre_pause_state
                        self.howto_scroll = 0
                        self.paused = False  # let howto state run
                        self.state = "howto"
                        # Timer stays frozen - will be adjusted on return
                    elif self.pause_cursor == 2:  # SAVE & QUIT
                        self._save_progress()
                        self._unpause()
                        self.state = "menu"
                    elif self.pause_cursor == 3:  # QUIT (no save)
                        self._unpause()
                        self.state = "menu"

    def _draw_pause(self):
        # Dim the current game screen
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Pause box
        bw, bh = 400, 300
        bx, by = (WIDTH - bw) // 2, (HEIGHT - bh) // 2
        pygame.draw.rect(screen, BLACK, (bx, by, bw, bh))
        pygame.draw.rect(screen, GREEN, (bx, by, bw, bh), 2)

        draw_text_centered(screen, "=== PAUSED ===", by + 20, FONT_LG, CYAN)

        # Show current mission status
        rem = self.remaining_time()
        status = f"Protocols done: {len(self.stages_done)}/3  |  {int(rem)}s left  |  {self.diff['label']}"
        draw_text_centered(screen, status, by + 60, FONT_SM, GREEN_DIM)

        items = ["RESUME", "HOW TO PLAY", "SAVE & QUIT TO MENU", "QUIT TO MENU"]
        for i, item in enumerate(items):
            iy = by + 100 + i * 40
            if i == self.pause_cursor:
                draw_text_centered(screen, f">> {item} <<", iy, FONT_MD, GREEN_BRIGHT)
            else:
                draw_text_centered(screen, item, iy, FONT_MD, GREEN)

        draw_text_centered(screen, "ESC to resume", by + bh - 30, FONT_SM, GREEN_DIM)

    # -- HOW TO PLAY ------------------------------------------------------
    def _update_howto(self, events, dt):
        self.rain.update(dt)
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    if self.howto_return_to in ("roulette", "maze", "connect", "intel", "transition"):
                        # Returning from pause howto - go back to pause menu
                        self.state = self.howto_return_to
                        self.paused = True
                        self.pause_cursor = 0
                    else:
                        self.state = "menu"
                elif e.key == pygame.K_UP:
                    self.howto_scroll = max(0, self.howto_scroll - 1)
                elif e.key == pygame.K_DOWN:
                    self.howto_scroll += 1

    def _draw_howto(self):
        pygame.draw.rect(screen, GREEN, (10, 10, WIDTH-20, HEIGHT-20), 1)
        draw_text_centered(screen, "=== HOW TO PLAY ===", 25, FONT_LG, CYAN)

        lines = [
            ("OBJECTIVE", CYAN, True),
            ("You are AGENT CIPHER. A classified file has been", GREEN, False),
            ("intercepted containing details of an imminent attack.", GREEN, False),
            ("Complete 3 security protocols to redact the file,", GREEN, False),
            ("then transmit the intel to HQ before time runs out.", GREEN, False),
            ("", None, False),
            ("PROTOCOL 1: ACCESS CODE ROULETTE", YELLOW, True),
            ("Numbers cycle on screen. Press SPACE to lock each digit.", GREEN, False),
            ("Match the target code shown at the top.", GREEN, False),
            ("Easy: correct digits stay locked on miss.", GREEN, False),
            ("Hard: one miss resets ALL digits.", GREEN, False),
            ("", None, False),
            ("PROTOCOL 2: MAZE EXTRACTION", YELLOW, True),
            ("Navigate the maze with ARROW KEYS (hold to move).", GREEN, False),
            ("Find the KEY (*) to unlock a gap in the wall.", GREEN, False),
            ("Escape through the gap to complete the maze.", GREEN, False),
            ("Harder difficulties add fog of war.", GREEN, False),
            ("", None, False),
            ("PROTOCOL 3: NODE LINK", YELLOW, True),
            ("Connect numbered nodes in order with ARROW KEYS.", GREEN, False),
            ("Up/Down/Left/Right only - no diagonals.", GREEN, False),
            ("Navigate around red obstacles to reach each node.", GREEN, False),
            ("Your trail must NOT cross itself!", GREEN, False),
            ("Press R to reset ALL trails if you get stuck.", GREEN, False),
            ("", None, False),
            ("INTEL PHASE", YELLOW, True),
            ("Read the file and answer each question.", GREEN, False),
            ("Choose from 4 multiple choice options.", GREEN, False),
            ("Use LEFT/RIGHT to switch questions.", GREEN, False),
            ("Limited attempts per question. Intel is RANDOMIZED!", CYAN, False),
            ("", None, False),
            ("CONTROLS", YELLOW, True),
            ("Arrow Keys .... Move / Navigate", GREEN, False),
            ("SPACE ......... Lock roulette digit", GREEN, False),
            ("R ............. Reset all trails (Node Link)", GREEN, False),
            ("ENTER ......... Confirm answer / Select", GREEN, False),
            ("ESC ........... Pause / Back / Skip", GREEN, False),
            ("", None, False),
            ("DIFFICULTIES", YELLOW, True),
            ("RECRUIT  Generous time, slow roulette, no fog", GREEN, False),
            ("AGENT    Standard challenge, moderate time", GREEN, False),
            ("SHADOW   Fast roulette, fog of war, crossing resets", GREEN, False),
            ("GHOST    Extreme speed, tiny vision, 1 attempt", GREEN, False),
        ]

        y = 65
        scroll = getattr(self, 'howto_scroll', 0)
        visible_start = scroll
        for i, (text, color, is_header) in enumerate(lines):
            if i < visible_start:
                continue
            if text == "":
                y += 14
                continue
            if color is None:
                color = GREEN
            if y > HEIGHT - 50:
                draw_text_centered(screen, "--- Arrow DOWN for more ---", HEIGHT - 35, FONT_SM, GREEN_DIM)
                break
            if is_header:
                y += 6  # extra space before headers
                draw_text(screen, text, 50, y, FONT_MD, color)
                y += 26
            else:
                draw_text(screen, text, 70, y, FONT_SM, color)
                y += 20

        draw_text_centered(screen, "[ Press ESC or ENTER to return ]", HEIGHT - 20, FONT_SM, GREEN_DIM)

    # -- BRIEFING ---------------------------------------------------------
    def _start_briefing(self):
        # Randomize intel for this mission
        global INTEL, FILE_REVEALED
        INTEL = generate_intel()
        FILE_REVEALED = build_revealed(INTEL)
        # Reset disabled-but-still-referenced subsystem state for safety
        self.event_active = None
        self.event_timer = 0
        self.event_cooldown = 5.0
        self.event_warning = ""
        self.event_warning_timer = 0
        self._pending_event = None
        self.comms_messages = []
        self.comms_text = ""
        self.comms_timer = 0
        self.comms_cooldown = 6.0
        self.comms_time_warned = False
        self.hack_type = ""
        self.hack_timer = 0
        self.hack_cooldown = 10.0
        self.state = "briefing"
        self.brief_t = 0.0

    def _update_briefing(self, events, dt):
        self.brief_t += dt
        for e in events:
            if e.type == pygame.KEYDOWN:
                self.stages_done = set()
                self._start_transition("roulette", "ACCESS CODE ROULETTE")
                return

    def _draw_briefing(self):
        pygame.draw.rect(screen, GREEN, (10, 10, WIDTH-20, HEIGHT-20), 1)
        draw_text(screen, "[ NEW MISSION ]", 20, 14, FONT_MD, GREEN)

        # Big headline
        draw_text_centered(screen, "REDACTED FILE INCOMING", 60, FONT_XL, CYAN_BRIGHT)

        # Shared vertical-file layout — same one used in the intel phase
        font = FONT_LG
        label_w = max(font.size(lbl)[0] for lbl, _k, _s in INTEL_FIELDS)
        list_w = label_w + 40 + 480
        list_x = (WIDTH - list_w) // 2
        list_y = 150
        end_y = draw_vertical_file(screen, list_x, list_y, set(), font=font)

        # Mission instruction below the list
        instr_y = end_y + 24
        draw_text_centered(screen, "Unredact this file by completing 3 challenges.",
                           instr_y, FONT_LG, YELLOW)

        # Press to begin (blinking)
        if int(self.brief_t * 2) % 2 == 0:
            draw_text_centered(screen, ">>> PRESS ENTER TO BEGIN <<<",
                               HEIGHT - 60, FONT_LG, GREEN_BRIGHT)

    # -- TRANSITION -------------------------------------------------------
    def _get_transition_instructions(self):
        """Build short, plain-language instructions for the upcoming minigame."""
        diff = self.diff
        next_state = self.trans_next

        if next_state == "roulette":
            return "PROTOCOL 1 — ACCESS CODE", [
                ("Match the rotating digits to the TARGET CODE.", GREEN),
                ("Press SPACE to lock the current digit.", GREEN),
                ("", None),
                (f"Time: {diff['roulette_time']}s   ·   Digits: {diff['roulette_digits']}", CYAN),
                ("Each correct digit grants +3 seconds.", GREEN_DIM),
            ]
        elif next_state == "maze":
            mw, mh = diff["maze_size"]
            lines = [
                ("Find the KEY, then escape through the EXIT.", GREEN),
                ("Use the ARROW KEYS to move.", GREEN),
                ("", None),
                (f"Time: {diff['maze_time']}s   ·   Size: {mw}x{mh}", CYAN),
            ]
            if diff.get("maze_guards", 0) > 0:
                lines.append((f"{diff['maze_guards']} guard(s) — avoid their sight!", RED))
            if diff.get("maze_fog", 0) > 0:
                lines.append(("Fog of war is active.", RED))
            return "PROTOCOL 2 — EXTRACTION", lines
        elif next_state == "connect":
            return "PROTOCOL 3 — NODE LINK", [
                ("Connect the numbered nodes IN ORDER.", GREEN),
                ("ARROW KEYS to move. Don't cross your trail.", GREEN),
                ("", None),
                (f"Time: {diff['connect_time']}s   ·   Nodes: {diff.get('num_nodes', 4)}", CYAN),
                ("R resets all trails.", GREEN_DIM),
            ]
        elif next_state == "intel":
            return "INTEL PHASE", [
                ("Type the missing words back into the file.", GREEN),
                ("Lines you UNLOCKED show the answer in cyan.", CYAN),
                ("Locked lines: type your best guess.", GREEN),
                ("", None),
                (f"Time: {diff['intel_time']}s   ·   Tries per slot: {diff.get('intel_attempts', 3)}", CYAN),
                ("ARROWS switch slot · letters/numbers to type · ENTER submit", GREEN_DIM),
            ]
        return self.trans_label, []

    def _draw_preview_bullets(self, x, y, w, bullets):
        """Right-column numbered bullets used by every loading-screen preview.
        Bullets: list of (num, text, color)."""
        for num, text, color in bullets:
            cx = x + 14
            cy = y + FONT_SM.get_height() // 2 + 2
            pygame.draw.circle(screen, color, (cx, cy), 13)
            num_s = FONT_SM.render(num, True, BLACK)
            screen.blit(num_s, (cx - num_s.get_width() // 2,
                                cy - num_s.get_height() // 2))
            # Word-wrap text to fit `w - 36`
            max_w = w - 36
            words = text.split(' ')
            line = ""
            ly = y
            for word in words:
                test = (line + ' ' + word).strip()
                if FONT_SM.size(test)[0] <= max_w:
                    line = test
                else:
                    draw_text(screen, line, x + 34, ly, FONT_SM, color)
                    line = word
                    ly += FONT_SM.get_linesize() + 2
            if line:
                draw_text(screen, line, x + 34, ly, FONT_SM, color)
                ly += FONT_SM.get_linesize() + 2
            y = max(ly, y + 28) + 4
        return y

    def _draw_param_pill(self, x, y, w, label):
        """Compact parameter strip drawn at the bottom of every preview."""
        pad = 10
        surf = FONT_SM.render(label, True, CYAN_BRIGHT)
        pill_h = surf.get_height() + pad
        pygame.draw.rect(screen, (0, 30, 30), (x, y, w, pill_h))
        pygame.draw.rect(screen, CYAN, (x, y, w, pill_h), 1)
        screen.blit(surf, (x + (w - surf.get_width()) // 2, y + pad // 2))
        return y + pill_h

    def _draw_connect_preview(self, x, y, w, h):
        """Animated mini node-link board so players see the goal."""
        title = FONT_MD.render("HOW NODE LINK WORKS", True, CYAN)
        screen.blit(title, (x + (w - title.get_width()) // 2, y))
        ty = y + title.get_height() + 14

        left_w = 280
        board_x = x + 20
        board_y = ty
        cell = 32
        cols = left_w // cell
        rows = max(5, (h - title.get_height() - 70) // cell)
        for r in range(rows):
            for c in range(cols):
                cx = board_x + c * cell
                cy = board_y + r * cell
                pygame.draw.rect(screen, (5, 35, 25), (cx, cy, cell, cell))
                pygame.draw.rect(screen, (0, 60, 0), (cx, cy, cell, cell), 1)

        # 4 nodes — same positions every load so muscle memory builds
        nodes = [(0, 1), (3, 0), (4, 3), (1, 3)]
        nodes_xy = [(board_x + c * cell + cell // 2,
                     board_y + r * cell + cell // 2) for c, r in nodes]
        # Sample trail 1→2 (right-angle path) drawn progressively
        trail_full = [nodes_xy[0],
                      (nodes_xy[1][0], nodes_xy[0][1]),
                      nodes_xy[1]]
        # Total path length
        seg_lens = [math.hypot(trail_full[i+1][0]-trail_full[i][0],
                               trail_full[i+1][1]-trail_full[i][1])
                    for i in range(len(trail_full)-1)]
        total_len = sum(seg_lens)
        cycle = (self.trans_timer * 90.0) % (total_len + 60)
        drawn = []
        remaining = min(cycle, total_len)
        for i, seg in enumerate(seg_lens):
            if remaining <= 0:
                break
            if not drawn:
                drawn.append(trail_full[i])
            if remaining >= seg:
                drawn.append(trail_full[i+1])
                remaining -= seg
            else:
                t = remaining / seg
                drawn.append((trail_full[i][0] + (trail_full[i+1][0] - trail_full[i][0]) * t,
                              trail_full[i][1] + (trail_full[i+1][1] - trail_full[i][1]) * t))
                remaining = 0
        if len(drawn) >= 2:
            pygame.draw.lines(screen, GREEN_BRIGHT, False,
                              [(int(p[0]), int(p[1])) for p in drawn], 4)

        # Obstacle
        ob_c, ob_r = 2, 2
        ob_x = board_x + ob_c * cell + 4
        ob_y = board_y + ob_r * cell + 4
        pygame.draw.rect(screen, RED, (ob_x, ob_y, cell - 8, cell - 8))

        # Numbered nodes
        for idx, (px, py) in enumerate(nodes_xy):
            r = 13
            connected = cycle >= total_len * (idx / max(1, len(nodes_xy) - 1))
            color = CYAN_BRIGHT if connected and idx <= 1 else (
                GREEN_BRIGHT if idx == 1 else GREEN if idx > 1 else CYAN_BRIGHT)
            pygame.draw.circle(screen, color, (px, py), r)
            pygame.draw.circle(screen, BLACK, (px, py), r - 4)
            num = FONT_SM.render(str(idx + 1), True, color)
            screen.blit(num, (px - num.get_width() // 2, py - num.get_height() // 2))

        # Right-column rules
        text_x = board_x + left_w + 30
        diff = self.diff
        bullets = [
            ("1", "Walk from node 1 → 2 → 3 → … IN ORDER.", GREEN_BRIGHT),
            ("2", "ARROW KEYS to move.", GREEN),
            ("3", "Avoid RED obstacles.", RED_BRIGHT),
            ("4", "Don't cross your own trail.", YELLOW),
        ]
        if diff.get("num_gates", 0) > 0:
            bullets.append(("5", "Pass through YELLOW GATES to unlock the matching node.", CYAN))
        self._draw_preview_bullets(text_x, ty, w - (text_x - x) - 20, bullets)

        # Parameter pill at the bottom
        pill_y = y + h - 30
        param = (f"TIME {diff['connect_time']}s   ·   NODES {diff.get('num_nodes', 4)}"
                 f"   ·   GATES {diff.get('num_gates', 0)}   ·   +2s per gate")
        self._draw_param_pill(x + 20, pill_y, w - 40, param)

    def _draw_maze_preview(self, x, y, w, h):
        """Animated mini-maze: player blip walks from start → key → exit."""
        title = FONT_MD.render("HOW MAZE EXTRACTION WORKS", True, CYAN)
        screen.blit(title, (x + (w - title.get_width()) // 2, y))
        ty = y + title.get_height() + 14

        left_w = 280
        # 13x9 sample maze (path=0, wall=1)
        sample = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,1,0,0,0,0,0,0,1],
            [1,1,1,1,0,1,0,1,1,1,1,0,1],
            [1,0,0,0,0,1,0,1,0,0,0,0,1],
            [1,0,1,1,1,1,0,1,0,1,1,1,1],
            [1,0,0,0,0,0,0,1,0,0,0,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,0,0],
            [1,0,0,0,0,0,0,0,0,0,1,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1],
        ]
        rows = len(sample); cols = len(sample[0])
        cell = min(left_w // cols, (h - title.get_height() - 70) // rows)
        cell = max(14, cell)
        board_x = x + 20 + (left_w - cols * cell) // 2
        board_y = ty
        for r in range(rows):
            for c in range(cols):
                cx = board_x + c * cell
                cy = board_y + r * cell
                color = (0, 110, 0) if sample[r][c] == 1 else (5, 30, 20)
                pygame.draw.rect(screen, color, (cx, cy, cell, cell))

        # Path: start (1,1) → key (3,1) → key (5,4) hop, then to exit (6,12)
        path = [(1,1),(1,2),(1,3),(1,4),(2,4),(3,4),(3,3),(3,2),(3,1),
                (3,2),(3,3),(3,4),(4,4),(5,4),(5,5),(5,6),(5,7),(5,8),
                (5,9),(5,10),(6,10),(6,11),(6,12)]
        kr, kc = 3, 1   # key cell
        er, ec = 6, 12  # exit cell

        n_steps = len(path) - 1
        cycle_len = n_steps + 6
        progress = (self.trans_timer * 5.5) % cycle_len
        idx = min(int(progress), n_steps)
        frac = max(0.0, min(1.0, progress - idx))
        if idx + 1 < len(path):
            r1, c1 = path[idx]; r2, c2 = path[idx + 1]
            pr = r1 + (r2 - r1) * frac
            pc = c1 + (c2 - c1) * frac
        else:
            pr, pc = path[-1]

        # Find when key is collected (path index reaches the key cell)
        try:
            key_pickup = path.index((kr, kc))
        except ValueError:
            key_pickup = 0
        key_collected = progress >= key_pickup

        # Key (yellow diamond)
        if not key_collected:
            kx = board_x + kc * cell + cell // 2
            ky = board_y + kr * cell + cell // 2
            kr_size = max(4, cell // 3)
            pygame.draw.polygon(screen, YELLOW, [
                (kx, ky - kr_size), (kx + kr_size, ky),
                (kx, ky + kr_size), (kx - kr_size, ky)])

        # Exit (pulses cyan once key is collected)
        ex = board_x + ec * cell
        ey = board_y + er * cell
        if key_collected:
            pulse = int(abs(math.sin(time.time() * 4)) * 60) + 195
            pygame.draw.rect(screen, (0, pulse, pulse), (ex, ey, cell, cell))
            pygame.draw.rect(screen, WHITE, (ex, ey, cell, cell), 1)
        else:
            pygame.draw.rect(screen, (80, 0, 0), (ex, ey, cell, cell))

        # Player blip
        pxs = board_x + pc * cell + cell // 2
        pys = board_y + pr * cell + cell // 2
        pygame.draw.circle(screen, CYAN, (int(pxs), int(pys)), max(3, cell // 3))

        # Right-column rules
        text_x = board_x + cols * cell + 40
        diff = self.diff
        bullets = [
            ("1", "Find the YELLOW KEY first — exit stays sealed.", YELLOW),
            ("2", "Then reach the CYAN EXIT.", CYAN_BRIGHT),
            ("3", "ARROW KEYS to move. Green + tiles give +10s.", GREEN_BRIGHT),
        ]
        if diff.get("maze_guards", 0) > 0:
            bullets.append(("4", "Avoid RED guards' line of sight.", RED_BRIGHT))
        if diff.get("maze_fog", 0) > 0:
            bullets.append((str(len(bullets) + 1), "Fog of war — only see what's near you.", GREEN_DIM))
        self._draw_preview_bullets(text_x, ty, w - (text_x - x) - 20, bullets)

        # Parameter pill
        pill_y = y + h - 30
        mw, mh = diff["maze_size"]
        guards_str = f"   ·   GUARDS {diff.get('maze_guards', 0)}" if diff.get("maze_guards", 0) > 0 else ""
        fog_str = "   ·   FOG ON" if diff.get("maze_fog", 0) > 0 else ""
        param = f"TIME {diff['maze_time']}s   ·   SIZE {mw}x{mh}{guards_str}{fog_str}"
        self._draw_param_pill(x + 20, pill_y, w - 40, param)

    def _draw_roulette_preview(self, x, y, w, h):
        """Animated digit reels — digits roll, then lock onto target sequentially."""
        title = FONT_MD.render("HOW ACCESS CODE WORKS", True, CYAN)
        screen.blit(title, (x + (w - title.get_width()) // 2, y))
        ty = y + title.get_height() + 14

        left_w = 280
        n = 4
        digit_w = 42
        gap = 8
        total_w = n * digit_w + (n - 1) * gap
        base_x = x + 20 + (left_w - total_w) // 2

        target = [3, 8, 1, 5]
        # Target row
        tlbl = FONT_SM.render("TARGET", True, YELLOW)
        screen.blit(tlbl, (base_x + total_w // 2 - tlbl.get_width() // 2, ty))
        target_y = ty + tlbl.get_height() + 4
        for i, d in enumerate(target):
            dx = base_x + i * (digit_w + gap)
            pygame.draw.rect(screen, DARK_GREEN, (dx, target_y, digit_w, 50))
            pygame.draw.rect(screen, YELLOW, (dx, target_y, digit_w, 50), 2)
            ts = FONT_LG.render(str(d), True, YELLOW)
            screen.blit(ts, (dx + (digit_w - ts.get_width()) // 2,
                              target_y + (50 - ts.get_height()) // 2))

        # Current row (animated)
        cur_y = target_y + 70
        clbl = FONT_SM.render("CURRENT", True, GREEN)
        screen.blit(clbl, (base_x + total_w // 2 - clbl.get_width() // 2, cur_y))
        cur_y += clbl.get_height() + 4
        # Lock one digit every 0.9s, full cycle ~6s
        per = 0.9
        cycle = per * (n + 1)
        t = self.trans_timer % cycle
        locked = min(n, int(t / per))
        for i in range(n):
            dx = base_x + i * (digit_w + gap)
            if i < locked:
                d = target[i]
                color = CYAN
                bg = (0, 40, 40)
            elif i == locked:
                d = int(t * 14) % 10
                color = WHITE
                bg = (20, 20, 20)
            else:
                d = int(t * 6 + i * 3) % 10
                color = GREEN_DIM
                bg = (10, 10, 10)
            pygame.draw.rect(screen, bg, (dx, cur_y, digit_w, 50))
            pygame.draw.rect(screen, color, (dx, cur_y, digit_w, 50), 2)
            ts = FONT_LG.render(str(d), True, color)
            screen.blit(ts, (dx + (digit_w - ts.get_width()) // 2,
                              cur_y + (50 - ts.get_height()) // 2))
        # Arrow under the digit currently being locked
        if locked < n:
            ax = base_x + locked * (digit_w + gap) + digit_w // 2
            pygame.draw.polygon(screen, WHITE, [(ax, cur_y + 56),
                                                 (ax - 7, cur_y + 68),
                                                 (ax + 7, cur_y + 68)])

        # Right-column rules
        text_x = x + 20 + left_w + 30
        diff = self.diff
        bullets = [
            ("1", "Watch the digits spin in CURRENT.", GREEN),
            ("2", "Press SPACE to lock a digit.", GREEN_BRIGHT),
            ("3", "Match every TARGET digit to win.", CYAN_BRIGHT),
            ("4", "Each correct digit grants +3s of game time.", YELLOW),
        ]
        if not diff.get("roulette_keep", True):
            bullets.append(("5", "Wrong lock RESETS all digits.", RED_BRIGHT))
        self._draw_preview_bullets(text_x, ty, w - (text_x - x) - 20, bullets)

        # Parameter pill
        pill_y = y + h - 30
        keep = "KEEP CORRECT" if diff.get("roulette_keep", True) else "FULL RESET"
        param = (f"TIME {diff['roulette_time']}s   ·   DIGITS {diff['roulette_digits']}"
                 f"   ·   ON MISS: {keep}")
        self._draw_param_pill(x + 20, pill_y, w - 40, param)

    def _draw_intel_preview(self, x, y, w, h):
        """Animated typing into a redacted field — illustrates the intel phase."""
        title = FONT_MD.render("HOW INTEL PHASE WORKS", True, CYAN)
        screen.blit(title, (x + (w - title.get_width()) // 2, y))
        ty = y + title.get_height() + 14

        left_w = 280
        # Mini file with 3 rows: 1 unlocked (cyan), 1 active (typing), 1 redacted
        rows = [
            ("TARGET",   "BLACKOUT", "unlocked"),
            ("LOCATION", "WAREHOUSE 7B", "typing"),
            ("CODE",     "", "redacted"),
        ]
        font = FONT_SM
        label_w = max(font.size(lbl)[0] for lbl, _v, _s in rows)
        row_h = 48
        row_x = x + 20
        row_w = left_w - 10
        for i, (lbl, val, kind) in enumerate(rows):
            ry = ty + i * row_h
            # Label
            screen.blit(font.render(lbl, True, GREEN_DIM), (row_x + 10, ry + 10))
            # Slot box
            slot_x = row_x + label_w + 24
            slot_w = row_w - (label_w + 34)
            slot_h = 32
            if kind == "unlocked":
                pygame.draw.rect(screen, (0, 40, 40), (slot_x, ry, slot_w, slot_h))
                pygame.draw.rect(screen, CYAN, (slot_x, ry, slot_w, slot_h), 1)
                screen.blit(font.render(val, True, CYAN_BRIGHT),
                            (slot_x + 8, ry + 6))
            elif kind == "typing":
                pygame.draw.rect(screen, (30, 30, 0), (slot_x, ry, slot_w, slot_h))
                pulse = int(abs(math.sin(time.time() * 3)) * 60) + 160
                pygame.draw.rect(screen, (pulse, pulse, 0),
                                 (slot_x, ry, slot_w, slot_h), 2)
                # Type out characters one by one
                cps = 6.0  # chars per second
                period = len(val) / cps + 1.4
                t = self.trans_timer % period
                ch_idx = min(len(val), int(t * cps))
                shown = val[:ch_idx]
                cur = "_" if int(time.time() * 2) % 2 else " "
                screen.blit(font.render(shown + cur, True, WHITE),
                            (slot_x + 8, ry + 6))
            else:
                pygame.draw.rect(screen, (0, 40, 0), (slot_x, ry, slot_w, slot_h))
                pygame.draw.rect(screen, GREEN_DIM, (slot_x, ry, slot_w, slot_h), 1)
                blocks = font.render("█" * (slot_w // 9),
                                     True, GREEN_DIM)
                screen.blit(blocks, (slot_x + 4, ry + 6))

        # Right-column rules
        text_x = row_x + left_w + 30
        diff = self.diff
        bullets = [
            ("1", "UP / DOWN cycle the multiple-choice options.", GREEN),
            ("2", "ENTER submits your pick.", GREEN_BRIGHT),
            ("3", "Unredacted fields auto-confirm — just hit ENTER.", CYAN_BRIGHT),
            ("4", "Wrong picks burn one of your tries per slot.", RED_BRIGHT),
        ]
        self._draw_preview_bullets(text_x, ty, w - (text_x - x) - 20, bullets)

        # Parameter pill
        pill_y = y + h - 30
        param = (f"TIME {diff['intel_time']}s   ·   TRIES PER SLOT "
                 f"{diff.get('intel_attempts', 3)}   ·   {len(DEBRIEF_QUESTIONS)} FIELDS")
        self._draw_param_pill(x + 20, pill_y, w - 40, param)

    # -- RESULT SCREEN (post-minigame, pre-transition) ----------------------
    def _start_result(self, success, text, next_state, label):
        """Show a result screen with fade transition."""
        # Capture current screen for dimmed overlay background
        self.result_bg = screen.copy()
        self.state = "result"
        self.result_success = success
        self.result_text = text
        self.result_next = next_state
        self.result_label = label
        self.result_fade = 0.0         # fade progress (0→0.5 = fade out game, 0.5→1.0 = fade in result)
        self.result_timer = 2.0        # lockout after fade completes
        self.result_ready = False
        self.result_fade_done = False   # True once fade animation is complete
        # Freeze the game timer during result screen
        self.result_pause_start = time.time()

    def _update_result(self, events, dt):
        # Phase 1: fade animation (2s total: 1s fade out, 1s fade in)
        if not self.result_fade_done:
            self.result_fade += dt
            if self.result_fade >= 2.0:
                self.result_fade = 2.0
                self.result_fade_done = True
            return
        # Phase 2: lockout countdown
        if not self.result_ready:
            self.result_timer -= dt
            if self.result_timer <= 0:
                self.result_ready = True
        else:
            for e in events:
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    paused = time.time() - self.result_pause_start
                    self.game_deadline += paused
                    self._start_transition(self.result_next, self.result_label)

    def _draw_result(self):
        fade = self.result_fade  # 0→1.0 = fade out game, 1.0→2.0 = fade in result

        # Phase 1 (0–1.0s): game fades to black
        if fade < 1.0:
            dim_alpha = int((fade / 1.0) * 255)
            if self.result_bg:
                screen.blit(self.result_bg, (0, 0))
            else:
                screen.fill(BLACK)
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, min(255, dim_alpha)))
            screen.blit(dim, (0, 0))
            return

        # Phase 2 (1.0–2.0s): result content fades in over dimmed game
        content_alpha = int(((fade - 1.0) / 1.0) * 255) if fade < 2.0 else 255

        # Dimmed game background
        if self.result_bg:
            screen.blit(self.result_bg, (0, 0))
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 200))
        screen.blit(dim, (0, 0))

        # Result content on a separate surface for alpha fade-in
        content = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        if self.result_success:
            t = time.time()
            pulse = int(abs(math.sin(t * 3)) * 80) + 175
            pygame.draw.rect(content, (0, pulse, pulse), (10, 10, WIDTH - 20, HEIGHT - 20), 3)
            ts1 = FONT_XL.render("PROTOCOL COMPLETE", True, CYAN_BRIGHT)
            content.blit(ts1, ((WIDTH - ts1.get_width()) // 2, 30))
            sub = FONT_MD.render("FILE SECTION DECRYPTED", True, GREEN)
            content.blit(sub, ((WIDTH - sub.get_width()) // 2, 30 + ts1.get_height() + 6))
            caption = FONT_SM.render("JUST UNREDACTED — shown in cyan below", True, GREEN_DIM)
        else:
            t = time.time()
            pulse = int(abs(math.sin(t * 5)) * 80) + 175
            pygame.draw.rect(content, (pulse, 0, 0), (10, 10, WIDTH - 20, HEIGHT - 20), 3)
            ts1 = FONT_XL.render("PROTOCOL FAILED", True, RED_BRIGHT)
            content.blit(ts1, ((WIDTH - ts1.get_width()) // 2, 30))
            sub = FONT_MD.render(self.result_text, True, YELLOW)
            content.blit(sub, ((WIDTH - sub.get_width()) // 2, 30 + ts1.get_height() + 6))
            caption = FONT_SM.render("THESE FIELDS STAY REDACTED", True, RED)

        # Shared vertical-file layout — same one used in the briefing & intel phase.
        # On success, self.stages_done already contains the just-completed stage,
        # so its fields render as cyan reveals. On failure, that stage is absent,
        # so its fields stay as redacted bars.
        cap_y = 30 + ts1.get_height() + 6 + sub.get_height() + 14
        content.blit(caption, ((WIDTH - caption.get_width()) // 2, cap_y))

        font = FONT_MD
        label_w = max(font.size(lbl)[0] for lbl, _k, _s in INTEL_FIELDS)
        list_w = label_w + 40 + 480
        list_x = (WIDTH - list_w) // 2
        list_y = cap_y + caption.get_height() + 18
        draw_vertical_file(content, list_x, list_y, self.stages_done, font=font)

        if content_alpha < 255:
            mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            mask.fill((255, 255, 255, content_alpha))
            content.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        screen.blit(content, (0, 0))

        # Prompt (only after fade + lockout)
        if self.result_ready:
            if int(time.time() * 2) % 2:
                draw_text_centered(screen, ">>> PRESS SPACE TO CONTINUE <<<", HEIGHT - 60, FONT_LG, WHITE)

    def _start_transition(self, next_state, label):
        self.state = "transition"
        self.trans_next = next_state
        self.trans_label = label
        self.trans_timer = 0
        self.trans_ready = False
        self.trans_pause_start = 0

    def _update_transition(self, events, dt):
        if not self.trans_ready:
            # Brief loading phase (1.5s) then show instructions
            self.trans_timer += dt
            if self.trans_timer >= 1.5:
                self.trans_ready = True
                # Freeze the main timer while user reads instructions
                self.trans_pause_start = time.time()
        else:
            # Waiting for user to press ENTER
            for e in events:
                if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Set per-game timer and init the next minigame
                    time_key = self.trans_next + "_time"
                    self.game_total = self.diff.get(time_key, 60)
                    self.game_deadline = time.time() + self.game_total
                    # Reset per-game event state
                    self.comms_time_warned = False
                    self.event_active = None
                    self.event_cooldown = 5.0
                    if self.trans_next == "roulette":
                        self._init_roulette()
                    elif self.trans_next == "maze":
                        self._init_maze()
                    elif self.trans_next == "connect":
                        self._init_connect()
                    elif self.trans_next == "intel":
                        self._init_intel()
                    self.state = self.trans_next

    def _draw_transition(self):
        pygame.draw.rect(screen, GREEN, (10, 10, WIDTH-20, HEIGHT-20), 1)
        title, _instr_unused = self._get_transition_instructions()

        # Header strip — "INCOMING PROTOCOL" + protocol title in a clear box
        draw_text_centered(screen, "INCOMING PROTOCOL", 28, FONT_MD, GREEN_DIM)
        # Pulsing border for the title to draw the eye
        pulse = int(abs(math.sin(time.time() * 2)) * 60) + 160
        title_box_w = 760
        title_box_x = (WIDTH - title_box_w) // 2
        pygame.draw.rect(screen, (0, pulse, pulse),
                         (title_box_x, 60, title_box_w, 70), 2)
        draw_text_centered(screen, title, 70, FONT_XL, CYAN_BRIGHT)

        # Animated preview — same 760×520 frame for every protocol so the
        # loading screen feels uniform and players know where to look.
        preview_w = 760
        preview_h = 520
        preview_x = (WIDTH - preview_w) // 2
        preview_y = 150
        pygame.draw.rect(screen, GREEN_DIM,
                         (preview_x, preview_y, preview_w, preview_h), 1)
        if self.trans_next == "roulette":
            self._draw_roulette_preview(preview_x, preview_y + 14, preview_w, preview_h - 14)
        elif self.trans_next == "maze":
            self._draw_maze_preview(preview_x, preview_y + 14, preview_w, preview_h - 14)
        elif self.trans_next == "connect":
            self._draw_connect_preview(preview_x, preview_y + 14, preview_w, preview_h - 14)
        elif self.trans_next == "intel":
            self._draw_intel_preview(preview_x, preview_y + 14, preview_w, preview_h - 14)

        # Bottom: prompt
        if self.trans_ready:
            if int(time.time() * 2) % 2:
                draw_text_centered(screen, ">>> PRESS ENTER TO START <<<",
                                   HEIGHT - 50, FONT_LG, GREEN_BRIGHT)
        else:
            draw_text_centered(screen, "[ LOADING ]", HEIGHT - 50, FONT_LG, GREEN_DIM)

    # -- ROULETTE ---------------------------------------------------------
    def _scramble_roulette_digit(self):
        """Change one unlocked target digit to a different value."""
        unlocked = [i for i in range(len(self.rl_target))
                     if not self.rl_locked[i] and i >= self.rl_lock_idx]
        if unlocked:
            idx = random.choice(unlocked)
            old = self.rl_target[idx]
            new = old
            while new == old:
                new = random.randint(0, 9)
            self.rl_target[idx] = new

    def _init_roulette(self):
        n = self.diff["roulette_digits"]
        lo, hi = self.diff["roulette_speed"]
        self.rl_target = [random.randint(0, 9) for _ in range(n)]
        self.rl_current = [random.randint(0, 9) for _ in range(n)]
        self.rl_locked = [False] * n
        self.rl_lock_idx = 0
        self.rl_speeds = [random.uniform(lo, hi) for _ in range(n)]
        self.rl_timers = [0.0] * n

    def _update_roulette(self, events, dt):
        rem = self.remaining_time()
        if rem <= 0:
            # Time's up — skip to maze without completing redaction
            self.flash_timer = 0.3
            self.flash_color = RED
            self._start_result(False, "Time expired - code not cracked", "maze", "MAZE EXTRACTION")
            return

        # Only spin the currently active digit
        i = self.rl_lock_idx
        if i < len(self.rl_current) and not self.rl_locked[i]:
            self.rl_timers[i] += dt
            if self.rl_timers[i] >= self.rl_speeds[i]:
                self.rl_timers[i] = 0
                self.rl_current[i] = (self.rl_current[i] + 1) % 10

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    self.state = "menu"
                    return
                if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.rl_lock_idx < len(self.rl_target):
                        idx = self.rl_lock_idx
                        self.rl_locked[idx] = True
                        if self.rl_current[idx] == self.rl_target[idx]:
                            play_sound(None)
                            self.game_deadline += 3  # +3s per correct digit
                            self.rl_lock_idx += 1
                            if self.rl_lock_idx >= len(self.rl_target):
                                # WIN
                                play_sound(None)
                                self.stages_done.add(0)
                                self._trigger_comms_success()
                                self.flash_timer = 0.3
                                self.flash_color = CYAN
                                self._start_result(True, "Access code cracked - file section decrypted", "maze", "MAZE EXTRACTION")
                        else:
                            play_sound(None)
                            self.flash_timer = 0.3
                            self.flash_color = RED
                            lo, hi = self.diff["roulette_speed"]
                            if self.diff["roulette_keep"]:
                                self.rl_locked[idx] = False
                                self.rl_current[idx] = random.randint(0, 9)
                            else:
                                n = self.diff["roulette_digits"]
                                self.rl_target = [random.randint(0, 9) for _ in range(n)]
                                self.rl_current = [random.randint(0, 9) for _ in range(n)]
                                self.rl_locked = [False] * n
                                self.rl_lock_idx = 0
                                self.rl_speeds = [random.uniform(lo, hi) for _ in range(n)]
                                self.rl_timers = [0.0] * n

    def _draw_roulette(self):
        # Game-area frame on the right; sidebar (timer + redaction file) on the left.
        pygame.draw.rect(screen, GREEN,
                         (GAME_AREA_X, 12, GAME_AREA_W, HEIGHT - 24), 1)
        draw_sidebar(screen, self.remaining_time(),
                     self.diff["roulette_time"], self.stages_done, active_stage=0)

        n = len(self.rl_target)
        digit_w = 60
        total_w = n * digit_w + (n - 1) * 20
        center_x = GAME_AREA_X + GAME_AREA_W // 2
        start_x = center_x - total_w // 2

        # Headline
        draw_text(screen, "PROTOCOL 1 — ACCESS CODE",
                  GAME_AREA_X + 16, 24, FONT_SM, GREEN_DIM)

        # Target
        ts_label = FONT_MD.render("TARGET", True, YELLOW)
        screen.blit(ts_label, (center_x - ts_label.get_width() // 2, 70))
        ty = 110
        for i, d in enumerate(self.rl_target):
            x = start_x + i * (digit_w + 20)
            pygame.draw.rect(screen, DARK_GREEN, (x, ty, digit_w, 70))
            pygame.draw.rect(screen, YELLOW, (x, ty, digit_w, 70), 2)
            ts = FONT_XL.render(str(d), True, YELLOW)
            screen.blit(ts, (x + (digit_w - ts.get_width())//2, ty + (70 - ts.get_height())//2))

        # Current
        cur_label = FONT_MD.render("CURRENT", True, GREEN)
        screen.blit(cur_label, (center_x - cur_label.get_width() // 2, 220))
        cy = 260
        for i in range(n):
            x = start_x + i * (digit_w + 20)
            d = self.rl_current[i]

            if self.rl_locked[i]:
                border_color = CYAN if self.rl_current[i] == self.rl_target[i] else RED
                bg = (0, 40, 40) if border_color == CYAN else (40, 0, 0)
                text_color = border_color
            elif i == self.rl_lock_idx:
                border_color = WHITE
                bg = (20, 20, 20)
                text_color = WHITE
            else:
                border_color = GREEN_DIM
                bg = (10, 10, 10)
                text_color = GREEN_DIM

            pygame.draw.rect(screen, bg, (x, cy, digit_w, 70))
            pygame.draw.rect(screen, border_color, (x, cy, digit_w, 70), 2)

            ts = FONT_XL.render(str(d), True, text_color)
            screen.blit(ts, (x + (digit_w - ts.get_width())//2, cy + (70 - ts.get_height())//2))

        # Arrow
        if self.rl_lock_idx < n:
            ax = start_x + self.rl_lock_idx * (digit_w + 20) + digit_w // 2
            pygame.draw.polygon(screen, WHITE, [(ax, cy + 80), (ax - 8, cy + 95), (ax + 8, cy + 95)])

        # Status
        locked = sum(self.rl_locked)
        st = FONT_MD.render(f"DIGITS LOCKED: {locked}/{n}", True, GREEN)
        screen.blit(st, (center_x - st.get_width() // 2, 390))

        if self.rl_lock_idx < n:
            hint = FONT_SM.render(
                f"Locking digit {self.rl_lock_idx+1}… time your lock with SPACE",
                True, GREEN_DIM)
            screen.blit(hint, (center_x - hint.get_width() // 2, 430))

    # -- MAZE -------------------------------------------------------------
    def _init_maze(self):
        tw, th = self.diff["maze_size"]
        # Maze lives in the right-hand game area (sidebar holds timer + file).
        avail_w = GAME_AREA_W - 20
        avail_h = HEIGHT - 80   # top margin + small bottom margin
        max_w = avail_w // 10
        max_h = avail_h // 10
        mw = min(tw, max_w)
        mh = min(th, max_h)
        mw = max(5, mw)
        mh = max(4, mh)

        self.maze_grid = generate_maze(mw, mh)
        self.maze_gh = len(self.maze_grid)
        self.maze_gw = len(self.maze_grid[0])
        self.maze_cell_size = min(avail_w // self.maze_gw, avail_h // self.maze_gh)
        self.maze_cell_size = max(4, min(self.maze_cell_size, 40))  # clamp 4-40
        self.maze_player = [1, 1]
        self.maze_has_key = False

        # Collect all open cells
        open_cells = []
        for r in range(1, self.maze_gh - 1):
            for c in range(1, self.maze_gw - 1):
                if self.maze_grid[r][c] == 0 and [r, c] != [1, 1]:
                    open_cells.append([r, c])

        # Place exit as a gap in the border wall, far from player start
        # Find border wall cells adjacent to an open interior cell
        border_exits = []
        for r in range(self.maze_gh):
            for c in range(self.maze_gw):
                if self.maze_grid[r][c] == 1 and (r == 0 or r == self.maze_gh - 1 or c == 0 or c == self.maze_gw - 1):
                    # This is a border wall — check if an open cell is adjacent inside
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r + dr, c + dc
                        if 0 < nr < self.maze_gh - 1 and 0 < nc < self.maze_gw - 1 and self.maze_grid[nr][nc] == 0:
                            dist = abs(r - 1) + abs(c - 1)
                            border_exits.append(([r, c], dist))
                            break
        # Sort by distance from start, pick from farthest 30%
        border_exits.sort(key=lambda x: x[1], reverse=True)
        top_n = max(1, len(border_exits) // 3)
        self.maze_exit_pos = random.choice(border_exits[:top_n])[0]
        # The exit starts as a wall; it opens when key is found
        self.maze_exit_open = False

        # Place key: far from player start
        open_cells.sort(key=lambda p: abs(p[0] - 1) + abs(p[1] - 1), reverse=True)
        top_n = max(1, len(open_cells) // 5)
        self.maze_key_pos = random.choice(open_cells[:top_n])

        # Place guards
        num_guards = self.diff.get("maze_guards", 0)
        self.maze_guards = []
        self.maze_guard_alert = 0
        guard_cells = [c for c in open_cells if abs(c[0] - 1) + abs(c[1] - 1) > 8]
        if not guard_cells:
            guard_cells = open_cells[:]
        for _ in range(min(num_guards, len(guard_cells))):
            pos = random.choice(guard_cells)
            guard_cells = [c for c in guard_cells if abs(c[0] - pos[0]) + abs(c[1] - pos[1]) > 4]
            # Pick a random valid direction
            dirs = []
            for d in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = pos[0] + d[0], pos[1] + d[1]
                if 0 <= nr < self.maze_gh and 0 <= nc < self.maze_gw and self.maze_grid[nr][nc] == 0:
                    dirs.append(d)
            d = random.choice(dirs) if dirs else (0, 1)
            self.maze_guards.append({"pos": list(pos), "dir": d, "timer": 0})

        # Place time pickups (green + symbols scattered in the maze)
        self.maze_time_pickups = []
        available = [c for c in open_cells
                     if c != self.maze_key_pos and abs(c[0] - 1) + abs(c[1] - 1) > 3]
        num_pickups = 3  # 3 pickups in every maze
        random.shuffle(available)
        for i in range(min(num_pickups, len(available))):
            self.maze_time_pickups.append(available[i])

    def _update_maze_guards(self, dt):
        """Move guards and check if they spot the player."""
        speed = self.diff.get("guard_speed", 3.0)
        vision = self.diff.get("guard_vision", 4)
        step_time = 1.0 / speed

        for guard in self.maze_guards:
            guard["timer"] += dt
            if guard["timer"] >= step_time:
                guard["timer"] -= step_time
                dr, dc = guard["dir"]
                nr, nc = guard["pos"][0] + dr, guard["pos"][1] + dc
                if 0 <= nr < self.maze_gh and 0 <= nc < self.maze_gw and self.maze_grid[nr][nc] == 0:
                    guard["pos"] = [nr, nc]
                else:
                    # Hit wall — pick new direction (not reverse)
                    reverse = (-dr, -dc)
                    options = []
                    for d in [(-1,0),(1,0),(0,-1),(0,1)]:
                        if d == reverse:
                            continue
                        tr, tc = guard["pos"][0] + d[0], guard["pos"][1] + d[1]
                        if 0 <= tr < self.maze_gh and 0 <= tc < self.maze_gw and self.maze_grid[tr][tc] == 0:
                            options.append(d)
                    if not options:
                        options = [reverse]  # dead end, turn around
                    guard["dir"] = random.choice(options)

            # Vision check: raycast in facing direction
            dr, dc = guard["dir"]
            for step in range(1, vision + 1):
                vr = guard["pos"][0] + dr * step
                vc = guard["pos"][1] + dc * step
                if not (0 <= vr < self.maze_gh and 0 <= vc < self.maze_gw):
                    break
                if self.maze_grid[vr][vc] == 1:
                    break  # wall blocks vision
                if [vr, vc] == self.maze_player:
                    # SPOTTED!
                    self.flash_timer = 0.3
                    self.flash_color = RED
                    self.game_deadline -= 8  # lose 8 seconds
                    self.maze_player = [1, 1]  # back to start
                    self.maze_guard_alert = 2.0
                    # Relocate guard far from player
                    far_cells = []
                    for r in range(1, self.maze_gh - 1):
                        for c in range(1, self.maze_gw - 1):
                            if self.maze_grid[r][c] == 0 and abs(r - 1) + abs(c - 1) > 6:
                                far_cells.append([r, c])
                    if far_cells:
                        guard["pos"] = random.choice(far_cells)
                    break

        if self.maze_guard_alert > 0:
            self.maze_guard_alert -= dt

    def _maze_try_move(self, dr, dc):
        """Try to move the player in the maze. Returns True if moved."""
        nr = self.maze_player[0] + dr
        nc = self.maze_player[1] + dc
        if 0 <= nr < self.maze_gh and 0 <= nc < self.maze_gw and self.maze_grid[nr][nc] == 0:
            self.maze_player = [nr, nc]
            play_sound(None)

            # Check time pickup
            for tp in self.maze_time_pickups[:]:
                if self.maze_player == tp:
                    self.maze_time_pickups.remove(tp)
                    self.game_deadline += 10  # +10 seconds
                    self.flash_timer = 0.15
                    self.flash_color = GREEN
                    self._add_comms_message("HQ: +10 SECONDS - Time bonus collected!", CYAN)
                    break

            if self.maze_player == self.maze_key_pos and not self.maze_has_key:
                self.maze_has_key = True
                # Open the exit — turn the border wall into a path
                er, ec = self.maze_exit_pos
                self.maze_grid[er][ec] = 0
                self.maze_exit_open = True
                play_sound(None)

            if self.maze_player == self.maze_exit_pos and self.maze_exit_open:
                play_sound(None)
                self.stages_done.add(1)
                self._trigger_comms_success()
                self.flash_timer = 0.3
                self.flash_color = CYAN
                self._start_result(True, "Maze escaped - file section decrypted", "connect", "NODE LINK")
            return True
        return False

    def _update_maze(self, events, dt):
        rem = self.remaining_time()
        if rem <= 0:
            # Time's up — skip to connect without completing redaction
            self.flash_timer = 0.3
            self.flash_color = RED
            self._start_result(False, "Time expired - maze not completed", "connect", "NODE LINK")
            return

        # Update guards
        if self.maze_guards:
            self._update_maze_guards(dt)

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    self.state = "menu"
                    return

        # Hold-to-move: poll held keys with a repeat timer
        MAZE_MOVE_INITIAL = 0.0    # first move is instant on keydown
        MAZE_MOVE_REPEAT = 0.07    # repeat rate when held (fast & smooth)

        keys = pygame.key.get_pressed()
        dr, dc = 0, 0
        if keys[pygame.K_UP]: dr = -1
        elif keys[pygame.K_DOWN]: dr = 1
        elif keys[pygame.K_LEFT]: dc = -1
        elif keys[pygame.K_RIGHT]: dc = 1
        # Disruption: invert controls
        if self._is_controls_inverted():
            dr, dc = -dr, -dc

        if dr != 0 or dc != 0:
            direction = (dr, dc)
            if direction != getattr(self, '_maze_last_dir', None):
                # New direction: move immediately
                self._maze_last_dir = direction
                self._maze_move_timer = 0
                self._maze_try_move(dr, dc)
            else:
                # Same direction held: repeat after timer
                self._maze_move_timer = getattr(self, '_maze_move_timer', 0) + dt
                if self._maze_move_timer >= MAZE_MOVE_REPEAT:
                    self._maze_move_timer = 0
                    self._maze_try_move(dr, dc)
        else:
            self._maze_last_dir = None
            self._maze_move_timer = 0

    def _draw_maze(self):
        pygame.draw.rect(screen, GREEN,
                         (GAME_AREA_X, 12, GAME_AREA_W, HEIGHT - 24), 1)
        draw_sidebar(screen, self.remaining_time(),
                     self.diff["maze_time"], self.stages_done, active_stage=1)
        draw_text(screen, "PROTOCOL 2 — MAZE EXTRACTION",
                  GAME_AREA_X + 16, 16, FONT_SM, GREEN_DIM)

        cs = self.maze_cell_size
        ox = GAME_AREA_X + (GAME_AREA_W - self.maze_gw * cs) // 2
        oy = 40

        fog = self.diff["maze_fog"]
        pr, pc = self.maze_player

        # Render maze to a surface
        maze_surf = pygame.Surface((self.maze_gw * cs, self.maze_gh * cs))
        maze_surf.fill(BLACK)

        for r in range(self.maze_gh):
            for c in range(self.maze_gw):
                x = c * cs
                y = r * cs

                if self.maze_grid[r][c] == 1:
                    # Wall - solid green block
                    pygame.draw.rect(maze_surf, (0, 160, 0), (x, y, cs, cs))
                else:
                    # Floor - visible dark teal so paths stand out
                    pygame.draw.rect(maze_surf, (5, 40, 30), (x, y, cs, cs))

        # Time pickups - green "+" symbols
        for tp in self.maze_time_pickups:
            tr, tc = tp
            tx, ty = tc * cs + cs // 2, tr * cs + cs // 2
            pr_sz = max(2, cs // 3)
            pygame.draw.line(maze_surf, GREEN_BRIGHT, (tx - pr_sz, ty), (tx + pr_sz, ty), max(1, cs // 5))
            pygame.draw.line(maze_surf, GREEN_BRIGHT, (tx, ty - pr_sz), (tx, ty + pr_sz), max(1, cs // 5))

        # Key - yellow diamond shape, scaled to cell
        if not self.maze_has_key:
            kr, kc = self.maze_key_pos
            kx, ky_pos = kc * cs + cs//2, kr * cs + cs//2
            r = max(2, cs//3)
            pygame.draw.polygon(maze_surf, YELLOW, [
                (kx, ky_pos - r), (kx + r, ky_pos), (kx, ky_pos + r), (kx - r, ky_pos)
            ])

        # Exit - a gap in the border wall
        er, ec = self.maze_exit_pos
        ex, ey = ec * cs, er * cs
        if self.maze_exit_open:
            # Exit is open — draw a bright pulsing gap
            pulse = int(abs(math.sin(time.time() * 4)) * 55) + 200
            pygame.draw.rect(maze_surf, (0, pulse, pulse), (ex, ey, cs, cs))
            # Bright border lines to make it pop
            pygame.draw.rect(maze_surf, WHITE, (ex, ey, cs, cs), 1)
        else:
            # Exit is still sealed — show a faint red marker on the wall
            pygame.draw.rect(maze_surf, (80, 0, 0), (ex, ey, cs, cs))

        # Guards on maze_surf (drawn before fog so fog covers them at distance)
        for guard in self.maze_guards:
            gr, gc = guard["pos"]
            gx, gy = gc * cs + cs // 2, gr * cs + cs // 2
            gradius = max(2, cs // 3)
            pygame.draw.circle(maze_surf, RED, (gx, gy), gradius)
            # Direction indicator
            ddr, ddc = guard["dir"]
            lx = gx + ddc * max(2, cs // 2)
            ly = gy + ddr * max(2, cs // 2)
            pygame.draw.line(maze_surf, RED_BRIGHT, (gx, gy), (lx, ly), max(1, cs // 6))

        # Player on maze_surf (will be redrawn on screen after fog)
        px_pos, py_pos = pc * cs + cs//2, pr * cs + cs//2
        pradius = max(3, cs//2)
        pygame.draw.circle(maze_surf, CYAN, (px_pos, py_pos), pradius)

        # Apply fog of war using colorkey surfaces (proven to work)
        if fog > 0:
            fog_px = max(fog * cs * 2, fog * 28)
            center = (pc * cs + cs // 2, pr * cs + cs // 2)
            sz = maze_surf.get_size()
            # Use (2,2,2) as colorkey - won't appear naturally in maze
            CK = (2, 2, 2)

            # Layer 1: heavy darkness outside the large circle
            f1 = pygame.Surface(sz)
            f1.fill(BLACK)
            f1.set_colorkey(CK)
            pygame.draw.circle(f1, CK, center, fog_px)
            f1.set_alpha(220)
            maze_surf.blit(f1, (0, 0))

            # Layer 2: medium darkness outside the medium circle
            f2 = pygame.Surface(sz)
            f2.fill(BLACK)
            f2.set_colorkey(CK)
            pygame.draw.circle(f2, CK, center, int(fog_px * 0.65))
            f2.set_alpha(140)
            maze_surf.blit(f2, (0, 0))

            # Layer 3: light darkness outside the small circle
            f3 = pygame.Surface(sz)
            f3.fill(BLACK)
            f3.set_colorkey(CK)
            pygame.draw.circle(f3, CK, center, int(fog_px * 0.4))
            f3.set_alpha(70)
            maze_surf.blit(f3, (0, 0))

        # Blit maze to screen
        screen.blit(maze_surf, (ox, oy))

        # Draw guards ON SCREEN (visible through fog as red dots)
        for guard in self.maze_guards:
            gr, gc_pos = guard["pos"]
            sgx = ox + gc_pos * cs + cs // 2
            sgy = oy + gr * cs + cs // 2
            pygame.draw.circle(screen, RED, (sgx, sgy), max(2, cs // 4))

        # Draw player ON SCREEN on top of everything (always visible over fog)
        screen_px = ox + pc * cs + cs // 2
        screen_py = oy + pr * cs + cs // 2
        pygame.draw.circle(screen, CYAN, (screen_px, screen_py), pradius)
        if cs >= 12:
            pt = FONT_SM.render("@", True, BLACK)
            screen.blit(pt, (screen_px - pt.get_width()//2, screen_py - pt.get_height()//2))

        # Guard alert warning
        if self.maze_guard_alert > 0:
            pulse = int(abs(math.sin(time.time() * 8)) * 55) + 200
            alert = FONT_SM.render("!! SECURITY ALERT - DETECTED !!", True, (pulse, 0, 0))
            screen.blit(alert,
                        (GAME_AREA_X + GAME_AREA_W - alert.get_width() - 16, 16))


    # -- CONNECT ----------------------------------------------------------
    def _init_connect(self):
        num = self.diff["num_nodes"]
        area_w, area_h = GAME_AREA_W - 60, HEIGHT - 200
        self.cn_area_offset = (GAME_AREA_X + 30, 60)
        self.cn_area_size = (area_w, area_h)

        # Generate obstacles (rectangular barriers) -- varied sizes
        self.cn_obstacles = []
        num_obstacles = self.diff.get("num_obstacles", num)
        for _ in range(num_obstacles):
            for _attempt in range(100):
                # Varied obstacle types
                kind = random.random()
                if kind < 0.35:
                    # Long thin barrier
                    ow = random.randint(60, 130)
                    oh = random.randint(6, 12)
                elif kind < 0.65:
                    # Medium block
                    ow = random.randint(30, 70)
                    oh = random.randint(20, 45)
                else:
                    # Small square blocker
                    ow = random.randint(14, 30)
                    oh = random.randint(14, 30)
                if random.random() > 0.5:
                    ow, oh = oh, ow  # rotate
                ox = random.randint(20, area_w - 20 - ow)
                oy = random.randint(20, area_h - 20 - oh)
                # Don't overlap existing obstacles too much
                overlap = False
                for eox, eoy, eow, eoh in self.cn_obstacles:
                    if (ox < eox + eow + 15 and ox + ow + 15 > eox and
                        oy < eoy + eoh + 15 and oy + oh + 15 > eoy):
                        overlap = True
                        break
                if not overlap:
                    self.cn_obstacles.append((ox, oy, ow, oh))
                    break

        # Generate gates — each gate is assigned to a node and must be
        # passed through before that node will activate.
        num_gates = self.diff.get("num_gates", 0)
        gap = 20  # just wide enough to squeeze through
        self.cn_gates = []          # list of gate dicts
        self.cn_gate_obstacles = [] # obstacle pairs belonging to gates (drawn differently)
        # Assign gates to evenly-spaced nodes (skip node 0, it's the start)
        if num_gates > 0 and num > 2:
            candidates = list(range(1, num))
            step = max(1, len(candidates) // num_gates)
            gate_nodes = candidates[step-1::step][:num_gates]
            # Fill remainder if needed
            for c in candidates:
                if len(gate_nodes) >= num_gates:
                    break
                if c not in gate_nodes:
                    gate_nodes.append(c)
            gate_nodes = sorted(gate_nodes[:num_gates])
        else:
            gate_nodes = []

        for gnode in gate_nodes:
            for _attempt in range(150):
                vertical = random.random() > 0.5
                if vertical:
                    # Two horizontal bars — gap runs vertically between them
                    bw = random.randint(50, 100)
                    bh = random.randint(8, 14)
                    gx = random.randint(40, area_w - 40 - bw)
                    gy = random.randint(40, area_h - 80 - bh * 2 - gap)
                    ob1 = (gx, gy, bw, bh)
                    ob2 = (gx, gy + bh + gap, bw, bh)
                    # Trigger zone is the gap between the two bars
                    trigger = (gx, gy + bh, bw, gap)
                else:
                    # Two vertical bars — gap runs horizontally between them
                    bw = random.randint(8, 14)
                    bh = random.randint(50, 100)
                    gx = random.randint(40, area_w - 80 - bw * 2 - gap)
                    gy = random.randint(40, area_h - 40 - bh)
                    ob1 = (gx, gy, bw, bh)
                    ob2 = (gx + bw + gap, gy, bw, bh)
                    trigger = (gx + bw, gy, gap, bh)
                # Check no overlap with existing obstacles or gate obstacles
                all_obs = self.cn_obstacles + self.cn_gate_obstacles
                ok = True
                for ob in (ob1, ob2):
                    for eox, eoy, eow, eoh in all_obs:
                        if (ob[0] < eox + eow + 15 and ob[0] + ob[2] + 15 > eox and
                            ob[1] < eoy + eoh + 15 and ob[1] + ob[3] + 15 > eoy):
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    self.cn_gate_obstacles.append(ob1)
                    self.cn_gate_obstacles.append(ob2)
                    self.cn_gates.append({
                        "node": gnode,
                        "ob1": ob1, "ob2": ob2,
                        "trigger": trigger,
                        "activated": False,
                    })
                    break

        # Gate node lookup: which nodes require a gate?
        self.cn_gated_nodes = {}  # node_index -> gate_index
        for gi, g in enumerate(self.cn_gates):
            self.cn_gated_nodes[g["node"]] = gi

        # Place nodes avoiding obstacles AND gate obstacles
        self.cn_nodes = []
        min_dist = 55 if num <= 6 else 40 if num <= 8 else 35
        for i in range(num):
            for _ in range(500):
                nx = random.randint(30, area_w - 30)
                ny = random.randint(30, area_h - 30)
                too_close = any(math.hypot(nx-ex, ny-ey) < min_dist for ex, ey in self.cn_nodes)
                # Check not inside an obstacle or gate obstacle
                in_obstacle = False
                for oox, ooy, oow, ooh in self.cn_obstacles + self.cn_gate_obstacles:
                    if oox - 15 < nx < oox + oow + 15 and ooy - 15 < ny < ooy + ooh + 15:
                        in_obstacle = True
                        break
                if not too_close and not in_obstacle:
                    self.cn_nodes.append((nx, ny))
                    break
            else:
                self.cn_nodes.append((random.randint(30, area_w-30), random.randint(30, area_h-30)))

        self.cn_player = list(self.cn_nodes[0])
        self.cn_target = 1
        self.cn_connected = [0]
        self.cn_current_trail = [tuple(self.cn_nodes[0])]
        self.cn_locked_trails = []
        self.cn_warning = ""
        self.cn_warning_timer = 0
        self.cn_move_speed = 250  # pixels per second

    def _update_connect(self, events, dt):
        rem = self.remaining_time()
        if rem <= 0:
            # Time's up — skip to intel without completing redaction
            self.flash_timer = 0.3
            self.flash_color = RED
            self._start_result(False, "Time expired - nodes not linked", "intel", "INTEL REPORT")
            return

        self.cn_warning_timer = max(0, self.cn_warning_timer - dt)

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_q:
                    self.state = "menu"
                    return
                if e.key == pygame.K_r:
                    # Full reset - go back to node 0, clear all trails & gates
                    self.cn_player = list(self.cn_nodes[0])
                    self.cn_target = 1
                    self.cn_connected = [0]
                    self.cn_current_trail = [tuple(self.cn_nodes[0])]
                    self.cn_locked_trails = []
                    for g in self.cn_gates:
                        g["activated"] = False
                    self.cn_warning = "FULL TRAIL RESET"
                    self.cn_warning_timer = 1.0

        # Cardinal movement only (no diagonal)
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_UP]: dy = -1
        elif keys[pygame.K_DOWN]: dy = 1
        elif keys[pygame.K_LEFT]: dx = -1
        elif keys[pygame.K_RIGHT]: dx = 1
        # Disruption: invert controls
        if self._is_controls_inverted():
            dx, dy = -dx, -dy

        if dx != 0 or dy != 0:
            speed = self.cn_move_speed * dt
            new_x = self.cn_player[0] + dx * speed
            new_y = self.cn_player[1] + dy * speed

            # Clamp to area
            area_w, area_h = self.cn_area_size
            new_x = max(0, min(area_w, new_x))
            new_y = max(0, min(area_h, new_y))

            # Check obstacle collision (regular + gate obstacles)
            blocked = False
            for oox, ooy, oow, ooh in self.cn_obstacles + self.cn_gate_obstacles:
                if oox - 4 < new_x < oox + oow + 4 and ooy - 4 < new_y < ooy + ooh + 4:
                    blocked = True
                    break

            if blocked:
                return

            old_pos = tuple(self.cn_player)
            new_pos = (new_x, new_y)

            # Check locked trail intersection
            crosses = False
            for trail in self.cn_locked_trails:
                for ti in range(len(trail) - 1):
                    if segments_intersect(old_pos, new_pos, trail[ti], trail[ti+1]):
                        crosses = True
                        break
                if crosses:
                    break

            if crosses:
                mode = self.diff.get("node_cross_mode", "none")
                if mode == "full":
                    # SHADOW/GHOST: full reset back to node 0
                    self.cn_warning = "!! LINE CROSSED - FULL RESET !!"
                    self.cn_warning_timer = 1.5
                    self.cn_player = list(self.cn_nodes[0])
                    self.cn_target = 1
                    self.cn_connected = [0]
                    self.cn_current_trail = [tuple(self.cn_nodes[0])]
                    self.cn_locked_trails = []
                    for g in self.cn_gates:
                        g["activated"] = False
                elif mode == "last":
                    # AGENT: reset current trail to last locked node
                    self.cn_warning = "!! LINE CROSSED - TRAIL RESET !!"
                    self.cn_warning_timer = 1.5
                    last = self.cn_nodes[self.cn_connected[-1]]
                    self.cn_player = list(last)
                    self.cn_current_trail = [tuple(last)]
                else:
                    # RECRUIT: nothing happens, just pass through
                    pass
            else:
                self.cn_player = [new_x, new_y]
                self.cn_current_trail.append(tuple(self.cn_player))

                # Limit trail length for performance
                if len(self.cn_current_trail) > 5000:
                    self.cn_current_trail = self.cn_current_trail[-4000:]

                # Check gate trigger zones
                for gate in self.cn_gates:
                    if not gate["activated"]:
                        tx, ty, tw, th = gate["trigger"]
                        if tx <= new_x <= tx + tw and ty <= new_y <= ty + th:
                            gate["activated"] = True
                            self.game_deadline += 2  # +2s per gate passed
                            self.cn_warning = f"GATE {gate['node']} ACTIVATED"
                            self.cn_warning_timer = 1.0

                # Check if near target node
                if self.cn_target < len(self.cn_nodes):
                    tx, ty = self.cn_nodes[self.cn_target]
                    if math.hypot(new_x - tx, new_y - ty) < 18:
                        # Check if this node requires a gate
                        gate_blocked = False
                        if self.cn_target in self.cn_gated_nodes:
                            gi = self.cn_gated_nodes[self.cn_target]
                            if not self.cn_gates[gi]["activated"]:
                                self.cn_warning = f"NODE {self.cn_target} LOCKED - FIND ITS GATE!"
                                self.cn_warning_timer = 1.5
                                gate_blocked = True

                        if not gate_blocked:
                            self.cn_connected.append(self.cn_target)
                            self.cn_locked_trails.append(list(self.cn_current_trail))
                            self.cn_player = list(self.cn_nodes[self.cn_target])
                            self.cn_current_trail = [tuple(self.cn_player)]
                            self.cn_target += 1
                            play_sound(None)

                            if self.cn_target >= len(self.cn_nodes):
                                play_sound(None)
                                self.stages_done.add(2)
                                self._trigger_comms_success()
                                self.flash_timer = 0.3
                                self.flash_color = CYAN
                                self._start_result(True, "All nodes linked - file section decrypted", "intel", "INTEL REPORT")

    def _draw_connect(self):
        pygame.draw.rect(screen, GREEN,
                         (GAME_AREA_X, 12, GAME_AREA_W, HEIGHT - 24), 1)
        draw_sidebar(screen, self.remaining_time(),
                     self.diff["connect_time"], self.stages_done, active_stage=2)
        draw_text(screen, "PROTOCOL 3 — NODE LINK",
                  GAME_AREA_X + 16, 16, FONT_SM, GREEN_DIM)

        ox, oy = self.cn_area_offset
        area_w, area_h = self.cn_area_size

        # Draw dot grid background
        for gx in range(0, area_w, 30):
            for gy in range(0, area_h, 30):
                screen.set_at((ox + gx, oy + gy), GREEN_DIM)

        # Draw obstacles
        for oox, ooy, oow, ooh in self.cn_obstacles:
            pygame.draw.rect(screen, RED, (oox + ox, ooy + oy, oow, ooh))
            pygame.draw.rect(screen, RED_BRIGHT, (oox + ox, ooy + oy, oow, ooh), 1)

        # Draw gates (distinct from regular obstacles)
        for gate in self.cn_gates:
            color = CYAN if gate["activated"] else YELLOW
            border = CYAN if gate["activated"] else (180, 180, 0)
            for ob_key in ("ob1", "ob2"):
                oox, ooy, oow, ooh = gate[ob_key]
                pygame.draw.rect(screen, color, (oox + ox, ooy + oy, oow, ooh))
                pygame.draw.rect(screen, border, (oox + ox, ooy + oy, oow, ooh), 1)
            # Draw node number label in the trigger gap
            tx, ty, tw, th = gate["trigger"]
            cx = tx + tw // 2 + ox
            cy = ty + th // 2 + oy
            lbl = str(gate["node"])
            t = FONT_SM.render(lbl, True, BLACK if gate["activated"] else BLACK)
            # Small background circle for readability
            pygame.draw.circle(screen, color, (cx, cy), 10)
            screen.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))

        # Draw locked trails (thick - match node size)
        trail_w = 10
        for trail in self.cn_locked_trails:
            if len(trail) >= 2:
                pts = [(int(p[0])+ox, int(p[1])+oy) for p in trail]
                pygame.draw.lines(screen, CYAN, False, pts, trail_w)

        # Draw current trail (thick - match node size)
        if len(self.cn_current_trail) >= 2:
            pts = [(int(p[0])+ox, int(p[1])+oy) for p in self.cn_current_trail]
            pygame.draw.lines(screen, GREEN, False, pts, trail_w)

        # Draw nodes
        for i, (nx, ny) in enumerate(self.cn_nodes):
            sx, sy = int(nx) + ox, int(ny) + oy
            if i in self.cn_connected:
                pygame.draw.circle(screen, CYAN, (sx, sy), 14)
                pygame.draw.circle(screen, BLACK, (sx, sy), 11)
                lbl = format(i, 'X') if i >= 10 else str(i)
                t = FONT_SM.render(lbl, True, CYAN)
                screen.blit(t, (sx - t.get_width()//2, sy - t.get_height()//2))
            elif i == self.cn_target:
                # Check if this node is gate-locked
                is_locked = False
                if i in self.cn_gated_nodes:
                    gi = self.cn_gated_nodes[i]
                    is_locked = not self.cn_gates[gi]["activated"]
                if is_locked:
                    # Locked node — red pulsing ring with lock symbol
                    pulse = int(abs(math.sin(time.time() * 4)) * 55) + 200
                    pygame.draw.circle(screen, (pulse, 0, 0), (sx, sy), 16, 3)
                    pygame.draw.circle(screen, RED, (sx, sy), 12)
                    pygame.draw.circle(screen, BLACK, (sx, sy), 9)
                    t = FONT_SM.render("X", True, RED)
                    screen.blit(t, (sx - t.get_width()//2, sy - t.get_height()//2))
                else:
                    pulse = int(abs(math.sin(time.time() * 4)) * 55) + 200
                    pygame.draw.circle(screen, (pulse, pulse, 0), (sx, sy), 16, 3)
                    pygame.draw.circle(screen, YELLOW, (sx, sy), 12)
                    pygame.draw.circle(screen, BLACK, (sx, sy), 9)
                    lbl = format(i, 'X') if i >= 10 else str(i)
                    t = FONT_SM.render(lbl, True, YELLOW)
                    screen.blit(t, (sx - t.get_width()//2, sy - t.get_height()//2))
            else:
                pygame.draw.circle(screen, GREEN_DIM, (sx, sy), 12)
                pygame.draw.circle(screen, BLACK, (sx, sy), 9)
                lbl = format(i, 'X') if i >= 10 else str(i)
                t = FONT_SM.render(lbl, True, GREEN_DIM)
                screen.blit(t, (sx - t.get_width()//2, sy - t.get_height()//2))

        # Player
        px = int(self.cn_player[0]) + ox
        py = int(self.cn_player[1]) + oy
        pygame.draw.circle(screen, WHITE, (px, py), 6)

        # Progress (centered in the game area)
        status = f"NODES: {len(self.cn_connected)}/{len(self.cn_nodes)}"
        if self.cn_gates:
            activated = sum(1 for g in self.cn_gates if g["activated"])
            status += f"  |  GATES: {activated}/{len(self.cn_gates)}"
        s_surf = FONT_MD.render(status, True, GREEN)
        cx = GAME_AREA_X + GAME_AREA_W // 2
        screen.blit(s_surf, (cx - s_surf.get_width() // 2, HEIGHT - 80))

        # Warning
        if self.cn_warning_timer > 0:
            w_surf = FONT_SM.render(self.cn_warning, True, RED_BRIGHT)
            screen.blit(w_surf, (cx - w_surf.get_width() // 2, HEIGHT - 110))

    # -- INTEL (confirm if unlocked, multiple choice if locked) -----------
    def _init_intel(self, restore=False):
        self.intel_cursor = 0
        self.intel_choice_cursor = 0
        self.intel_answers = [None] * len(DEBRIEF_QUESTIONS)
        self.intel_attempts = [self.diff["intel_attempts"]] * len(DEBRIEF_QUESTIONS)
        self.intel_correct = 0
        self.intel_feedback = ""
        self.intel_feedback_color = GREEN
        self.intel_feedback_timer = 0.0

        # For each question: build either a 4-option choice list (locked
        # stage — player must guess) or None (unlocked — just confirm).
        self.intel_choices = []
        for _label, key in DEBRIEF_QUESTIONS:
            if QUESTION_STAGE.get(key) in self.stages_done:
                self.intel_choices.append(None)
            else:
                correct = INTEL[key]
                pool = [v for v in INTEL_POOL[key] if v != correct]
                wrongs = random.sample(pool, min(3, len(pool)))
                options = wrongs + [correct]
                random.shuffle(options)
                self.intel_choices.append(options)

        self._intel_skip_done()

    def _intel_skip_done(self):
        """Land cursor on the next unresolved slot, if any."""
        n = len(DEBRIEF_QUESTIONS)
        for _ in range(n):
            if (self.intel_answers[self.intel_cursor] is not None or
                self.intel_attempts[self.intel_cursor] <= 0):
                self.intel_cursor = (self.intel_cursor + 1) % n
            else:
                self.intel_choice_cursor = 0
                return
        self.intel_choice_cursor = 0

    def _intel_next_unresolved(self):
        n = len(DEBRIEF_QUESTIONS)
        for off in range(1, n + 1):
            idx = (self.intel_cursor + off) % n
            if self.intel_answers[idx] is None and self.intel_attempts[idx] > 0:
                self.intel_cursor = idx
                self.intel_choice_cursor = 0
                return

    def _intel_submit(self):
        i = self.intel_cursor
        key = DEBRIEF_QUESTIONS[i][1]
        choices = self.intel_choices[i]
        correct = INTEL[key]

        if choices is None:
            # Unlocked — auto-confirm.
            picked = correct
        else:
            picked = choices[self.intel_choice_cursor]

        if picked == correct:
            self.intel_answers[i] = correct
            self.intel_correct += 1
            self.intel_feedback = "CORRECT"
            self.intel_feedback_color = CYAN_BRIGHT
            self.flash_timer = 0.12
            self.flash_color = CYAN
            self._intel_next_unresolved()
        else:
            self.intel_attempts[i] -= 1
            if self.intel_attempts[i] <= 0:
                self.intel_feedback = f"OUT OF TRIES — answer was {correct}"
                self.intel_feedback_color = RED_BRIGHT
                self._intel_next_unresolved()
            else:
                self.intel_feedback = (
                    f"WRONG — {self.intel_attempts[i]} "
                    f"{'try' if self.intel_attempts[i] == 1 else 'tries'} left"
                )
                self.intel_feedback_color = RED
            self.flash_timer = 0.18
            self.flash_color = RED
        self.intel_feedback_timer = 1.6

    def _update_intel(self, events, dt):
        if self.intel_feedback_timer > 0:
            self.intel_feedback_timer -= dt

        if self.remaining_time() <= 0:
            self._finish_intel()
            return
        all_done = all(a is not None or att <= 0
                       for a, att in zip(self.intel_answers, self.intel_attempts))
        if all_done:
            self._finish_intel()
            return

        n = len(DEBRIEF_QUESTIONS)
        for e in events:
            if e.type != pygame.KEYDOWN:
                continue
            i = self.intel_cursor
            resolved = (self.intel_answers[i] is not None or
                        self.intel_attempts[i] <= 0)
            choices = self.intel_choices[i]

            if e.key == pygame.K_LEFT:
                self.intel_cursor = (i - 1) % n
                self.intel_choice_cursor = 0
                self.intel_feedback_timer = 0
            elif e.key == pygame.K_RIGHT:
                self.intel_cursor = (i + 1) % n
                self.intel_choice_cursor = 0
                self.intel_feedback_timer = 0
            elif resolved:
                continue
            elif e.key == pygame.K_UP and choices is not None:
                self.intel_choice_cursor = (self.intel_choice_cursor - 1) % len(choices)
            elif e.key == pygame.K_DOWN and choices is not None:
                self.intel_choice_cursor = (self.intel_choice_cursor + 1) % len(choices)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._intel_submit()

    def _finish_intel(self):
        self.state = "debrief"
        self._compute_rank()

    # ---- intel rendering helpers ----
    def _intel_slot_rect(self, line_idx, key):
        """Approximate (x, y, w, h) for a redacted slot in the rendered file.
        Used for the visual highlight box when a slot is selected."""
        # Best-effort: the file is monospace, but layout has fixed columns.
        # We just box the whole line; that's clear enough for the player.
        font = FONT_MD
        lh = font.get_linesize() + 2
        file_w = font.size(FILE_HEADER[0])[0]
        file_x = (WIDTH - file_w) // 2
        # File starts at y=20 with 3 header lines, then redacted lines
        line_y = 20 + len(FILE_HEADER) * lh + line_idx * lh
        return (file_x, line_y, file_w, lh)

    def _draw_intel(self):
        pygame.draw.rect(screen, GREEN, (10, 10, WIDTH - 20, HEIGHT - 20), 1)
        draw_timer_bar(screen, self.remaining_time(), self.game_total)

        # ----- FILE at top — same vertical layout as the briefing -----
        i = self.intel_cursor
        label, key = DEBRIEF_QUESTIONS[i]
        ans = self.intel_answers[i]
        att = self.intel_attempts[i]

        font = FONT_MD
        label_w = max(font.size(lbl)[0] for lbl, _k, _s in INTEL_FIELDS)
        list_w = label_w + 40 + 480
        list_x = (WIDTH - list_w) // 2
        y = draw_vertical_file(screen, list_x, 20, self.stages_done,
                               font=font, active_key=key) + 12

        # Question dots row (overall progress)
        dy = y
        dot_x = (WIDTH - len(DEBRIEF_QUESTIONS) * 60) // 2
        for j, (lbl, k) in enumerate(DEBRIEF_QUESTIONS):
            a = self.intel_answers[j]
            at_j = self.intel_attempts[j]
            if a is not None:
                c, marker = CYAN, "✓"
            elif at_j <= 0:
                c, marker = RED, "✗"
            elif j == self.intel_cursor:
                c, marker = WHITE, "▸"
            else:
                c, marker = GREEN_DIM, "•"
            draw_text(screen, f"{marker} {lbl[:3]}", dot_x, dy, FONT_SM, c)
            dot_x += 60
        y = dy + FONT_SM.get_linesize() + 16

        # Question label
        prompt = label
        draw_text_centered(screen, prompt, y, FONT_LG, YELLOW)
        y += FONT_LG.get_linesize() + 8

        # Hint line
        choices = self.intel_choices[i]
        if ans is not None:
            hint = "✓ CORRECT — confirmed"
            hint_color = CYAN_BRIGHT
        elif att <= 0:
            hint = f"✗ FAILED — answer was: {INTEL[key]}"
            hint_color = RED_BRIGHT
        elif choices is None:
            hint = "UNLOCKED — press ENTER to confirm the answer above"
            hint_color = CYAN
        else:
            hint = f"Tries left: {att}   ·   UP/DN  pick   ·   ENTER  submit"
            hint_color = GREEN_DIM
        draw_text_centered(screen, hint, y, FONT_MD, hint_color)
        y += FONT_MD.get_linesize() + 14

        if choices is None:
            # Unlocked — show the answer big with a CONFIRM box
            box_w = 760
            box_h = FONT_LG.get_linesize() + 24
            box_x = (WIDTH - box_w) // 2
            border = CYAN_BRIGHT if ans is None else CYAN
            pygame.draw.rect(screen, (0, 20, 20), (box_x, y, box_w, box_h))
            pygame.draw.rect(screen, border, (box_x, y, box_w, box_h), 2)
            disp = INTEL[key]
            ts = FONT_LG.render(disp, True, CYAN_BRIGHT)
            screen.blit(ts, (box_x + (box_w - ts.get_width()) // 2,
                             y + (box_h - ts.get_height()) // 2))
            y += box_h + 14
        else:
            # Locked — multiple choice
            letters = "ABCD"
            for ci, option in enumerate(choices):
                is_sel = (ci == self.intel_choice_cursor)
                if ans is not None:
                    color = CYAN if option == INTEL[key] else GREEN_DIM
                elif att <= 0:
                    color = RED_BRIGHT if option == INTEL[key] else GREEN_DIM
                elif is_sel:
                    color = WHITE
                else:
                    color = GREEN
                marker = ">" if is_sel and ans is None and att > 0 else " "
                line = f"{marker} [{letters[ci]}]  {option}"
                draw_text_centered(screen, line, y, FONT_MD, color)
                y += FONT_MD.get_linesize() + 4
            y += 10

        # Feedback flash
        if self.intel_feedback_timer > 0 and self.intel_feedback:
            draw_text_centered(screen, self.intel_feedback, y, FONT_MD, self.intel_feedback_color)

        # Bottom controls hint
        controls = "LEFT/RIGHT  switch slot   ·   UP/DN  pick option   ·   ENTER  submit"
        draw_text_centered(screen, controls, HEIGHT - 32, FONT_SM, GREEN_DIM)

    # -- DEBRIEF ----------------------------------------------------------
    def _compute_rank(self):
        total = len(DEBRIEF_QUESTIONS)
        pct = self.intel_correct / total if total > 0 else 0

        if pct >= 0.9:
            self.debrief_rank = "LEGENDARY"
        elif pct >= 0.7:
            self.debrief_rank = "EXCELLENT"
        elif pct >= 0.5:
            self.debrief_rank = "ADEQUATE"
        elif pct >= 0.25:
            self.debrief_rank = "POOR"
        else:
            self.debrief_rank = "CATASTROPHIC FAILURE"

        # Save
        sd = load_save()
        dk = self.diff["label"]
        current_best = sd.get("best", {}).get(dk)
        if current_best is None or RANK_ORDER.index(self.debrief_rank) > RANK_ORDER.index(current_best):
            sd.setdefault("best", {})[dk] = self.debrief_rank
        save_game(sd)

    def _update_debrief(self, events, dt):
        for e in events:
            if e.type == pygame.KEYDOWN:
                self.state = "menu"

    def _draw_debrief(self):
        total = len(DEBRIEF_QUESTIONS)
        pct = self.intel_correct / total if total > 0 else 0
        redact_pct = len(self.stages_done) / 3
        rank = self.debrief_rank
        mission_success = pct >= 0.5

        if rank in ("LEGENDARY", "EXCELLENT"):
            rank_color = CYAN
        elif rank == "ADEQUATE":
            rank_color = YELLOW
        else:
            rank_color = RED

        border_color = CYAN if mission_success else RED
        pygame.draw.rect(screen, border_color, (10, 10, WIDTH-20, HEIGHT-20), 2)
        draw_text(screen, "[ HQ DEBRIEF - CLASSIFIED ]", 20, 12, FONT_SM, border_color)

        sy = 50
        if mission_success:
            draw_text_centered(screen, "M I S S I O N   S U C C E S S", sy, FONT_LG, CYAN)
        else:
            draw_text_centered(screen, "M I S S I O N   F A I L E D", sy, FONT_LG, RED)

        # Stats box
        sy = 110
        bx, bw, bh = 200, 620, 160
        pygame.draw.rect(screen, GREEN, (bx, sy, bw, bh), 1)

        draw_text(screen, f"DIFFICULTY:         {self.diff['label']}", bx + 20, sy + 15, FONT_MD, GREEN)
        draw_text(screen, f"REDACTION PROGRESS: {int(redact_pct * 100)}%", bx + 20, sy + 45, FONT_MD, GREEN)
        draw_text(screen, f"INTEL ACCURACY:     {self.intel_correct}/{total} correct", bx + 20, sy + 75, FONT_MD, GREEN)
        draw_text(screen, f"AGENT RATING:       {rank}", bx + 20, sy + 105, FONT_MD, rank_color)

        # Debrief text
        sy = 300
        draw_text(screen, "DIRECTOR KNOX:", 40, sy, FONT_MD, CYAN)
        sy += 35

        if rank == "LEGENDARY":
            lines = [
                "Outstanding work, Agent Cipher.",
                "Every piece of intel was reported accurately.",
                "The attack has been neutralized. Zero civilian casualties.",
                "You are hereby awarded the Director's Medal of Excellence.",
            ]
        elif rank == "EXCELLENT":
            lines = [
                "Strong performance, Agent.",
                "Most intel was reported correctly. The attack was thwarted.",
                "Minor gaps in your report, but field teams filled them in.",
            ]
        elif rank == "ADEQUATE":
            lines = [
                "The mission is... partially successful, Agent.",
                "Your intel had significant gaps.",
                "Field teams scrambled to compensate. Some damage occurred.",
            ]
        elif rank == "POOR":
            lines = [
                "This is a disappointing result, Agent Cipher.",
                "Critical intel was missing or incorrect.",
                "The attack caused significant damage before responders arrived.",
            ]
        else:
            lines = [
                "Agent Cipher... this is a disaster.",
                "Almost none of the intel was usable.",
                "The attack succeeded. Casualties are mounting.",
                "Your clearance is revoked effective immediately.",
            ]

        for line in lines:
            draw_text(screen, f"  {line}", 40, sy, FONT_SM, GREEN)
            sy += 24

        sy += 20
        if int(time.time() * 2) % 2:
            draw_text_centered(screen, ">>> PRESS ANY KEY TO RETURN TO HQ <<<", sy, FONT_MD, border_color)


# --- MAIN --------------------------------------------------------------------

async def main():
    game = Game()
    await game.run()

asyncio.run(main())
