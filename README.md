# ClaudePetRebirth

> 繁體中文版請見 [README.zh-TW.md](README.zh-TW.md)

Reroll your Claude Code companion pet until you find the one you love.

Inspired by [any-buddy](https://github.com/cpaczek/any-buddy).

---

## What is this?

Claude Code assigns you a deterministic companion pet based on your account ID. **ClaudePetRebirth** lets you reroll random pets in your terminal, preview their sprites, save your favorites, and **apply any pet you want directly to Claude Code** by brute-force searching for a matching salt.

---

## Features

- **18 species** — duck, goose, blob, cat, dragon, octopus, owl, penguin, turtle, snail, ghost, axolotl, capybara, cactus, robot, rabbit, mushroom, chonk
- **5 rarities** — Common (60%), Uncommon (25%), Rare (10%), Epic (4%), Legendary (1%)
- **6 eye styles** — `·` `✦` `×` `◉` `@` `°`
- **7 hats** — crown, tophat, propeller, halo, wizard, beanie, tinyduck (uncommon+ only)
- **5 stats** — DEBUGGING, PATIENCE, CHAOS, WISDOM, SNARK
- **Shiny** — 1% chance per roll
- **Favorites system** — keep, compare, and apply pets
- **Custom pick mode** — choose exact species / rarity / eyes / hat / peak stat
- **Fast parallel search** — persistent bun process + multiprocessing, ~500k–1M+ hashes/sec
- **Auto-detected workers** — detects CPU core count automatically; better hardware = faster search
- **zh/en bilingual UI**

---

## Requirements

- Python 3.8+
- [Bun](https://bun.sh) (for wyhash — must be on PATH)

Bun is **required**. Claude Code internally uses `Bun.hash` (wyhash) to generate pets, and there is no equivalent native Python implementation. The tool spawns a persistent Bun subprocess to replicate the exact same hash — without it, the search cannot run.

**Install Bun:**

```bash
# Linux / macOS / WSL
curl -fsSL https://bun.sh/install | bash

# Windows (PowerShell)
powershell -c "irm bun.sh/install.ps1 | iex"
```

---

## Usage

```bash
cd ClaudePetRebirth
python main.py
```

---

## Controls

| Key | Action |
|---|---|
| `Enter` | Reroll a new random pet |
| `k` | Keep current pet (add to favorites) |
| `f` | View favorites / apply to Claude Code |
| `d` | Remove last favorite |
| `a` | Toggle animation preview |
| `p` | Custom pick mode |
| `l` | Toggle zh/en language |
| `h` | Show help |
| `q` | Quit |

---

## Applying a Pet

From the favorites list (`f`), select a pet by number → confirm → the tool:

1. Reads your `oauthAccount.accountUuid` from `~/.claude.json`
2. Auto-detects CPU cores and launches that many parallel workers
3. Brute-forces a 15-char salt so that `hash(userId + salt)` rolls your chosen pet
4. Shows the **actual stats** that will appear in `/buddy` before you commit
5. Patches the Claude Code binary in-place (backup created automatically)
6. Saves salt to `~/.claude-code-any-buddy.json`
7. Updates `companion.name` / `companion.personality` in `~/.claude.json`

After patching, restart Claude Code and run `/buddy` to see your new pet.

---

## Custom Pick Mode (`p`)

Choose species → rarity → eyes → hat → shiny → optional peak/dump stat.  
After the search finds a salt, the **actual stats** that will appear in `/buddy` are shown before you commit. Press `Enter` to re-search for different stats, or `p` to add peak/dump constraints.

---

## Search Speed

The tool uses a persistent Bun subprocess + Python multiprocessing. The worker count is auto-detected and displayed before each search.

| Hardware | Approx. speed |
|---|---|
| 2 cores | ~200k hashes/sec |
| 4 cores | ~400k hashes/sec |
| 8 cores | ~800k hashes/sec |
| 16 cores | ~1.5M hashes/sec |

---

## Match Difficulty

Each trait you specify multiplies the expected attempts.

| Target | Odds | Est. attempts |
|---|---|---|
| Any pet | — | 1 |
| Common + species + eyes | 1/180 | ~180 |
| Rare + species + eyes + hat | 1/6,480 | ~6,480 |
| Legendary + species + eyes + hat | 1/75,600 | ~75,600 |
| Legendary + species + eyes + hat + peak + dump | 1/1,512,000 | ~1.5M |
| Any + shiny | ×100 | ×100 |

At 1M hashes/sec, even the hardest combination takes only a few minutes.

> **Note:** Stats cannot all be 100. The PRNG always produces one peak and one dump stat by design — a dump stat on Legendary caps at ~54.

---

## Project Structure

| File | Purpose |
|---|---|
| `main.py` | Main TUI loop |
| `lang.py` | Bilingual string table + `t()` helper |
| `ui.py` | All display / rendering functions |
| `apply.py` | `apply_pet()` — salt search → binary patch |
| `pick.py` | `custom_pick()` — interactive trait selector |
| `save.py` | Favorites save / load |
| `patcher.py` | Binary patching, salt search engine, bun hash |
| `generation.py` | Random pet roll (Mulberry32 PRNG) |
| `sprites.py` | ASCII sprite data + renderer |
| `constants.py` | Species, rarities, eyes, hats, stats, personalities |

---

## Rarities

| Rarity | Stars | Odds | Stat floor |
|---|---|---|---|
| Common | ★ | 60% | 5 |
| Uncommon | ★★ | 25% | 15 |
| Rare | ★★★ | 10% | 25 |
| Epic | ★★★★ | 4% | 35 |
| Legendary | ★★★★★ | 1% | 50 |

---

## License

MIT
