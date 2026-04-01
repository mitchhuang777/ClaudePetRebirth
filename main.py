#!/usr/bin/env python3
"""
ClaudePetRebirth - Reroll your Claude Code companion pet!

Roll a random pet and keep rerolling until you find the one you love.
"""

import os
import sys
import time

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("")  # Enable ANSI escape codes on Windows

import lang
from lang import t, species_name, set_lang
from ui import (
    color, clear_screen, display_banner, display_help,
    display_pet, display_favorites, animate_pet,
)
from save import auto_save, load_save
from apply import apply_pet
from pick import custom_pick
from generation import roll_pet


def main():
    clear_screen()
    display_banner()
    display_help()

    favorites, roll_count = load_save()
    show_animation = False
    current_pet = None

    while True:
        # Roll a new pet
        if current_pet is None:
            current_pet = roll_pet()
            roll_count += 1
            auto_save(favorites, roll_count)

        clear_screen()
        display_banner()
        if lang.current_lang == "zh":
            print(color(f"  {t('roll')} {roll_count} 抽", "dim"))
        else:
            print(color(f"  {t('roll')} #{roll_count}", "dim"))
        print()
        display_pet(current_pet, show_stats=False)

        if show_animation:
            animate_pet(current_pet, duration=2.0)

        # Prompt
        fav_count = f" | {len(favorites)} {t('favs_title')}" if favorites else ""
        if lang.current_lang == "zh":
            prompt = color(f"  [Enter]=重抽 [k]=收藏 [f]=收藏列表 [p]=自選 [l]=語言 [h]=說明 [q]=離開{fav_count}", "dim")
        else:
            prompt = color(f"  [Enter]=Reroll [k]=Keep [f]=Favs [p]=Pick [l]=Lang [h]=Help [q]=Quit{fav_count}", "dim")
        print(prompt)

        try:
            choice = input(color("  > ", "cyan")).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(color(f"\n\n  {t('bye')}\n", "dim"))
            break

        if choice == "q":
            print(color(f"\n  {t('bye')}\n", "dim"))
            break
        elif choice == "k":
            favorites.append(current_pet)
            auto_save(favorites, roll_count)
            sp = species_name(current_pet["species"])
            print(color(f"\n  {t('kept')} {sp}! ({len(favorites)} {t('favs_total')})", "green"))
            time.sleep(0.8)
            current_pet = None
        elif choice == "f":
            clear_screen()
            display_banner()
            has_favs = display_favorites(favorites)
            if has_favs:
                fav_choice = input(color("  > ", "cyan")).strip().lower()
                if fav_choice == "d" and favorites:
                    removed = favorites.pop()
                    auto_save(favorites, roll_count)
                    sp = species_name(removed["species"])
                    print(color(f"\n  {t('removed')} {sp} {t('from_favs')}", "yellow"))
                    time.sleep(0.8)
                elif fav_choice.isdigit():
                    idx = int(fav_choice) - 1
                    if 0 <= idx < len(favorites):
                        clear_screen()
                        display_banner()
                        display_pet(favorites[idx], show_index=idx + 1, total=len(favorites), show_stats=False)
                        apply_choice = input(color(f"  {t('apply_confirm')} ", "yellow")).strip().lower()
                        if apply_choice == "y":
                            apply_pet(favorites[idx])
                            input(color(f"  {t('press_enter')}", "dim"))
                    else:
                        print(color(f"  {t('fav_invalid')} 1-{len(favorites)}.", "red"))
                        time.sleep(0.8)
            else:
                input(color(f"  {t('press_enter')}", "dim"))
        elif choice == "d":
            if favorites:
                removed = favorites.pop()
                auto_save(favorites, roll_count)
                sp = species_name(removed["species"])
                print(color(f"\n  {t('removed')} {sp} {t('from_favs')}", "yellow"))
                time.sleep(0.8)
            else:
                print(color(f"\n  {t('no_favs_remove')}", "dim"))
                time.sleep(0.8)
        elif choice == "a":
            show_animation = not show_animation
            status = "ON" if show_animation else "OFF"
            print(color(f"\n  {t('anim')}: {status}", "cyan"))
            time.sleep(0.5)
        elif choice == "p":
            custom_pick(favorites, roll_count)
        elif choice == "l":
            set_lang("zh" if lang.current_lang == "en" else "en")
        elif choice == "h":
            clear_screen()
            display_banner()
            display_help()
            input(color(f"  {t('press_enter')}", "dim"))
        elif choice == "":
            current_pet = None
        else:
            current_pet = None


if __name__ == "__main__":
    main()
