#!/usr/bin/env python3
"""
D A T A   B R E A C H — A Terminal Hacker Game
================================================
You are AGENT CIPHER. HQ has intercepted a file containing mission-critical
intel on an imminent terrorist attack. You must redact the file before it
falls into enemy hands. Complete 3 security protocols, then input the intel
to stop the attack before time runs out.

Controls: Arrow keys to move, ENTER/SPACE to confirm, Q to quit
Requires: Python 3, a terminal with color support (most terminals work)
"""

import curses
import time
import random
import textwrap
import json
import os

# ─── SAVE FILE ───────────────────────────────────────────────────────────────

SAVE_PATH = os.path.join(os.path.expanduser("~"), ".databreach_save.json")

def load_save():
    """Load save data. Returns dict with best ranks per difficulty."""
    try:
        with open(SAVE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"best": {}, "last_difficulty": "AGENT"}

def save_game(data):
    """Write save data to disk."""
    with open(SAVE_PATH, "w") as f:
        json.dump(data, f)

# ─── DIFFICULTY ──────────────────────────────────────────────────────────────

DIFFICULTIES = {
    "RECRUIT": {
        "label":         "RECRUIT",
        "description":   "For first-time agents. Generous time, slow roulette.",
        "total_time":    240,
        "roulette_digits": 3,
        "roulette_speed": (0.55, 0.75),
        "roulette_keep":  True,     # keep correct digits on wrong lock
        "maze_size":     (6, 4),
        "maze_fog":      0,         # 0 = full visibility
        "num_nodes":     5,
        "node_cross_reset": False,  # crossing trail does NOT reset
        "intel_attempts": 5,
        "intel_bonus":   45,
    },
    "AGENT": {
        "label":         "AGENT",
        "description":   "Standard field operation. Balanced challenge.",
        "total_time":    180,
        "roulette_digits": 4,
        "roulette_speed": (0.35, 0.55),
        "roulette_keep":  True,
        "maze_size":     (10, 6),
        "maze_fog":      0,
        "num_nodes":     8,
        "node_cross_reset": False,
        "intel_attempts": 3,
        "intel_bonus":   30,
    },
    "SHADOW": {
        "label":         "SHADOW",
        "description":   "Elite operatives only. Fog of war, full roulette reset.",
        "total_time":    120,
        "roulette_digits": 5,
        "roulette_speed": (0.20, 0.35),
        "roulette_keep":  False,    # full reset on wrong lock
        "maze_size":     (14, 8),
        "maze_fog":      4,         # visibility radius
        "num_nodes":     10,
        "node_cross_reset": True,   # crossing trail resets to last node
        "intel_attempts": 2,
        "intel_bonus":   15,
    },
    "GHOST": {
        "label":         "GHOST",
        "description":   "Impossible. Fog of war, no mercy. Prove yourself.",
        "total_time":    90,
        "roulette_digits": 6,
        "roulette_speed": (0.12, 0.22),
        "roulette_keep":  False,
        "maze_size":     (16, 10),
        "maze_fog":      3,
        "num_nodes":     12,
        "node_cross_reset": True,
        "intel_attempts": 1,
        "intel_bonus":   10,
    },
}

DIFFICULTY_ORDER = ["RECRUIT", "AGENT", "SHADOW", "GHOST"]

# Active difficulty — set before each run
DIFF = DIFFICULTIES["AGENT"]

# ─── CONSTANTS ───────────────────────────────────────────────────────────────

TOTAL_TIME = 180  # default, overridden by DIFF at runtime
MATRIX_CHARS = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF"
# Lines 3-9 are data lines (indices 0-6 in these lists)
# Grouped into 3 stages: stage1 = lines 0-1, stage2 = lines 2-4, stage3 = lines 5-6
FILE_HEADER = [
    "╔══════════════════════════════════════════════════════════╗",
    "║  CLASSIFIED — OPERATION BLACKOUT — EYES ONLY            ║",
    "║──────────────────────────────────────────────────────────║",
]
FILE_FOOTER_SEP = "║──────────────────────────────────────────────────────────║"
FILE_BOTTOM = "╚══════════════════════════════════════════════════════════╝"

FILE_REDACTED = [
    "║  TARGET: ██████████████  CODE: ████████                 ║",
    "║  LOCATION: ████████████████████████████                 ║",
    "║  DATE: ████████  TIME: ████████                        ║",
    "║  OPERATIVES: ████████, ████████, ████████              ║",
    "║  METHOD: ██████████████████████████                     ║",
    "║  FUNDING: $██████████  SOURCE: ████████████            ║",
    "║  CONTACTS: ████████████████████████████████             ║",
]

# Actual intel that gets revealed — player must memorize/read these for the debrief
INTEL = {
    "target":     "Grand Central",
    "code":       "OMEGA-7",
    "location":   "New York City",
    "date":       "03-27",
    "time":       "14:30",
    "operatives": "VIPER",
    "method":     "EMP device",
    "funding":    "2.4M",
    "source":     "PHANTOM LLC",
    "contact":    "RAVEN",
}

FILE_REVEALED = [
    f"║  TARGET: {INTEL['target']:<14s}  CODE: {INTEL['code']:<8s}                 ║",
    f"║  LOCATION: {INTEL['location']:<28s}                 ║",
    f"║  DATE: {INTEL['date']:<10s}TIME: {INTEL['time']:<8s}                        ║",
    f"║  OPERATIVES: {INTEL['operatives']:<30s}              ║",
    f"║  METHOD: {INTEL['method']:<26s}                     ║",
    f"║  FUNDING: ${INTEL['funding']:<11s} SOURCE: {INTEL['source']:<12s}            ║",
    f"║  CONTACTS: {INTEL['contact']:<32s}             ║",
]

# Which data lines each stage reveals (indices into FILE_REDACTED/FILE_REVEALED)
STAGE_LINES = [
    [0, 1],        # Stage 1: TARGET, LOCATION
    [2, 3, 4],     # Stage 2: DATE, OPERATIVES, METHOD
    [5, 6],        # Stage 3: FUNDING, CONTACTS
]

# Questions for the debrief — answers must match INTEL values (case-insensitive)
DEBRIEF_QUESTIONS = [
    ("What is the TARGET of the attack?",       "target"),
    ("What CITY is the attack located in?",      "location"),
    ("What is the operation CODE name?",         "code"),
    ("What DATE is the attack planned? (MM-DD)", "date"),
    ("What TIME is the attack scheduled?",       "time"),
    ("Who is the lead OPERATIVE?",               "operatives"),
    ("What METHOD of attack will be used?",      "method"),
    ("Who is the primary CONTACT?",              "contact"),
]


# ─── UTILITY FUNCTIONS ───────────────────────────────────────────────────────

def init_colors():
    """Initialize color pairs for the Matrix aesthetic."""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)    # main green
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)    # inverse green
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)    # bright white
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)      # red/danger
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # yellow/warning
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)     # cyan/info
    curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_GREEN)    # solid green block
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)      # red inverse


GREEN = 1
GREEN_INV = 2
WHITE = 3
RED = 4
YELLOW = 5
CYAN = 6
GREEN_BLOCK = 7
RED_INV = 8


