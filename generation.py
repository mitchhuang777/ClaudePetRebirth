import random
import math
from constants import (
    RARITIES, RARITY_WEIGHTS, RARITY_FLOOR, SPECIES, EYES, HATS, STAT_NAMES,
)


def mulberry32(seed):
    """Mulberry32 seeded PRNG - matches the original companion.ts logic."""
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


def roll_stats(rng, rarity):
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
    return stats


def roll_pet(seed=None):
    """Roll a random pet. If seed is None, generate a random seed."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    rng = mulberry32(seed)
    rarity = roll_rarity(rng)

    pet = {
        "seed": seed,
        "rarity": rarity,
        "species": pick(rng, SPECIES),
        "eye": pick(rng, EYES),
        "hat": "none" if rarity == "common" else pick(rng, HATS),
        "shiny": rng() < 0.01,
        "stats": roll_stats(rng, rarity),
    }
    return pet
