import multiprocessing
import sys
import time

import lang
from lang import t, species_name
from ui import color, rarity_color, stat_bar, pad_right
from constants import RARITY_STARS, STAT_NAMES, DEFAULT_PERSONALITIES


def apply_pet(pet, desired_override=None):
    """Apply a favorite pet to Claude Code by finding a salt and patching the binary."""
    from patcher import (
        get_user_id, find_claude_binary, get_current_salt,
        find_salt, patch_binary, save_anybuddy_config, update_companion,
    )
    from pick import pick_from_list

    print(color(f"\n  === {t('apply_title')} ===\n", "bold"))

    # Step 1: Get userId
    try:
        user_id = get_user_id()
        print(color(f"  User ID: {user_id[:12]}...", "dim"))
    except Exception as e:
        print(color(f"  {t('error')}: {e}", "red"))
        return False

    # Step 2: Find binary
    try:
        binary_path = find_claude_binary()
        print(color(f"  Binary:  {binary_path}", "dim"))
    except Exception as e:
        print(color(f"  {t('error')}: {e}", "red"))
        return False

    # Step 3: Get current salt
    try:
        old_salt = get_current_salt(binary_path)
        print(color(f"  Current salt: {old_salt}", "dim"))
    except Exception as e:
        print(color(f"  {t('error')}: {e}", "red"))
        return False

    # Step 4: Show target
    if desired_override:
        desired = desired_override
    else:
        desired = {
            "species": pet["species"],
            "rarity": pet["rarity"],
            "eye": pet["eye"],
            "hat": pet["hat"],
            "shiny": pet.get("shiny", False),
        }
    stars = RARITY_STARS[pet["rarity"]]
    sp = species_name(pet["species"])
    print()
    print(rarity_color(f"  {t('apply_target')}: {sp} {stars}  {t('eyes')}:{pet['eye']}  {t('hat')}:{pet['hat']}", pet["rarity"]))
    print()

    # Step 5: Brute-force search
    cpu_count = multiprocessing.cpu_count()
    num_workers = max(1, cpu_count)
    if lang.current_lang == "zh":
        print(color(f"  偵測到 {cpu_count} 核心 → 使用 {num_workers} 工作進程", "dim"))
        print(color(f"  {t('apply_searching')}", "cyan"))
    else:
        print(color(f"  Detected {cpu_count} CPU cores → using {num_workers} workers", "dim"))
        print(color(f"  {t('apply_searching')}", "cyan"))

    def on_progress(info):
        rate = info["rate"]
        rate_str = f"{rate/1000:.0f}k/s" if rate < 1e6 else f"{rate/1e6:.1f}M/s"
        attempts = info["attempts"]
        elapsed = info["elapsed"]
        sys.stdout.write(
            f"\r  {color(f'{attempts:,} tried', 'cyan')}  "
            f"{color(rate_str, 'dim')}  "
            f"{color(f'{elapsed:.1f}s', 'dim')}  "
            f"{color(f'[{num_workers}w]', 'dim')}   "
        )
        sys.stdout.flush()

    # Step 5b: Search loop — keep re-searching until user accepts the stats
    while True:
        result = find_salt(user_id, desired, on_progress=on_progress, num_workers=num_workers)

        sys.stdout.write("\r" + " " * 60 + "\r")
        print(color(f"  {t('apply_found')} {result['attempts']:,} {t('apply_attempts')} ({result['elapsed']:.1f}s)", "green"))
        print()

        # Show the actual stats this salt will produce in /buddy
        actual_stats = result.get("stats", {})
        if actual_stats:
            if lang.current_lang == "zh":
                print(color("  /buddy 實際會顯示的屬性:", "bold"))
            else:
                print(color("  Actual stats that will appear in /buddy:", "bold"))
            best_stat = max(actual_stats, key=lambda k: actual_stats[k])
            worst_stat = min(actual_stats, key=lambda k: actual_stats[k])
            peak_label = "  (最強)" if lang.current_lang == "zh" else "  (peak)"
            dump_label = "  (最弱)" if lang.current_lang == "zh" else "  (dump)"
            for name in STAT_NAMES:
                value = actual_stats[name]
                bar = stat_bar(value)
                display_name = pad_right(t(name), 10)
                suffix = peak_label if name == best_stat else (dump_label if name == worst_stat else "")
                label = f"    {display_name} {bar} {value:>3}{suffix}"
                if name == best_stat:
                    print(color(label, "green"))
                elif name == worst_stat:
                    print(color(label, "red"))
                else:
                    print(label)
            print()

        if lang.current_lang == "zh":
            prompt = "  [y]=套用  [Enter]=重搜  [p]=指定最強/弱屬性後重搜: "
        else:
            prompt = "  [y]=Apply  [Enter]=Re-search  [p]=Set peak/dump then re-search: "
        choice = input(color(prompt, "yellow")).strip().lower()

        if choice == "y":
            break
        elif choice == "p":
            # Let user pick peak/dump constraints then re-search
            from constants import STAT_NAMES as _STAT_NAMES
            stat_opts = ["skip"] + list(_STAT_NAMES)
            def _stat_label(s):
                return color("skip", "dim") if s == "skip" else t(s)
            peak_pick = pick_from_list(
                "最強屬性 (可跳過)" if lang.current_lang == "zh" else "Best stat (optional)",
                stat_opts, _stat_label)
            new_peak = None if (peak_pick == "skip" or peak_pick is None) else peak_pick
            new_dump = None
            if new_peak:
                dump_opts = ["skip"] + [s for s in _STAT_NAMES if s != new_peak]
                dump_pick = pick_from_list(
                    "最弱屬性 (可跳過)" if lang.current_lang == "zh" else "Worst stat (optional)",
                    dump_opts, _stat_label)
                new_dump = None if (dump_pick == "skip" or dump_pick is None) else dump_pick
            desired = {k: v for k, v in desired.items() if k not in ("peak", "dump")}
            if new_peak:
                desired["peak"] = new_peak
            if new_dump:
                desired["dump"] = new_dump
            if lang.current_lang == "zh":
                print(color("  重新搜尋中...\n", "dim"))
            else:
                print(color("  Re-searching...\n", "dim"))
        else:
            # plain re-search, keep existing peak/dump
            if lang.current_lang == "zh":
                print(color("  重新搜尋中...\n", "dim"))
            else:
                print(color("  Re-searching...\n", "dim"))

    # Step 6: Patch binary
    try:
        patch_result = patch_binary(binary_path, old_salt, result["salt"])
        print(color(f"  {t('apply_patched')} {patch_result['replacements']} {t('apply_replacements')}: {patch_result['verified']}", "green"))
        print(color(f"  {t('apply_backup')}: {patch_result['backup_path']}", "dim"))
    except Exception as e:
        print(color(f"  {t('apply_patch_failed')}: {e}", "red"))
        return False

    # Step 7: Save config
    save_anybuddy_config({
        "salt": result["salt"],
        "previousSalt": old_salt,
        "species": desired["species"],
        "rarity": desired["rarity"],
        "eye": desired["eye"],
        "hat": desired["hat"],
        "appliedTo": binary_path,
        "appliedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })

    # Step 8: Set companion name and personality directly
    species = pet["species"]
    default_personality = DEFAULT_PERSONALITIES.get(species, "A loyal coding companion.")
    print()
    prompt_text = t("apply_name").format(species=species_name(species))
    new_name = input(color(f"  {prompt_text}: ", "cyan")).strip()
    if not new_name:
        new_name = species.capitalize()

    try:
        update_companion(name=new_name, personality=default_personality)
        print(color(f"  {t('apply_set')}: {new_name}", "green"))
        print(color(f"  {t('apply_personality')}: \"{default_personality[:60]}...\"", "dim"))
    except Exception as e:
        print(color(f"  {t('error')}: {e}", "red"))

    print(color(f"\n  {t('apply_done')}\n", "bold"))
    return True