def safe_addstr(win, y, x, text, attr=0):
    """Safely add string, ignoring out-of-bounds errors."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0:
        return
    text = text[:max(0, w - x - 1)]
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


def draw_border(win, color_pair=GREEN):
    """Draw a border with the given color."""
    try:
        win.attron(curses.color_pair(color_pair))
        win.border()
        win.attroff(curses.color_pair(color_pair))
    except curses.error:
        pass


def center_x(win, text):
    """Get x position to center text in window."""
    _, w = win.getmaxyx()
    return max(0, (w - len(text)) // 2)


def typewriter(win, y, x, text, color=GREEN, delay=0.03):
    """Print text with typewriter effect."""
    for i, ch in enumerate(text):
        safe_addstr(win, y, x + i, ch, curses.color_pair(color) | curses.A_BOLD)
        win.refresh()
        time.sleep(delay)


def draw_timer(win, remaining, total):
    """Draw the countdown timer bar at the top."""
    h, w = win.getmaxyx()
    bar_width = w - 20
    filled = max(0, int(bar_width * remaining / total))

    if remaining > total * 0.5:
        color = GREEN
    elif remaining > total * 0.25:
        color = YELLOW
    else:
        color = RED

    time_str = f" TIME: {int(remaining)}s "
    safe_addstr(win, 0, 2, time_str, curses.color_pair(color) | curses.A_BOLD)

    bar_start = len(time_str) + 3
    bar = "█" * filled + "░" * (bar_width - filled)
    safe_addstr(win, 0, bar_start, bar[:w - bar_start - 2], curses.color_pair(color))


def draw_file_status(win, y_start, stages_done):
    """Draw the redacted file with progress — reveals actual content per stage."""
    h, w = win.getmaxyx()
    ref_line = FILE_HEADER[0]  # reference for centering

    # Build set of revealed data-line indices
    revealed = set()
    for s in range(stages_done):
        for idx in STAGE_LINES[s]:
            revealed.add(idx)

    row = y_start

    # Header
    for line in FILE_HEADER:
        if row >= h - 1:
            return
        safe_addstr(win, row, center_x(win, ref_line), line, curses.color_pair(GREEN))
        row += 1

    # Data lines
    for i in range(len(FILE_REDACTED)):
        if row >= h - 1:
            return
        if i in revealed:
            # Show redacted-text version (██ blocks replaced with [REDACTED])
            safe_addstr(win, row, center_x(win, ref_line), FILE_REVEALED[i],
                        curses.color_pair(CYAN) | curses.A_BOLD)
        else:
            # Still blacked out with ██ blocks
            safe_addstr(win, row, center_x(win, ref_line), FILE_REDACTED[i],
                        curses.color_pair(GREEN) | curses.A_DIM)
        row += 1

    # Footer separator
    if row < h - 1:
        safe_addstr(win, row, center_x(win, ref_line), FILE_FOOTER_SEP, curses.color_pair(GREEN))
        row += 1

    # Status line
    if row < h - 1:
        pct = int(stages_done / 3 * 100)
        status = f"║  STATUS: REDACTION {'COMPLETE' if pct == 100 else 'IN PROGRESS'} [{pct}%]"
        status += " " * (len(ref_line) - len(status) - 1) + "║"
        color = CYAN if pct == 100 else GREEN
        safe_addstr(win, row, center_x(win, ref_line), status, curses.color_pair(color) | curses.A_BOLD)
        row += 1

    # Bottom border
    if row < h - 1:
        safe_addstr(win, row, center_x(win, ref_line), FILE_BOTTOM, curses.color_pair(GREEN))


# ─── MATRIX RAIN ─────────────────────────────────────────────────────────────

def matrix_rain(stdscr, duration=4.0):
    """Display the iconic Matrix rain effect."""
    stdscr.clear()
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()

    drops = [random.randint(-h, 0) for _ in range(w)]
    speeds = [random.uniform(0.3, 1.0) for _ in range(w)]
    accum = [0.0 for _ in range(w)]

    start = time.time()
    while time.time() - start < duration:
        for col in range(min(w - 1, len(drops))):
            accum[col] += speeds[col]
            if accum[col] >= 1.0:
                accum[col] = 0.0
                drops[col] += 1

            row = drops[col]
            if 0 <= row < h:
                ch = random.choice(MATRIX_CHARS)
                safe_addstr(stdscr, row, col, ch, curses.color_pair(WHITE) | curses.A_BOLD)
            if 0 <= row - 1 < h:
                ch = random.choice(MATRIX_CHARS)
                safe_addstr(stdscr, row - 1, col, ch, curses.color_pair(GREEN) | curses.A_BOLD)
            if 0 <= row - 2 < h:
                ch = random.choice(MATRIX_CHARS)
                safe_addstr(stdscr, row - 2, col, ch, curses.color_pair(GREEN) | curses.A_DIM)
            if 0 <= row - 4 < h:
                safe_addstr(stdscr, row - 4, col, " ", 0)

            if drops[col] > h + 4:
                drops[col] = random.randint(-10, -1)
                speeds[col] = random.uniform(0.3, 1.0)

        stdscr.refresh()
        time.sleep(0.04)

        key = stdscr.getch()
        if key != -1:
            break

    stdscr.nodelay(False)


# ─── TITLE SCREEN ────────────────────────────────────────────────────────────

TITLE_ART = [
    "██████╗  █████╗ ████████╗ █████╗ ",
    "██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗",
    "██║  ██║███████║   ██║   ███████║",
    "██║  ██║██╔══██║   ██║   ██╔══██║",
    "██████╔╝██║  ██║   ██║   ██║  ██║",
    "╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝",
]
TITLE_ART2 = [
    "██████╗ ██████╗ ███████╗ █████╗  ██████╗██╗  ██╗",
    "██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝██║  ██║",
    "██████╔╝██████╔╝█████╗  ███████║██║     ███████║",
    "██╔══██╗██╔══██╗██╔══╝  ██╔══██║██║     ██╔══██║",
    "██████╔╝██║  ██║███████╗██║  ██║╚██████╗██║  ██║",
    "╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝",
]

def draw_title_art(stdscr, start_y):
    """Draw the DATA BREACH ascii art. Returns the row after the art."""
    for i, line in enumerate(TITLE_ART):
        safe_addstr(stdscr, start_y + i, center_x(stdscr, line), line,
                    curses.color_pair(GREEN) | curses.A_BOLD)
    for i, line in enumerate(TITLE_ART2):
        safe_addstr(stdscr, start_y + len(TITLE_ART) + i, center_x(stdscr, line), line,
                    curses.color_pair(GREEN) | curses.A_BOLD)
    return start_y + len(TITLE_ART) + len(TITLE_ART2)


def title_screen(stdscr):
    """Show the title splash with Matrix rain."""
    matrix_rain(stdscr, duration=3.0)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    start_y = max(1, h // 2 - len(TITLE_ART) - 3)
    art_end = draw_title_art(stdscr, start_y)

    subtitle = "[ CLASSIFIED TERMINAL v2.049 ]"
    safe_addstr(stdscr, art_end + 1, center_x(stdscr, subtitle), subtitle,
                curses.color_pair(GREEN) | curses.A_DIM)

    prompt = ">>> PRESS ANY KEY TO CONNECT <<<"
    safe_addstr(stdscr, art_end + 4, center_x(stdscr, prompt), prompt,
                curses.color_pair(GREEN) | curses.A_BLINK)

    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


# ─── MAIN MENU ──────────────────────────────────────────────────────────────

def main_menu(stdscr):
    """
    Main menu: NEW MISSION, DIFFICULTY, QUIT.
    Returns selected difficulty key (e.g. 'AGENT') or None to quit.
    """
    save_data = load_save()
    selected_diff = save_data.get("last_difficulty", "AGENT")
    cursor = 0  # 0=NEW MISSION, 1=DIFFICULTY, 2=QUIT
    menu_items = ["NEW MISSION", "DIFFICULTY", "QUIT"]

    stdscr.nodelay(False)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        draw_border(stdscr, GREEN)

        # Title art at top
        art_y = 2
        art_end = draw_title_art(stdscr, art_y)

        # Best ranks
        sy = art_end + 2
        safe_addstr(stdscr, sy, center_x(stdscr, "─── AGENT RECORDS ───"),
                    "─── AGENT RECORDS ───", curses.color_pair(GREEN) | curses.A_DIM)
        sy += 1
        has_records = False
        for dk in DIFFICULTY_ORDER:
            best = save_data.get("best", {}).get(dk)
            if best:
                has_records = True
                record = f"  {dk}: {best}"
                safe_addstr(stdscr, sy, center_x(stdscr, record), record,
                            curses.color_pair(CYAN))
                sy += 1
        if not has_records:
            msg = "  No records yet."
            safe_addstr(stdscr, sy, center_x(stdscr, msg), msg,
                        curses.color_pair(GREEN) | curses.A_DIM)
            sy += 1

        # Menu
        sy += 2
        for i, item in enumerate(menu_items):
            if item == "DIFFICULTY":
                label = f"DIFFICULTY: [ {selected_diff} ]"
            else:
                label = item

            if i == cursor:
                display = f"  ▶  {label}  "
                safe_addstr(stdscr, sy + i, center_x(stdscr, display), display,
                            curses.color_pair(GREEN_INV) | curses.A_BOLD)
            else:
                display = f"     {label}  "
                safe_addstr(stdscr, sy + i, center_x(stdscr, display), display,
                            curses.color_pair(GREEN))

        # Difficulty description
        desc_y = sy + len(menu_items) + 2
        diff_info = DIFFICULTIES[selected_diff]
        safe_addstr(stdscr, desc_y, center_x(stdscr, diff_info["description"]),
                    diff_info["description"], curses.color_pair(GREEN) | curses.A_DIM)
        time_str = f"Time: {diff_info['total_time']}s  |  Roulette: {diff_info['roulette_digits']} digits  |  Nodes: {diff_info['num_nodes']}  |  Retries: {diff_info['intel_attempts']}"
        safe_addstr(stdscr, desc_y + 1, center_x(stdscr, time_str),
                    time_str, curses.color_pair(GREEN) | curses.A_DIM)

        # Controls
        ctrl = "↑↓ Select  |  ENTER Confirm  |  ←→ Change Difficulty"
        safe_addstr(stdscr, min(desc_y + 4, h - 2), center_x(stdscr, ctrl), ctrl,
                    curses.color_pair(GREEN) | curses.A_DIM)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = (cursor - 1) % len(menu_items)
        elif key == curses.KEY_DOWN:
            cursor = (cursor + 1) % len(menu_items)
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            # Cycle difficulty
            idx = DIFFICULTY_ORDER.index(selected_diff)
            if key == curses.KEY_RIGHT:
                idx = (idx + 1) % len(DIFFICULTY_ORDER)
            else:
                idx = (idx - 1) % len(DIFFICULTY_ORDER)
            selected_diff = DIFFICULTY_ORDER[idx]
        elif key in (10, 13, ord(' ')):  # Enter/Space
            if cursor == 0:  # NEW MISSION
                save_data["last_difficulty"] = selected_diff
                save_game(save_data)
                return selected_diff
            elif cursor == 1:  # DIFFICULTY — cycle on enter too
                idx = DIFFICULTY_ORDER.index(selected_diff)
                idx = (idx + 1) % len(DIFFICULTY_ORDER)
                selected_diff = DIFFICULTY_ORDER[idx]
            elif cursor == 2:  # QUIT
                return None
        elif key == ord('q') or key == ord('Q'):
            return None


# ─── MISSION BRIEFING ────────────────────────────────────────────────────────

def mission_briefing(stdscr):
    """Display the mission briefing with typewriter effect."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    draw_border(stdscr, GREEN)

    safe_addstr(stdscr, 0, 3, "[ SECURE CHANNEL — HQ ]", curses.color_pair(GREEN) | curses.A_BOLD)

    lines = [
        ("INCOMING TRANSMISSION...", GREEN, 0.05),
        ("", 0, 0),
        ("FROM: DIRECTOR KNOX — CENTRAL COMMAND", CYAN, 0.03),
        ("TO:   AGENT CIPHER", CYAN, 0.03),
        ("RE:   OPERATION BLACKOUT — PRIORITY ALPHA", RED, 0.03),
        ("", 0, 0),
        ("Agent, we've intercepted a file containing details", GREEN, 0.02),
        ("of an imminent attack on civilian infrastructure.", GREEN, 0.02),
        ("", 0, 0),
        ("The file must be REDACTED before it can be leaked.", YELLOW, 0.02),
        ("Three security protocols guard the redaction system:", GREEN, 0.02),
        ("", 0, 0),
        ("  [1] ACCESS CODE ROULETTE — Crack the rotating cipher", GREEN, 0.02),
        ("  [2] MAZE EXTRACTION — Retrieve the decryption key", GREEN, 0.02),
        ("  [3] NODE LINK — Connect the network to finish redaction", GREEN, 0.02),
        ("", 0, 0),
        (f"You have {DIFF['total_time']} seconds. Fail, and the file goes public.", RED, 0.03),
        ("", 0, 0),
        ("Good luck, Agent. The world is counting on you.", GREEN, 0.03),
    ]

    y = 2
    for text, color, delay in lines:
        if y >= h - 2:
            break
        if text == "":
            y += 1
            continue
        typewriter(stdscr, y, 3, text, color, delay)
        y += 1

    y = min(y + 2, h - 2)
    prompt = ">>> PRESS ANY KEY TO BEGIN REDACTION <<<"
    safe_addstr(stdscr, y, center_x(stdscr, prompt), prompt,
                curses.color_pair(GREEN) | curses.A_BLINK)
    stdscr.refresh()
    stdscr.getch()


