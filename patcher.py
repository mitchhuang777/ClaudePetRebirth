"""
Patcher module - finds salt via brute-force and patches Claude Code binary.

Flow:
1. Read userId from ~/.claude.json
2. Use Bun's wyhash to match Claude Code's internal hashing
3. Brute-force search for a salt that produces the desired pet
4. Patch the binary (replace old salt with new one)
"""

import json
import os
import sys
import random
import string
import shutil
import struct
import subprocess
import threading
import time
from pathlib import Path

from constants import (
    RARITIES, RARITY_WEIGHTS, RARITY_FLOOR, SPECIES, EYES, HATS, STAT_NAMES,
)


# ─── Config paths ───

def get_claude_json_path():
    return Path.home() / ".claude.json"


def get_anybuddy_config_path():
    return Path.home() / ".claude-code-any-buddy.json"


def get_user_id():
    """Read userId from ~/.claude.json, matching any-buddy's priority:
    oauthAccount.accountUuid > userID > userId
    """
    path = get_claude_json_path()
    if not path.exists():
        raise FileNotFoundError(f"Cannot find {path}")
    data = json.loads(path.read_text(encoding="utf-8"))

    # Claude Code uses oauthAccount.accountUuid when present (same priority as any-buddy)
    oauth = data.get("oauthAccount")
    if isinstance(oauth, dict) and oauth.get("accountUuid"):
        return oauth["accountUuid"]

    user_id = data.get("userID") or data.get("userId")
    if not user_id:
        raise ValueError("No userId found in ~/.claude.json")
    return user_id


def load_anybuddy_config():
    path = get_anybuddy_config_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_anybuddy_config(config):
    path = get_anybuddy_config_path()
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── Binary detection ───

ORIGINAL_SALT = "friend-2026-401"


