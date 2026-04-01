import time

import lang
from lang import t, species_name, SPECIES_ZH
from ui import color, rarity_color, clear_screen, display_banner, display_pet, stat_bar, pad_right
from save import auto_save
from constants import SPECIES, RARITIES, EYES, HATS, RARITY_STARS, STAT_NAMES
from sprites import render_sprite, BODIES
from patcher import estimate_attempts
from apply import apply_pet


def pick_from_list(prompt_text, items, display_fn=None):
    """Let user pick from a numbered list. Returns selected item or None."""
    print(color(f"\n  {prompt_text}:", "bold"))
    for i, item in enumerate(items, 1):
        label = display_fn(item) if display_fn else str(item)
        print(color(f"    {i:>2}. ", "cyan") + label)
    print()
    while True:
        raw = input(color("  > ", "cyan")).strip()
        if raw == "":
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return items[idx]
        print(color(f"  1-{len(items)}", "red"))


def custom_pick(favorites, roll_count):
    """Interactive custom pick mode: user chooses species, rarity, eyes, hat, stats."""
    clear_screen()
    display_banner()
    print(color(f"  === {t('pick_title')} ===\n", "bold"))

    # 1. Species — full sprite gallery (3 columns)
    def _print_species_gallery():
        preview = {"eye": "\u00b7", "hat": "none", "rarity": "common", "shiny": False}
        col_width = 26
        cols = 3
        print(color(f"\n  {t('pick_species')}:", "bold"))
        print()
        for row_start in range(0, len(SPECIES), cols):
            row_species = SPECIES[row_start:row_start + cols]
            # Sprite lines (5 lines per species)
            sprites = []
            for s in row_species:
                preview["species"] = s
                lines = render_sprite(preview, frame=0)
                sprites.append(lines)
            # Number + name header row
            header = ""
            for idx, s in enumerate(row_species):
                num = row_start + idx + 1
                if lang.current_lang == "zh":
                    zh = SPECIES_ZH.get(s, "")
                    label = f"{num:>2}. {s} ({zh})"
                else:
                    label = f"{num:>2}. {s}"
                header += label.ljust(col_width)
            print(color("  " + header, "cyan"))
            # Sprite rows
            for line_idx in range(5):
                row_str = ""
                for i, s in enumerate(row_species):
                    sprite_line = sprites[i][line_idx] if line_idx < len(sprites[i]) else ""
                    row_str += sprite_line.ljust(col_width)
                print("  " + row_str)
            print()

    _print_species_gallery()
    while True:
        raw = input(color("  > ", "cyan")).strip()
        if raw == "":
            species = None
            break
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(SPECIES):
                species = SPECIES[idx]
                break
        print(color(f"  1-{len(SPECIES)}", "red"))
    if species is None:
        return
    if species is None:
        return

    # Show full sprite after selection
    preview = {"species": species, "eye": "\u00b7", "hat": "none", "rarity": "common", "shiny": False}
    print()
    for line in render_sprite(preview):
        print(color(f"    {line}", "cyan"))
    print()

    # 2. Rarity
    def rarity_label(r):
        stars = RARITY_STARS[r]
        name = t(r)
        return rarity_color(f"{pad_right(name, 10)} {stars}", r)

    rarity = pick_from_list(t("pick_rarity"), RARITIES, rarity_label)
    if rarity is None:
        return

    # 3. Eyes — with live face preview
    def eye_label(e):
        from sprites import BODIES as _BODIES
        # Find the face line directly from body definition to avoid render_sprite
        # empty-line inconsistency (some species have non-empty decoration lines
        # in other frames, which prevents the empty top line from being removed)
        body_frame = _BODIES[species][0]
        face_line = next((l for l in body_frame if "{E}" in l), body_frame[2])
        face = face_line.replace("{E}", e).strip()
        return f"{e}   {face}"

    eye = pick_from_list(t("pick_eyes"), EYES, eye_label)
    if eye is None:
        return

    # 4. Hat
    if rarity == "common":
        hat = "none"
        print(color(f"\n  {t('pick_no_hat')}\n", "dim"))
    else:
        hat_choices = [h for h in HATS if h != "none"]

        HAT_ZH = {
            "crown": "皇冠", "tophat": "高帽", "propeller": "螺旋槳",
            "halo": "光環", "wizard": "巫師帽", "beanie": "毛帽", "tinyduck": "小鴨",
        }

        def hat_label(h):
            p = {"species": species, "eye": eye, "hat": h, "rarity": rarity, "shiny": False}
            sprite_lines = render_sprite(p)
            top = sprite_lines[0].strip() if sprite_lines else ""
            if lang.current_lang == "zh":
                zh = HAT_ZH.get(h, "")
                return f"{h:<12} ({zh})  {top}"
            return f"{h:<12} {top}"

        hat = pick_from_list(t("pick_hat"), hat_choices, hat_label)
        if hat is None:
            return

    # Show full preview with current selections
    preview_pet = {"species": species, "eye": eye, "hat": hat, "rarity": rarity, "shiny": False}
    print()
    for line in render_sprite(preview_pet):
        print(rarity_color(f"    {line}", rarity))
    print()

    # 5. Shiny
    shiny_input = input(color(f"  {t('pick_shiny')} ", "yellow")).strip().lower()
    shiny = shiny_input == "y"

    # 6. Peak stat (optional)
    if lang.current_lang == "zh":
        peak_prompt = "最強屬性 (可跳過)"
    else:
        peak_prompt = "Best stat (optional)"

    stat_choices = ["skip"] + list(STAT_NAMES)

    def stat_label(s):
        if s == "skip":
            return color("Skip / 跳過", "dim") if lang.current_lang == "zh" else color("Skip", "dim")
        return t(s)

    peak = pick_from_list(peak_prompt, stat_choices, stat_label)
    if peak == "skip" or peak is None:
        peak = None

    # 7. Dump stat (optional)
    dump = None
    if peak:
        if lang.current_lang == "zh":
            dump_prompt = "最弱屬性 (可跳過)"
        else:
            dump_prompt = "Worst stat (optional)"
        dump_choices = ["skip"] + [s for s in STAT_NAMES if s != peak]
        dump = pick_from_list(dump_prompt, dump_choices, stat_label)
        if dump == "skip" or dump is None:
            dump = None

    # Build desired config
    desired = {
        "species": species,
        "rarity": rarity,
        "eye": eye,
        "hat": hat,
        "shiny": shiny,
    }
    if peak:
        desired["peak"] = peak
    if dump:
        desired["dump"] = dump

    est = estimate_attempts(desired)

    # Build preview pet
    pet = {
        "species": species,
        "rarity": rarity,
        "eye": eye,
        "hat": hat,
        "shiny": shiny,
        "stats": {s: 50 for s in STAT_NAMES},
        "seed": 0,
    }

    # Final preview
    clear_screen()
    display_banner()
    print(color(f"  === {t('pick_preview')} ===\n", "bold"))
    display_pet(pet, show_stats=False)

    if peak:
        if lang.current_lang == "zh":
            print(color(f"  最強屬性: {t(peak)}", "green"))
        else:
            print(color(f"  Best stat: {peak}", "green"))
    if dump:
        if lang.current_lang == "zh":
            print(color(f"  最弱屬性: {t(dump)}", "red"))
        else:
            print(color(f"  Worst stat: {dump}", "red"))

    if lang.current_lang == "zh":
        print(color(f"  預估搜尋: ~{est:,} 次\n", "dim"))
    else:
        print(color(f"  Estimated: ~{est:,} attempts\n", "dim"))

    # Confirm apply
    apply_choice = input(color(f"  {t('pick_confirm')} ", "yellow")).strip().lower()
    if apply_choice == "y":
        apply_pet(pet, desired_override=desired)
        input(color(f"  {t('press_enter')}", "dim"))
    else:
        keep = input(color(f"  [k] = {t('cmd_keep')}, [Enter] = {t('fav_back')} ", "dim")).strip().lower()
        if keep == "k":
            favorites.append(pet)
            auto_save(favorites, roll_count)
            sp = species_name(species)
            print(color(f"\n  {t('kept')} {sp}! ({len(favorites)} {t('favs_total')})", "green"))
            time.sleep(0.8)
