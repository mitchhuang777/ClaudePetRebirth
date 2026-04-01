from pathlib import Path
import json

SAVE_PATH = Path("save_data.json")


def auto_save(favorites, roll_count):
    """Auto-save favorites and roll count."""
    data = {
        "roll_count": roll_count,
        "favorites": [],
    }
    for pet in favorites:
        data["favorites"].append({
            "seed": pet.get("seed", 0),
            "species": pet["species"],
            "rarity": pet["rarity"],
            "eye": pet["eye"],
            "hat": pet["hat"],
            "shiny": pet.get("shiny", False),
            "stats": pet["stats"],
        })
    SAVE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_save():
    """Load favorites and roll count from save file."""
    # Migrate from old favorites.json
    old_path = Path("favorites.json")
    if not SAVE_PATH.exists() and old_path.exists():
        try:
            favs = json.loads(old_path.read_text(encoding="utf-8"))
            return favs, 0
        except (json.JSONDecodeError, KeyError):
            return [], 0

    if not SAVE_PATH.exists():
        return [], 0
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        return data.get("favorites", []), data.get("roll_count", 0)
    except (json.JSONDecodeError, KeyError):
        return [], 0