def find_claude_binary():
    """Find the Claude Code binary."""
    # Check CLAUDE_BINARY env var override
    env_path = os.environ.get("CLAUDE_BINARY")
    if env_path:
        real = os.path.realpath(env_path)
        if os.path.isfile(real):
            return real
        raise FileNotFoundError(f"CLAUDE_BINARY={env_path!r} does not exist")

    home = Path.home()

    # Windows-specific detection
    if sys.platform == "win32":
        app_data = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local_app_data = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))

        candidates = []

        # npm global install — the actual JS bundle to patch
        npm_cli = app_data / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "cli.mjs"
        candidates.append(npm_cli)

        # Resolve via `where claude` → might return the .cmd shim
        try:
            result = subprocess.run(["where", "claude"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # `where` may return multiple lines; try each
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.endswith(".cmd"):
                        # Parse the .cmd shim to find the actual cli.mjs
                        try:
                            content = Path(line).read_text(encoding="utf-8", errors="replace")
                            import re
                            m = re.search(r'node_modules[\\/]@anthropic-ai[\\/]claude-code[\\/][^\s"]+', content)
                            if m:
                                target = Path(line).parent / m.group(0).replace("\\", os.sep)
                                if target.is_file():
                                    candidates.insert(0, target)
                        except Exception:
                            pass
                    else:
                        real = os.path.realpath(line)
                        if os.path.isfile(real):
                            candidates.insert(0, Path(real))
        except Exception:
            pass

        # Desktop app (Electron)
        candidates.append(local_app_data / "Programs" / "claude" / "claude.exe")

        for c in candidates:
            if Path(c).exists() and Path(c).is_file():
                return str(os.path.realpath(c))

        raise FileNotFoundError(
            "Cannot find Claude Code binary.\n"
            "Set CLAUDE_BINARY to the path of cli.mjs (e.g. "
            r'%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\cli.mjs'
            ")."
        )

    # Unix: try 'which claude' first
    try:
        result = subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            path = result.stdout.strip()
            real = os.path.realpath(path)
            if os.path.isfile(real):
                return real
    except Exception:
        pass

    # Known Unix paths
    candidates = [
        home / ".local" / "bin" / "claude",
    ]

    # Check versioned paths
    versions_dir = home / ".local" / "share" / "claude" / "versions"
    if versions_dir.exists():
        for d in sorted(versions_dir.iterdir(), reverse=True):
            if d.is_dir():
                candidates.append(d / "claude")
            elif d.is_file() and "anybuddy-bak" not in d.name:
                candidates.append(d)

    for c in candidates:
        if c.exists() and c.is_file():
            return str(os.path.realpath(c))

    raise FileNotFoundError("Cannot find Claude Code binary. Set CLAUDE_BINARY env var.")


def get_current_salt(binary_path):
    """Determine what salt is currently in the binary."""
    data = open(binary_path, "rb").read()

    # Check original salt
    if data.count(ORIGINAL_SALT.encode()) >= 3:
        return ORIGINAL_SALT

    # Check any-buddy config for current salt
    config = load_anybuddy_config()
    if config and config.get("salt"):
        salt = config["salt"]
        if data.count(salt.encode()) >= 3:
            return salt

    raise ValueError("Cannot determine current salt in binary.")


# ─── Persistent bun hash process ───
# One long-lived bun subprocess per Python process, reused across all batches.
# Eliminates the ~100ms per-batch startup cost.

_BUN_HASH_SCRIPT = r"""
process.stdin.setEncoding('utf8');
let buf = '';
process.stdin.on('data', (chunk) => {
    buf += chunk;
    let idx;
    while ((idx = buf.indexOf('\n')) !== -1) {
        const line = buf.slice(0, idx);
        buf = buf.slice(idx + 1);
        if (line.length > 0) {
            process.stdout.write(
                String(Number(BigInt(Bun.hash(line)) & 0xffffffffn)) + '\n'
            );
        }
    }
});
"""

_bun_proc = None
_bun_lock = threading.Lock()


def _get_bun_proc():
    """Return the module-level persistent bun process, starting it if needed."""
    global _bun_proc
    with _bun_lock:
        if _bun_proc is None or _bun_proc.poll() is not None:
            _bun_proc = subprocess.Popen(
                ["bun", "-e", _BUN_HASH_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
    return _bun_proc


def bun_hash(s):
    """Hash a single string via the persistent bun process."""
    return bun_hash_batch([s])[0]


# ─── Mulberry32 PRNG (matches Claude Code) ───

def mulberry32(seed):
    a = seed & 0xFFFFFFFF

    def next_val():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (1 | t)) & 0xFFFFFFFF
        imul = ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF
        t = (((t + imul) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return next_val


def pick(rng, arr):
    return arr[int(rng() * len(arr))]


def roll_rarity(rng):
    total = sum(RARITY_WEIGHTS.values())
    roll = rng() * total
    for rarity in RARITIES:
        roll -= RARITY_WEIGHTS[rarity]
        if roll < 0:
            return rarity
    return "common"


def roll_from_salt(user_id, salt):
    """Roll a pet using userId + salt, matching Claude Code's logic exactly."""
    key = user_id + salt
    h = bun_hash(key)
    rng = mulberry32(h)

    rarity = roll_rarity(rng)
    species = pick(rng, SPECIES)
    eye = pick(rng, EYES)
    hat = "none" if rarity == "common" else pick(rng, HATS)
    shiny = rng() < 0.01

    return {
        "rarity": rarity,
        "species": species,
        "eye": eye,
        "hat": hat,
        "shiny": shiny,
    }


# ─── Batch hash for speed ───

def bun_hash_batch(strings):
    """Hash multiple strings using the persistent bun process.

    Writing to stdin and reading from stdout run concurrently via a thread
    to prevent pipe-buffer deadlock when batches are large.
    """
    global _bun_proc
    try:
        proc = _get_bun_proc()
        input_bytes = "\n".join(strings).encode("utf-8") + b"\n"

        write_exc = []

        def _write():
            try:
                proc.stdin.write(input_bytes)
                proc.stdin.flush()
            except Exception as e:
                write_exc.append(e)

        writer = threading.Thread(target=_write, daemon=True)
        writer.start()

        hashes = []
        for _ in strings:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("bun process exited unexpectedly")
            hashes.append(int(line.strip()))

        writer.join()
        if write_exc:
            raise write_exc[0]
        return hashes
    except Exception as e:
        with _bun_lock:
            _bun_proc = None  # force restart on next call
        raise RuntimeError(f"Batch hash failed: {e}")


# ─── Salt brute-force search ───

def generate_salt(length=15):
    """Generate a random salt string of exact length (must match original salt length)."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def roll_stats_from_rng(rng, rarity):
    """Roll stats matching Claude Code's logic. Returns (stats_dict, peak_name, dump_name)."""
    floor = RARITY_FLOOR[rarity]
    peak = pick(rng, STAT_NAMES)
    dump = pick(rng, STAT_NAMES)
    while dump == peak:
        dump = pick(rng, STAT_NAMES)

    stats = {}
    for name in STAT_NAMES:
        if name == peak:
            stats[name] = min(100, floor + 50 + int(rng() * 30))
        elif name == dump:
            stats[name] = max(1, floor - 10 + int(rng() * 15))
        else:
            stats[name] = floor + int(rng() * 40)
    return stats, peak, dump


def estimate_attempts(desired):
    """Estimate how many attempts needed to find a matching salt."""
    rarity_chance = RARITY_WEIGHTS[desired["rarity"]] / 100
    species_chance = 1 / len(SPECIES)
    eye_chance = 1 / len(EYES)
    hat_chance = 1.0
    if desired["rarity"] != "common" and desired.get("hat", "none") != "none":
        hat_chance = 1 / (len(HATS) - 1)  # exclude 'none'
    shiny_chance = 0.01 if desired.get("shiny") else 1.0
    peak_chance = 1 / len(STAT_NAMES) if desired.get("peak") else 1.0
    dump_chance = 1 / (len(STAT_NAMES) - 1) if desired.get("dump") else 1.0

    total_chance = rarity_chance * species_chance * eye_chance * hat_chance * shiny_chance * peak_chance * dump_chance
    return int(1 / total_chance) if total_chance > 0 else 999999


def _check_batch(salts, hashes, desired, want_shiny, want_peak, want_dump):
    """Check a batch of salts against desired traits. Returns matching salt or None."""
    for salt, h in zip(salts, hashes):
        rng = mulberry32(h)

        rarity = roll_rarity(rng)
        if rarity != desired["rarity"]:
            continue

        species = pick(rng, SPECIES)
        if species != desired["species"]:
            continue

        eye = pick(rng, EYES)
        if eye != desired["eye"]:
            continue

        if rarity == "common":
            hat = "none"
        else:
            hat = pick(rng, HATS)
        if hat != desired["hat"]:
            continue

        shiny = rng() < 0.01
        if want_shiny and not shiny:
            continue

        # Check peak/dump stats
        stats, peak, dump = roll_stats_from_rng(rng, rarity)
        if want_peak and peak != want_peak:
            continue
        if want_dump and dump != want_dump:
            continue

        return salt, stats
    return None


def _worker(args):
    """Worker task: generate a batch of salts, hash them, and check for a match."""
    user_id, desired, want_shiny, want_peak, want_dump, batch_size, worker_seed = args
    rnd = random.Random(worker_seed)
    chars = string.ascii_letters + string.digits

    # rnd.choices is ~10x faster than calling rnd.choice in a loop
    salts = ["".join(rnd.choices(chars, k=15)) for _ in range(batch_size)]
    keys = [user_id + s for s in salts]
    hashes = bun_hash_batch(keys)
    result = _check_batch(salts, hashes, desired, want_shiny, want_peak, want_dump)
    return result  # (salt, stats) or None


def find_salt(user_id, desired, on_progress=None, batch_size=10000, num_workers=None):
    """
    Brute-force search for a salt that produces the desired pet traits.
    Uses a pipelined ProcessPoolExecutor: as soon as any worker finishes,
    a new task is immediately submitted so all cores stay busy.

    desired: dict with species, rarity, eye, hat, and optionally shiny, peak, dump
    """
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

    if num_workers is None:
        num_workers = max(1, multiprocessing.cpu_count())

    total_attempts = 0
    start_time = time.time()
    want_shiny = desired.get("shiny", False)
    want_peak = desired.get("peak")
    want_dump = desired.get("dump")

    # For tiny searches, single-thread is faster (no process spawn overhead)
    est = estimate_attempts(desired)
    if est < 10_000:
        num_workers = 1

    def make_args():
        return (user_id, desired, want_shiny, want_peak, want_dump,
                batch_size, random.randint(0, 2**32))

    if num_workers == 1:
        while True:
            result = _worker(make_args())
            total_attempts += batch_size
            if result:
                salt, stats = result
                return {"salt": salt, "attempts": total_attempts,
                        "elapsed": time.time() - start_time, "stats": stats}
            if on_progress:
                elapsed = time.time() - start_time
                rate = total_attempts / elapsed if elapsed > 0 else 0
                on_progress({"attempts": total_attempts, "elapsed": elapsed, "rate": rate})
    else:
        # Pipelined parallel search:
        # Keep (num_workers * 2) tasks in-flight so workers are never starved.
        # As soon as any task completes, check the result and immediately
        # submit a replacement — no waiting for the whole batch to finish.
        queue_depth = num_workers * 2
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            pending = {executor.submit(_worker, make_args()) for _ in range(queue_depth)}

            while True:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)

                for future in done:
                    total_attempts += batch_size
                    result = future.result()
                    if result:
                        # Found — cancel queued (not yet running) tasks and return
                        for f in pending:
                            f.cancel()
                        salt, stats = result
                        return {"salt": salt, "attempts": total_attempts,
                                "elapsed": time.time() - start_time, "stats": stats}
                    # Slot freed — submit a replacement immediately
                    pending.add(executor.submit(_worker, make_args()))

                if on_progress:
                    elapsed = time.time() - start_time
                    rate = total_attempts / elapsed if elapsed > 0 else 0
                    on_progress({"attempts": total_attempts, "elapsed": elapsed, "rate": rate})


# ─── Binary patching ───

def patch_binary(binary_path, old_salt, new_salt):
    """
    Replace old_salt with new_salt in the binary (all occurrences).
    Uses atomic rename for safety.
    """
    if len(old_salt) != len(new_salt):
        raise ValueError(f"Salt length mismatch: {len(old_salt)} vs {len(new_salt)}")

    data = open(binary_path, "rb").read()
    old_bytes = old_salt.encode("utf-8")
    new_bytes = new_salt.encode("utf-8")

    count = data.count(old_bytes)
    if count == 0:
        raise ValueError(f"Salt '{old_salt}' not found in binary.")

    # Create backup if not exists
    backup_path = binary_path + ".rebirth-bak"
    if not os.path.exists(backup_path):
        shutil.copy2(binary_path, backup_path)

    # Replace
    patched = data.replace(old_bytes, new_bytes)

    # Write to temp file then atomic rename
    tmp_path = binary_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(patched)

    # Copy permissions
    st = os.stat(binary_path)
    os.chmod(tmp_path, st.st_mode)

    # Atomic rename
    os.replace(tmp_path, binary_path)

    # Verify
    verify_data = open(binary_path, "rb").read()
    verified = verify_data.count(new_bytes) >= count

    return {
        "replacements": count,
        "verified": verified,
        "backup_path": backup_path,
    }


# ─── Update companion in .claude.json ───

def update_companion(name=None, personality=None):
    """Update companion name/personality in ~/.claude.json."""
    path = get_claude_json_path()
    data = json.loads(path.read_text(encoding="utf-8"))

    if "companion" not in data:
        data["companion"] = {}

    if name:
        data["companion"]["name"] = name
    if personality:
        data["companion"]["personality"] = personality

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def delete_companion():
    """Delete companion from ~/.claude.json so Claude re-hatches on next /buddy."""
    path = get_claude_json_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if "companion" in data:
        del data["companion"]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