# ─── MINIGAME 1: CODE CRACKER ROULETTE ──────────────────────────────────────

def minigame_roulette(stdscr, start_time):
    """
    Roulette-style code cracker. 4 spinning digits — press SPACE/ENTER to
    lock each digit in place. Match the target code to win.
    """
    stdscr.clear()
    stdscr.nodelay(True)
    h, w = stdscr.getmaxyx()

    num_digits = DIFF["roulette_digits"]
    spd_lo, spd_hi = DIFF["roulette_speed"]
    target = [random.randint(0, 9) for _ in range(num_digits)]
    current = [random.randint(0, 9) for _ in range(num_digits)]
    locked = [False] * num_digits
    lock_idx = 0  # which digit we're locking next
    speeds = [random.uniform(spd_lo, spd_hi) for _ in range(num_digits)]
    last_tick = [time.time()] * num_digits
    win = False

    while True:
        elapsed = time.time() - start_time
        remaining = DIFF["total_time"] - elapsed
        if remaining <= 0:
            return False, remaining

        stdscr.erase()
        draw_border(stdscr, GREEN)
        draw_timer(stdscr, remaining, DIFF["total_time"])

        # Header
        header = "═══ PROTOCOL 1: ACCESS CODE ROULETTE ═══"
        safe_addstr(stdscr, 2, center_x(stdscr, header), header,
                    curses.color_pair(CYAN) | curses.A_BOLD)

        safe_addstr(stdscr, 4, 4, "Crack the access code. Press SPACE to lock each digit.",
                    curses.color_pair(GREEN))
        safe_addstr(stdscr, 5, 4, "Lock all digits to match the target code.",
                    curses.color_pair(GREEN) | curses.A_DIM)

        # Target code display
        target_str = "TARGET:  [ " + "  ".join(str(d) for d in target) + " ]"
        cy = 8
        safe_addstr(stdscr, cy, center_x(stdscr, target_str), target_str,
                    curses.color_pair(YELLOW) | curses.A_BOLD)

        # Spin unlocked digits
        now = time.time()
        for i in range(num_digits):
            if not locked[i]:
                if now - last_tick[i] > speeds[i]:
                    current[i] = (current[i] + 1) % 10
                    last_tick[i] = now

        # Current digits display
        cy += 3
        digit_display = "CURRENT: [ "
        safe_addstr(stdscr, cy, center_x(stdscr, target_str), "CURRENT: [ ",
                    curses.color_pair(GREEN) | curses.A_BOLD)

        base_x = center_x(stdscr, target_str) + len("CURRENT: [ ")
        for i in range(num_digits):
            ch = str(current[i])
            if locked[i]:
                if current[i] == target[i]:
                    color = curses.color_pair(CYAN) | curses.A_BOLD
                else:
                    color = curses.color_pair(RED) | curses.A_BOLD
            elif i == lock_idx:
                color = curses.color_pair(WHITE) | curses.A_BOLD | curses.A_REVERSE
            else:
                color = curses.color_pair(GREEN) | curses.A_DIM
            safe_addstr(stdscr, cy, base_x + i * 3, ch, color)

        safe_addstr(stdscr, cy, base_x + num_digits * 3 - 1, "]",
                    curses.color_pair(GREEN) | curses.A_BOLD)

        # Arrow indicator
        if lock_idx < num_digits:
            arrow_x = base_x + lock_idx * 3
            safe_addstr(stdscr, cy + 1, arrow_x, "▲", curses.color_pair(WHITE) | curses.A_BOLD)

        # Status
        cy += 4
        locked_count = sum(locked)
        status = f"DIGITS LOCKED: {locked_count}/{num_digits}"
        safe_addstr(stdscr, cy, center_x(stdscr, status), status,
                    curses.color_pair(GREEN))

        # Hint
        cy += 2
        if lock_idx < num_digits:
            hint = f"Locking digit {lock_idx + 1}... watch the spin and time your lock!"
            safe_addstr(stdscr, cy, center_x(stdscr, hint), hint,
                        curses.color_pair(GREEN) | curses.A_DIM)

        stdscr.refresh()
        time.sleep(0.03)

        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            return False, remaining
        elif key in (ord(' '), 10, 13):  # space or enter
            if lock_idx < num_digits:
                locked[lock_idx] = True
                if current[lock_idx] == target[lock_idx]:
                    # Correct digit
                    lock_idx += 1
                    if lock_idx == num_digits:
                        win = True
                else:
                    # Wrong digit — flash error
                    time.sleep(0.3)
                    for flash in range(3):
                        stdscr.erase()
                        msg = "WRONG DIGIT" if flash % 2 == 0 else ""
                        safe_addstr(stdscr, h // 2, center_x(stdscr, msg), msg,
                                    curses.color_pair(RED) | curses.A_BOLD)
                        stdscr.refresh()
                        time.sleep(0.15)

                    if DIFF["roulette_keep"]:
                        # RECRUIT/AGENT: keep correct digits, only unlock this one
                        locked[lock_idx] = False
                        current[lock_idx] = random.randint(0, 9)
                        # lock_idx stays the same — retry this digit
                    else:
                        # SHADOW/GHOST: full reset, new target code
                        target = [random.randint(0, 9) for _ in range(num_digits)]
                        current = [random.randint(0, 9) for _ in range(num_digits)]
                        locked = [False] * num_digits
                        lock_idx = 0
                        speeds = [random.uniform(spd_lo, spd_hi) for _ in range(num_digits)]

        if win:
            # Success animation
            stdscr.nodelay(False)
            for flash in range(4):
                stdscr.erase()
                draw_border(stdscr, CYAN)
                msg = ">>> ACCESS CODE ACCEPTED <<<"
                safe_addstr(stdscr, h // 2, center_x(stdscr, msg), msg,
                            curses.color_pair(CYAN) | curses.A_BOLD)
                msg2 = "Protocol 1 complete — Section redacted"
                safe_addstr(stdscr, h // 2 + 1, center_x(stdscr, msg2), msg2,
                            curses.color_pair(GREEN))
                stdscr.refresh()
                time.sleep(0.4)
            time.sleep(0.5)
            return True, DIFF["total_time"] - (time.time() - start_time)

    return False, 0


