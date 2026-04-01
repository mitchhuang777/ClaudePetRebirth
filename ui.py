import os
import sys
import time

import lang
from lang import t, species_name
from constants import RARITY_STARS, RARITY_COLORS, STAT_NAMES, DEFAULT_PERSONALITIES
from sprites import render_sprite, BODIES


def display_width(s):
    """Calculate display width accounting for CJK double-width characters."""
    width = 0
    for ch in s:
        if ord(ch) > 0x7F:
            width += 2
        else:
            width += 1
    return width


def pad_right(s, total_width):
    """Pad string to total_width columns, accounting for CJK characters."""
    current = display_width(s)
    if current >= total_width:
        return s
    return s + " " * (total_width - current)


# ─── ANSI Colors ───

COLORS = {
    "white": "\033[37m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "purple": "\033[38;5;135m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "red": "\033[31m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def color(text, c):
    return f"{COLORS.get(c, '')}{text}{COLORS['reset']}"


def rarity_color(text, rarity):
    return color(text, RARITY_COLORS.get(rarity, "white"))


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ─── Display ───

def stat_bar(value, width=20):
    filled = min(width, round(value / 100 * width))
    empty = width - filled
    return color("\u2588" * filled, "cyan") + color("\u2591" * empty, "dim")


def display_pet(pet, show_index=None, total=None, show_stats=True):
    """Display a pet with its sprite, stats, and info."""
    rarity = pet["rarity"]
    stars = RARITY_STARS[rarity]
    shiny_tag = color(" SHINY!", "yellow") if pet["shiny"] else ""

    # Header
    sp = species_name(pet["species"]).upper()
    header = f"  {sp} {stars}{shiny_tag}"
    if show_index is not None and total is not None:
        header = f"  [{show_index}/{total}] {sp} {stars}{shiny_tag}"
    print(rarity_color(header, rarity))

    # Info line
    info = f"  {t('rarity')}: {t(rarity)}  |  {t('eyes')}: {pet['eye']}  |  {t('hat')}: {pet['hat']}"
    print(rarity_color(info, rarity))
    print()

    # Sprite
    lines = render_sprite(pet, frame=0)
    for line in lines:
        print(rarity_color(f"    {line}", rarity))
    print()

    if show_stats:
        # Stats
        print(color(f"  {t('stats')}:", "bold"))
        best_stat = max(pet["stats"], key=lambda k: pet["stats"][k])
        worst_stat = min(pet["stats"], key=lambda k: pet["stats"][k])
        for name in STAT_NAMES:
            value = pet["stats"][name]
            bar = stat_bar(value)
            display_name = pad_right(t(name), 10)
            label = f"    {display_name} {bar} {value:>3}"
            if name == best_stat:
                print(color(label, "green"))
            elif name == worst_stat:
                print(color(label, "red"))
            else:
                print(label)
        print()

    # Personality
    personality = DEFAULT_PERSONALITIES.get(pet["species"], "")
    if personality:
        print(color(f"  \"{personality}\"", "dim"))
        print()


def display_banner():
    print(color(f"\n  {t('banner_title')}", "bold"))
    print(color(f"  {t('banner_sub')}\n", "dim"))


def display_help():
    print(color(f"  {t('commands')}:", "bold"))
    print(color("    [Enter]    ", "cyan") + t("cmd_reroll"))
    print(color("    [k]        ", "cyan") + t("cmd_keep"))
    print(color("    [f]        ", "cyan") + t("cmd_favs"))
    print(color("    [d]        ", "cyan") + t("cmd_remove"))
    print(color("    [a]        ", "cyan") + t("cmd_anim"))
    print(color("    [p]        ", "cyan") + t("cmd_pick"))
    print(color("    [l]        ", "cyan") + t("cmd_lang"))
    print(color("    [h]        ", "cyan") + t("cmd_help"))
    print(color("    [q]        ", "cyan") + t("cmd_quit"))
    print()


# ─── Animation ───

def animate_pet(pet, duration=3.0):
    """Show a short animation of the pet cycling through frames."""
    num_frames = len(BODIES[pet["species"]])
    rarity = pet["rarity"]
    fps = 3
    total_frames = int(duration * fps)

    for i in range(total_frames):
        lines = render_sprite(pet, frame=i % num_frames)
        if i > 0:
            sys.stdout.write(f"\033[{len(lines)}A")
        for line in lines:
            print(rarity_color(f"    {line}", rarity))
        sys.stdout.flush()
        time.sleep(1 / fps)


# ─── Favorites ───

def display_favorites(favorites):
    if not favorites:
        print(color(f"  {t('no_favs')}\n", "dim"))
        return False

    print(color(f"  === {t('favs_title')} ({len(favorites)}) ===\n", "bold"))
    for i, pet in enumerate(favorites, 1):
        rarity = pet["rarity"]
        stars = RARITY_STARS[rarity]
        shiny = color(" SHINY!", "yellow") if pet.get("shiny") else ""
        sp = species_name(pet["species"])
        header = f"  {i}. {sp} {stars}{shiny}"
        print(rarity_color(header, rarity))

        info = f"     {t('rarity')}: {t(rarity)}  |  {t('eyes')}: {pet['eye']}  |  {t('hat')}: {pet['hat']}"
        print(rarity_color(info, rarity))

        # Sprite preview
        lines = render_sprite(pet, frame=0)
        for line in lines:
            print(rarity_color(f"      {line}", rarity))

        # Stats with best/worst coloring
        best_stat = max(pet["stats"], key=lambda k: pet["stats"][k])
        worst_stat = min(pet["stats"], key=lambda k: pet["stats"][k])
        for name in STAT_NAMES:
            value = pet["stats"][name]
            bar = stat_bar(value, width=10)
            display_name = pad_right(t(name), 10)
            label = f"     {display_name} {bar} {value:>3}"
            if name == best_stat:
                print(color(label, "green"))
            elif name == worst_stat:
                print(color(label, "red"))
            else:
                print(label)
        print()

    print(color(f"  [number] = {t('fav_apply')}", "cyan"))
    print(color(f"  [d]      = {t('fav_remove')}", "cyan"))
    print(color(f"  [Enter]  = {t('fav_back')}", "dim"))
    print()
    return True