# ─── MINIGAME 2: MAZE ───────────────────────────────────────────────────────

def generate_maze(mw, mh):
    """Generate a maze using recursive backtracker. Returns 2D grid."""
    # Each cell: walls = [top, right, bottom, left]
    cells = [[True] * (mw * mh) for _ in range(4)]  # not great, let's use dict
    visited = [[False] * mw for _ in range(mh)]
    walls = {}
    for r in range(mh):
        for c in range(mw):
            walls[(r, c)] = [True, True, True, True]  # top right bottom left

    stack = [(0, 0)]
    visited[0][0] = True

    while stack:
        r, c = stack[-1]
        neighbors = []
        for dr, dc, wall_self, wall_neighbor in [(-1, 0, 0, 2), (0, 1, 1, 3), (1, 0, 2, 0), (0, -1, 3, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < mh and 0 <= nc < mw and not visited[nr][nc]:
                neighbors.append((nr, nc, wall_self, wall_neighbor))
        if neighbors:
            nr, nc, ws, wn = random.choice(neighbors)
            walls[(r, c)][ws] = False
            walls[(nr, nc)][wn] = False
            visited[nr][nc] = True
            stack.append((nr, nc))
        else:
            stack.pop()

    # Convert to character grid
    gh = mh * 2 + 1
    gw = mw * 2 + 1
    grid = [['█'] * gw for _ in range(gh)]

    for r in range(mh):
        for c in range(mw):
            # Cell center
            grid[r * 2 + 1][c * 2 + 1] = ' '
            # Passages
            if not walls[(r, c)][0]:  # top
                grid[r * 2][c * 2 + 1] = ' '
            if not walls[(r, c)][1]:  # right
                grid[r * 2 + 1][c * 2 + 2] = ' '
            if not walls[(r, c)][2]:  # bottom
                grid[(r + 1) * 2][c * 2 + 1] = ' '
            if not walls[(r, c)][3]:  # left
                grid[r * 2 + 1][c * 2] = ' '

    return grid


def minigame_maze(stdscr, start_time):
    """Maze game: navigate to find the key, then reach the exit."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    target_w, target_h = DIFF["maze_size"]
    maze_cells_w = min(target_w, (w - 20) // 4)
    maze_cells_h = min(target_h, (h - 10) // 3)
    maze_cells_w = max(5, maze_cells_w)
    maze_cells_h = max(4, maze_cells_h)

    grid = generate_maze(maze_cells_w, maze_cells_h)
    gh = len(grid)
    gw = len(grid[0])

    # Player starts top-left
    player = [1, 1]
    # Key in a random open cell in bottom-right quadrant
    key_placed = False
    has_key = False
    key_pos = [0, 0]

    attempts = 0
    while not key_placed and attempts < 200:
        kr = random.randint(gh // 2, gh - 2)
        kc = random.randint(gw // 2, gw - 2)
        if grid[kr][kc] == ' ':
            key_pos = [kr, kc]
            key_placed = True
        attempts += 1
    if not key_placed:
        key_pos = [gh - 2, gw - 2]

    # Exit at bottom-right
    exit_pos = [gh - 2, gw - 2]
    # Make sure exit is open
    grid[exit_pos[0]][exit_pos[1]] = ' '

    stdscr.nodelay(True)

    while True:
        elapsed = time.time() - start_time
        remaining = DIFF["total_time"] - elapsed
        if remaining <= 0:
            return False, remaining

        stdscr.erase()
        draw_border(stdscr, GREEN)
        draw_timer(stdscr, remaining, DIFF["total_time"])

        header = "═══ PROTOCOL 2: MAZE EXTRACTION ═══"
        safe_addstr(stdscr, 2, center_x(stdscr, header), header,
                    curses.color_pair(CYAN) | curses.A_BOLD)

        if not has_key:
            inst = "Find the KEY [K] then reach the EXIT [E]"
        else:
            inst = "KEY acquired! Navigate to the EXIT [E]"
        safe_addstr(stdscr, 4, center_x(stdscr, inst), inst,
                    curses.color_pair(YELLOW if has_key else GREEN))

        # Draw maze
        maze_start_y = 6
        maze_start_x = max(2, center_x(stdscr, "X" * gw))
        fog = DIFF["maze_fog"]

        for r in range(gh):
            if maze_start_y + r >= h - 1:
                break
            for c in range(gw):
                if maze_start_x + c >= w - 1:
                    break

                py, px = maze_start_y + r, maze_start_x + c

                # Fog of war: only draw cells within radius of player
                if fog > 0:
                    dist = abs(r - player[0]) + abs(c - player[1])
                    if dist > fog:
                        safe_addstr(stdscr, py, px, " ", 0)
                        continue

                if [r, c] == player:
                    safe_addstr(stdscr, py, px, "@",
                                curses.color_pair(WHITE) | curses.A_BOLD)
                elif [r, c] == key_pos and not has_key:
                    safe_addstr(stdscr, py, px, "K",
                                curses.color_pair(YELLOW) | curses.A_BOLD)
                elif [r, c] == exit_pos:
                    if has_key:
                        safe_addstr(stdscr, py, px, "E",
                                    curses.color_pair(CYAN) | curses.A_BOLD | curses.A_BLINK)
                    else:
                        safe_addstr(stdscr, py, px, "E",
                                    curses.color_pair(RED) | curses.A_DIM)
                elif grid[r][c] == '█':
                    safe_addstr(stdscr, py, px, "█",
                                curses.color_pair(GREEN) | curses.A_DIM)
                else:
                    safe_addstr(stdscr, py, px, "·",
                                curses.color_pair(GREEN) | curses.A_DIM)

        # Legend
        ly = maze_start_y + gh + 1
        if ly < h - 1:
            safe_addstr(stdscr, ly, 4, "@ = You   K = Key   E = Exit   Arrow keys to move",
                        curses.color_pair(GREEN) | curses.A_DIM)

        stdscr.refresh()
        time.sleep(0.03)

        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            return False, remaining

        dr, dc = 0, 0
        if key == curses.KEY_UP:
            dr = -1
        elif key == curses.KEY_DOWN:
            dr = 1
        elif key == curses.KEY_LEFT:
            dc = -1
        elif key == curses.KEY_RIGHT:
            dc = 1

        if dr != 0 or dc != 0:
            nr, nc = player[0] + dr, player[1] + dc
            if 0 <= nr < gh and 0 <= nc < gw and grid[nr][nc] != '█':
                player = [nr, nc]

                # Check key pickup
                if player == key_pos and not has_key:
                    has_key = True

                # Check exit
                if player == exit_pos and has_key:
                    stdscr.nodelay(False)
                    for flash in range(4):
                        stdscr.erase()
                        draw_border(stdscr, CYAN)
                        msg = ">>> DECRYPTION KEY EXTRACTED <<<"
                        safe_addstr(stdscr, h // 2, center_x(stdscr, msg), msg,
                                    curses.color_pair(CYAN) | curses.A_BOLD)
                        msg2 = "Protocol 2 complete — Section redacted"
                        safe_addstr(stdscr, h // 2 + 1, center_x(stdscr, msg2), msg2,
                                    curses.color_pair(GREEN))
                        stdscr.refresh()
                        time.sleep(0.4)
                    time.sleep(0.5)
                    return True, DIFF["total_time"] - (time.time() - start_time)


# ─── MINIGAME 3: CONNECT THE NODES ──────────────────────────────────────────

def _segments_intersect(p1, p2, p3, p4):
    """Check if grid segment p1-p2 crosses segment p3-p4.
    Handles axis-aligned (collinear) overlaps common in grid movement.
    Shared endpoints are allowed (adjacent segments don't count)."""
    # Skip if they share an endpoint
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False

    # Check if new position p2 lands exactly on segment p3-p4
    # (most common grid case: stepping onto an existing trail segment)
    def on_segment(a, b, p):
        """Is point p on segment a-b? (grid/integer coords)"""
        # Check collinear via cross product
        cross = (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])
        if cross != 0:
            return False
        # Check within bounding box
        return (min(a[0],b[0]) <= p[0] <= max(a[0],b[0]) and
                min(a[1],b[1]) <= p[1] <= max(a[1],b[1]))

    # If the destination point lies on an existing segment, that's a cross
    if on_segment(p3, p4, p2):
        return True

    # Standard CCW intersection test for non-collinear crossing
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    if (ccw(p1,p3,p4) != ccw(p2,p3,p4)) and (ccw(p1,p2,p3) != ccw(p1,p2,p4)):
        return True

    return False


def minigame_connect(stdscr, start_time):
    """Connect numbered nodes in sequence by navigating to each one."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    stdscr.nodelay(True)

    # Create grid of nodes
    grid_h = min(15, h - 10)
    grid_w = min(40, w - 20)

    num_nodes = DIFF["num_nodes"]
    nodes = []
    used_positions = set()

    for i in range(num_nodes):
        attempts = 0
        while attempts < 100:
            ny = random.randint(1, grid_h - 2)
            nx = random.randint(1, grid_w - 2)
            too_close = False
            for ey, ex in nodes:
                min_dist = 3 if num_nodes > 8 else 4
                if abs(ny - ey) + abs(nx - ex) < min_dist:
                    too_close = True
                    break
            if not too_close and (ny, nx) not in used_positions:
                nodes.append((ny, nx))
                used_positions.add((ny, nx))
                break
            attempts += 1
        else:
            nodes.append((random.randint(1, grid_h - 2), random.randint(1, grid_w - 2)))

    # Player starts at node 0
    player = list(nodes[0])
    current_target = 1
    connected = [0]
    # Trail: list of positions forming the current path from last connected node
    current_trail = [tuple(player)]
    # Locked trails: list of trails between connected nodes (frozen, can't cross)
    locked_trails = []
    # All trail positions for drawing
    all_trail_pos = {tuple(player)}

    cross_reset = DIFF["node_cross_reset"]
    warning_msg = ""
    warning_time = 0

    offset_y = 6
    offset_x = max(2, (w - grid_w) // 2)

    while True:
        elapsed = time.time() - start_time
        remaining = DIFF["total_time"] - elapsed
        if remaining <= 0:
            return False, remaining

        stdscr.erase()
        draw_border(stdscr, GREEN)
        draw_timer(stdscr, remaining, DIFF["total_time"])

        header = "═══ PROTOCOL 3: NODE LINK ═══"
        safe_addstr(stdscr, 2, center_x(stdscr, header), header,
                    curses.color_pair(CYAN) | curses.A_BOLD)

        target_label = format(current_target, 'X') if current_target >= 10 else str(current_target)
        inst = f"Connect to node {target_label} — navigate with arrow keys"
        safe_addstr(stdscr, 4, center_x(stdscr, inst), inst,
                    curses.color_pair(YELLOW))

        # Draw locked trails (between connected nodes)
        for trail in locked_trails:
            for ty, tx in trail:
                py, px = offset_y + ty, offset_x + tx
                safe_addstr(stdscr, py, px, "·", curses.color_pair(CYAN) | curses.A_DIM)

        # Draw current trail
        for ty, tx in current_trail:
            py, px = offset_y + ty, offset_x + tx
            safe_addstr(stdscr, py, px, "·", curses.color_pair(GREEN))

        # Draw nodes (use hex for 10+: A, B, C...)
        for i, (ny, nx) in enumerate(nodes):
            py, px = offset_y + ny, offset_x + nx
            label = format(i, 'X') if i >= 10 else str(i)
            if i in connected:
                safe_addstr(stdscr, py, px, label,
                            curses.color_pair(CYAN) | curses.A_BOLD)
            elif i == current_target:
                safe_addstr(stdscr, py, px, label,
                            curses.color_pair(YELLOW) | curses.A_BOLD | curses.A_BLINK)
            else:
                safe_addstr(stdscr, py, px, label,
                            curses.color_pair(GREEN) | curses.A_DIM)

        # Draw player
        py, px = offset_y + player[0], offset_x + player[1]
        safe_addstr(stdscr, py, px, "@", curses.color_pair(WHITE) | curses.A_BOLD)

        # Progress
        progress = f"NODES LINKED: {len(connected)}/{num_nodes}"
        safe_addstr(stdscr, offset_y + grid_h + 1, center_x(stdscr, progress), progress,
                    curses.color_pair(GREEN))

        # Warning message (fades after 1s)
        if warning_msg and time.time() - warning_time < 1.0:
            safe_addstr(stdscr, offset_y + grid_h + 2, center_x(stdscr, warning_msg),
                        warning_msg, curses.color_pair(RED) | curses.A_BOLD)

        stdscr.refresh()
        time.sleep(0.03)

        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            return False, remaining

        dr, dc = 0, 0
        if key == curses.KEY_UP:
            dr = -1
        elif key == curses.KEY_DOWN:
            dr = 1
        elif key == curses.KEY_LEFT:
            dc = -1
        elif key == curses.KEY_RIGHT:
            dc = 1

        if dr != 0 or dc != 0:
            nr, nc = player[0] + dr, player[1] + dc
            if 0 <= nr < grid_h and 0 <= nc < grid_w:
                new_pos = (nr, nc)
                old_pos = (player[0], player[1])

                # Check intersection with locked trails (completed connections)
                crosses_locked = False
                for trail in locked_trails:
                    for ti in range(len(trail) - 1):
                        if _segments_intersect(old_pos, new_pos, trail[ti], trail[ti + 1]):
                            crosses_locked = True
                            break
                    if crosses_locked:
                        break

                if crosses_locked:
                    # All difficulties: can't cross locked trails
                    if cross_reset:
                        warning_msg = "!! LINE CROSSED — RESET TO LAST NODE !!"
                        warning_time = time.time()
                        last_node = nodes[connected[-1]]
                        player = list(last_node)
                        for pos in current_trail:
                            all_trail_pos.discard(pos)
                        current_trail = [tuple(player)]
                        all_trail_pos.add(tuple(player))
                    else:
                        warning_msg = "!! CAN'T CROSS LINES !!"
                        warning_time = time.time()
                    continue

                # SHADOW/GHOST: stepping on own trail resets to last node
                if cross_reset and new_pos in set(current_trail[:-1]):
                    is_node = any(new_pos == (ny, nx) for ny, nx in nodes)
                    if not is_node:
                        warning_msg = "!! TRAIL CROSSED — RESET !!"
                        warning_time = time.time()
                        last_node = nodes[connected[-1]]
                        player = list(last_node)
                        for pos in current_trail:
                            all_trail_pos.discard(pos)
                        current_trail = [tuple(player)]
                        all_trail_pos.add(tuple(player))
                        continue

                player = [nr, nc]
                current_trail.append(tuple(player))
                all_trail_pos.add(tuple(player))

                # Check if reached target node
                if current_target < num_nodes:
                    ty, tx = nodes[current_target]
                    if player[0] == ty and player[1] == tx:
                        connected.append(current_target)
                        # Lock the current trail
                        locked_trails.append(list(current_trail))
                        current_target += 1
                        # Start new trail from this node
                        current_trail = [tuple(player)]

                        if current_target >= num_nodes:
                            stdscr.nodelay(False)
                            for flash in range(4):
                                stdscr.erase()
                                draw_border(stdscr, CYAN)
                                msg = ">>> ALL NODES LINKED <<<"
                                safe_addstr(stdscr, h // 2, center_x(stdscr, msg), msg,
                                            curses.color_pair(CYAN) | curses.A_BOLD)
                                msg2 = "Protocol 3 complete — Final section redacted"
                                safe_addstr(stdscr, h // 2 + 1, center_x(stdscr, msg2), msg2,
                                            curses.color_pair(GREEN))
                                stdscr.refresh()
                                time.sleep(0.4)
                            time.sleep(0.5)
                            return True, DIFF["total_time"] - (time.time() - start_time)


# ─── CURSES TEXT INPUT (time-aware) ──────────────────────────────────────────

def curses_input_timed(stdscr, y, x, deadline, max_len=30, color=GREEN):
    """
    Read a string with a running deadline. Returns (string, timed_out).
    Uses halfdelay so the timer keeps ticking visually.
    """
    curses.curs_set(1)
    curses.halfdelay(2)  # 200ms timeout on getch
    buf = []
    timed_out = False

    while True:
        if time.time() >= deadline:
            timed_out = True
            break

        display = "".join(buf)
        safe_addstr(stdscr, y, x, display + " " * (max_len - len(buf) + 1),
                    curses.color_pair(color) | curses.A_BOLD)
        try:
            stdscr.move(y, x + len(buf))
        except curses.error:
            pass

        # Update timer on row 0
        remaining = max(0, deadline - time.time())
        draw_timer(stdscr, remaining, DIFF["total_time"] + DIFF["intel_bonus"])
        stdscr.refresh()

        try:
            key = stdscr.getch()
        except curses.error:
            continue
        if key == -1:
            continue

        if key in (10, 13):  # Enter
            break
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if buf:
                buf.pop()
        elif key == 27:
            break
        elif 32 <= key <= 126 and len(buf) < max_len:
            buf.append(chr(key))

    curses.curs_set(0)
    curses.halfdelay(1)  # reset
    try:
        curses.nocbreak()
        curses.cbreak()
    except curses.error:
        pass
    return "".join(buf), timed_out


def flash_error(stdscr, y, x):
    """Quick red error buzz effect."""
    msg = "!! ACCESS DENIED !!"
    safe_addstr(stdscr, y, x, msg, curses.color_pair(RED_INV) | curses.A_BOLD)
    stdscr.refresh()
    curses.flash()
    time.sleep(0.3)
    safe_addstr(stdscr, y, x, " " * len(msg), 0)
    stdscr.refresh()


# ─── INTEL INPUT SCREEN ─────────────────────────────────────────────────────

MAX_ATTEMPTS = 3  # default, overridden by DIFF at runtime

def draw_intel_screen(stdscr, stages_done, deadline, questions, answers, attempts_left, cursor, input_mode, input_buf):
    """Redraw the full intel screen. Called every frame."""
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    draw_border(stdscr, GREEN)

    remaining = max(0, deadline - time.time())
    draw_timer(stdscr, remaining, DIFF["total_time"] + DIFF["intel_bonus"])

    header = "═══ INTEL REPORT — TRANSMIT TO HQ ═══"
    safe_addstr(stdscr, 1, center_x(stdscr, header), header,
                curses.color_pair(CYAN) | curses.A_BOLD)

    # File reference
    draw_file_status(stdscr, 3, stages_done)
    file_end_y = 3 + len(FILE_HEADER) + len(FILE_REVEALED) + 3  # header+data+sep+status+bottom

    safe_addstr(stdscr, file_end_y, 4, "Select a field with ↑↓, press ENTER to answer. ESC when done.",
                curses.color_pair(GREEN) | curses.A_DIM)

    # Questions list
    list_y = file_end_y + 1
    for i, (question, intel_key) in enumerate(questions):
        if list_y + i >= h - 2:
            break
        row_y = list_y + i

        # Selector arrow
        if i == cursor and not input_mode:
            safe_addstr(stdscr, row_y, 2, "▶", curses.color_pair(WHITE) | curses.A_BOLD)
        else:
            safe_addstr(stdscr, row_y, 2, " ", 0)

        # Short label from question (extract the CAPS word)
        label = question.split("?")[0]
        # Truncate for display
        max_label = 38
        if len(label) > max_label:
            label = label[:max_label - 1] + "…"

        # Color based on state
        ans = answers[i]
        if ans is not None:
            # Answered — show question and answer
            safe_addstr(stdscr, row_y, 4, f"{label}?",
                        curses.color_pair(CYAN) | curses.A_DIM)
            safe_addstr(stdscr, row_y, 4 + max_label + 3, ans,
                        curses.color_pair(CYAN) | curses.A_BOLD)
        elif attempts_left[i] <= 0:
            # Out of attempts
            safe_addstr(stdscr, row_y, 4, f"{label}?",
                        curses.color_pair(RED) | curses.A_DIM)
            safe_addstr(stdscr, row_y, 4 + max_label + 3, "FAILED",
                        curses.color_pair(RED))
        elif i == cursor and input_mode:
            # Currently being answered
            safe_addstr(stdscr, row_y, 4, f"{label}?",
                        curses.color_pair(YELLOW) | curses.A_BOLD)
            prompt = ">>> "
            safe_addstr(stdscr, row_y, 4 + max_label + 3, prompt,
                        curses.color_pair(GREEN) | curses.A_BOLD)
            display = "".join(input_buf)
            safe_addstr(stdscr, row_y, 4 + max_label + 3 + len(prompt),
                        display + " " * (20 - len(display)),
                        curses.color_pair(WHITE) | curses.A_BOLD)
            try:
                stdscr.move(row_y, 4 + max_label + 3 + len(prompt) + len(display))
            except curses.error:
                pass
        else:
            # Unanswered
            att = attempts_left[i]
            att_str = f"[{att} left]" if att < DIFF["intel_attempts"] else ""
            safe_addstr(stdscr, row_y, 4, f"{label}?",
                        curses.color_pair(YELLOW))
            safe_addstr(stdscr, row_y, 4 + max_label + 3, f"_______________  {att_str}",
                        curses.color_pair(GREEN) | curses.A_DIM)

    # Correct count
    answered = sum(1 for a in answers if a is not None)
    total = len(questions)
    status_y = min(list_y + len(questions) + 1, h - 2)
    safe_addstr(stdscr, status_y, 4, f"TRANSMITTED: {answered}/{total}",
                curses.color_pair(GREEN) | curses.A_BOLD)


def intel_input_screen(stdscr, stages_done, start_time):
    """
    Interactive intel input. File visible, all questions listed.
    Player picks which to answer with arrow keys. 3 attempts per question.
    Timer keeps running. +30s bonus if all minigames completed.
    Returns (correct_count, total_questions, time_remaining).
    """
    h, w = stdscr.getmaxyx()

    bonus = DIFF["intel_bonus"] if stages_done == 3 else 0
    deadline = start_time + DIFF["total_time"] + bonus

    questions = DEBRIEF_QUESTIONS
    total = len(questions)
    answers = [None] * total          # None = unanswered, string = accepted answer
    max_att = DIFF["intel_attempts"]
    attempts_left = [max_att] * total
    correct = 0
    cursor = 0
    input_mode = False
    input_buf = []

    curses.halfdelay(2)  # 200ms getch timeout so timer updates

    while True:
        if time.time() >= deadline:
            break

        # Check if all answered or all exhausted
        all_done = all(a is not None or att <= 0 for a, att in zip(answers, attempts_left))
        if all_done:
            break

        if input_mode:
            curses.curs_set(1)
        else:
            curses.curs_set(0)

        draw_intel_screen(stdscr, stages_done, deadline, questions, answers,
                          attempts_left, cursor, input_mode, input_buf)
        stdscr.refresh()

        try:
            key = stdscr.getch()
        except curses.error:
            continue
        if key == -1:
            continue

        if input_mode:
            # Typing an answer
            if key in (10, 13):  # Enter — submit
                answer = "".join(input_buf).strip()
                intel_key = questions[cursor][1]
                expected = INTEL[intel_key].strip().lower()

                if answer.lower() == expected:
                    answers[cursor] = answer
                    correct += 1
                    input_mode = False
                    input_buf = []
                else:
                    attempts_left[cursor] -= 1
                    input_buf = []
                    if attempts_left[cursor] <= 0:
                        input_mode = False
                    else:
                        flash_error(stdscr, cursor + 3 + len(FILE_HEADER) + len(FILE_REVEALED) + 4, 4)
            elif key == 27:  # Escape — cancel input, go back to selection
                input_mode = False
                input_buf = []
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if input_buf:
                    input_buf.pop()
            elif 32 <= key <= 126 and len(input_buf) < 25:
                input_buf.append(chr(key))
        else:
            # Selection mode
            if key == curses.KEY_UP:
                cursor = (cursor - 1) % total
            elif key == curses.KEY_DOWN:
                cursor = (cursor + 1) % total
            elif key in (10, 13):  # Enter — start answering selected question
                if answers[cursor] is None and attempts_left[cursor] > 0:
                    input_mode = True
                    input_buf = []
            elif key == 27:  # Escape — done, submit what we have
                break

    curses.curs_set(0)
    # Reset to normal input mode
    try:
        curses.nocbreak()
        curses.cbreak()
    except curses.error:
        pass

    time_remaining = max(0, deadline - time.time())
    return correct, total, time_remaining


# ─── END SCREENS ─────────────────────────────────────────────────────────────

def debrief_screen(stdscr, correct, total, stages_done, time_remaining):
    """HQ debrief based on performance."""
    stdscr.clear()
    stdscr.nodelay(False)
    h, w = stdscr.getmaxyx()

    # Determine rating
    pct = correct / total if total > 0 else 0
    redaction_pct = stages_done / 3

    if pct >= 0.9 and redaction_pct == 1.0:
        rank = "LEGENDARY"
        rank_color = CYAN
        lines = [
            "Outstanding work, Agent Cipher.",
            "Every piece of intel was reported accurately.",
            "The attack has been neutralized. Zero civilian casualties.",
            "You are hereby awarded the Director's Medal of Excellence.",
            "The world owes you a debt it can never repay.",
        ]
    elif pct >= 0.7 and redaction_pct == 1.0:
        rank = "EXCELLENT"
        rank_color = CYAN
        lines = [
            "Strong performance, Agent.",
            "Most intel was reported correctly. The attack was thwarted.",
            "Minor gaps in your report, but field teams filled them in.",
            "HQ commends your service. Well done.",
        ]
    elif pct >= 0.5:
        rank = "ADEQUATE"
        rank_color = YELLOW
        lines = [
            "The mission is... partially successful, Agent.",
            "Your intel had significant gaps.",
            "Field teams scrambled to compensate. Some damage occurred.",
            "HQ expects better. Report for additional training.",
        ]
    elif pct >= 0.25:
        rank = "POOR"
        rank_color = RED
        lines = [
            "This is a disappointing result, Agent Cipher.",
            "Critical intel was missing or incorrect.",
            "The attack caused significant damage before responders arrived.",
            "You are suspended pending review. Report to Internal Affairs.",
        ]
    else:
        rank = "CATASTROPHIC FAILURE"
        rank_color = RED
        lines = [
            "Agent Cipher... this is a disaster.",
            "Almost none of the intel was usable.",
            "The attack succeeded. Casualties are mounting.",
            "Your clearance is revoked effective immediately.",
            "This will be investigated.",
        ]

    # Determine if overall win or loss
    mission_success = pct >= 0.5 and redaction_pct >= 1.0

    if mission_success:
        matrix_rain(stdscr, duration=1.0)

    stdscr.clear()
    border_color = rank_color if mission_success else RED
    draw_border(stdscr, border_color)

    safe_addstr(stdscr, 0, 3, "[ HQ DEBRIEF — CLASSIFIED ]",
                curses.color_pair(border_color) | curses.A_BOLD)

    sy = 2
    # Result header
    if mission_success:
        result_title = "M I S S I O N   S U C C E S S"
        safe_addstr(stdscr, sy, center_x(stdscr, result_title), result_title,
                    curses.color_pair(CYAN) | curses.A_BOLD)
    else:
        result_title = "M I S S I O N   F A I L E D"
        safe_addstr(stdscr, sy, center_x(stdscr, result_title), result_title,
                    curses.color_pair(RED) | curses.A_BOLD)

    sy += 2
    # Stats box
    safe_addstr(stdscr, sy, 4, "╔═══════════════════════════════════════╗",
                curses.color_pair(GREEN))
    sy += 1
    safe_addstr(stdscr, sy, 4, f"║  DIFFICULTY:          {DIFF['label']:<17s}║",
                curses.color_pair(GREEN))
    sy += 1
    safe_addstr(stdscr, sy, 4, f"║  REDACTION PROGRESS:  {int(redaction_pct * 100):>3d}%            ║",
                curses.color_pair(GREEN))
    sy += 1
    safe_addstr(stdscr, sy, 4, f"║  INTEL ACCURACY:      {correct}/{total} correct        ║",
                curses.color_pair(GREEN))
    sy += 1
    safe_addstr(stdscr, sy, 4, f"║  TIME REMAINING:      {max(0, int(time_remaining)):>3d}s             ║",
                curses.color_pair(GREEN))
    sy += 1
    rank_line = f"║  AGENT RATING:        {rank:<17s}║"
    safe_addstr(stdscr, sy, 4, rank_line,
                curses.color_pair(rank_color) | curses.A_BOLD)
    sy += 1
    safe_addstr(stdscr, sy, 4, "╚═══════════════════════════════════════╝",
                curses.color_pair(GREEN))

    # Debrief text
    sy += 2
    safe_addstr(stdscr, sy, 4, "DIRECTOR KNOX:",
                curses.color_pair(CYAN) | curses.A_BOLD)
    sy += 1
    for line in lines:
        if sy >= h - 3:
            break
        safe_addstr(stdscr, sy, 4, f"  {line}", curses.color_pair(GREEN))
        sy += 1

    # Prompt
    prompt = ">>> PRESS ANY KEY TO RETURN TO HQ <<<"
    safe_addstr(stdscr, min(sy + 2, h - 2), center_x(stdscr, prompt), prompt,
                curses.color_pair(border_color) | curses.A_BLINK)

    stdscr.refresh()
    stdscr.getch()
    return rank


# ─── TRANSITION SCREEN ───────────────────────────────────────────────────────

def transition_screen(stdscr, stage_num, stage_name, start_time):
    """Brief transition between minigames showing file redaction progress."""
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    draw_border(stdscr, GREEN)

    remaining = DIFF["total_time"] - (time.time() - start_time)
    draw_timer(stdscr, remaining, DIFF["total_time"])

    sy = 3
    draw_file_status(stdscr, sy, stage_num)

    file_lines = len(FILE_HEADER) + len(FILE_REVEALED) + 3  # +3 for sep, status, bottom
    sy += file_lines + 2
    msg = f"Initiating Protocol {stage_num + 1}: {stage_name}..."
    if sy < h - 2:
        safe_addstr(stdscr, sy, center_x(stdscr, msg), msg,
                    curses.color_pair(YELLOW) | curses.A_BOLD)

    stdscr.refresh()
    time.sleep(2.0)


# ─── MAIN GAME LOOP ─────────────────────────────────────────────────────────

RANK_ORDER = ["CATASTROPHIC FAILURE", "POOR", "ADEQUATE", "EXCELLENT", "LEGENDARY"]

def run_mission(stdscr):
    """Run a single mission. Returns the rank string."""
    global DIFF

    mission_briefing(stdscr)

    # Start the clock
    start_time = time.time()
    stages_done = 0

    # Minigame 1: Roulette
    transition_screen(stdscr, 0, "ACCESS CODE ROULETTE", start_time)
    success, remaining = minigame_roulette(stdscr, start_time)
    if success and remaining > 0:
        stages_done = 1

    # Minigame 2: Maze (only if time remains)
    if remaining > 0:
        transition_screen(stdscr, stages_done, "MAZE EXTRACTION", start_time)
        success, remaining = minigame_maze(stdscr, start_time)
        if success and remaining > 0:
            stages_done = 2

    # Minigame 3: Connect the Nodes (only if time remains)
    if remaining > 0:
        transition_screen(stdscr, stages_done, "NODE LINK", start_time)
        success, remaining = minigame_connect(stdscr, start_time)
        if success and remaining > 0:
            stages_done = 3

    # Intel input phase — timer keeps running
    transition_screen(stdscr, stages_done, "INTEL REPORT", start_time)
    correct, total, time_remaining = intel_input_screen(stdscr, stages_done, start_time)

    # Debrief
    rank = debrief_screen(stdscr, correct, total, stages_done, time_remaining)
    return rank


def main(stdscr):
    """Main game function — menu loop."""
    global DIFF

    curses.curs_set(0)
    init_colors()
    stdscr.clear()

    # Check minimum terminal size
    h, w = stdscr.getmaxyx()
    if h < 24 or w < 60:
        stdscr.addstr(0, 0, f"Terminal too small ({w}x{h}). Need at least 60x24.")
        stdscr.addstr(1, 0, "Resize your terminal and try again.")
        stdscr.refresh()
        stdscr.getch()
        return

    # Title splash (only once)
    title_screen(stdscr)

    # Game loop — keep returning to menu after each mission
    while True:
        difficulty_key = main_menu(stdscr)
        if difficulty_key is None:
            break  # QUIT

        DIFF = DIFFICULTIES[difficulty_key]

        rank = run_mission(stdscr)

        # Save best rank
        if rank:
            save_data = load_save()
            save_data["last_difficulty"] = difficulty_key
            current_best = save_data.get("best", {}).get(difficulty_key)
            if current_best is None or RANK_ORDER.index(rank) > RANK_ORDER.index(current_best):
                save_data.setdefault("best", {})[difficulty_key] = rank
            save_game(save_data)


if __name__ == "__main__":
    curses.wrapper(main)
