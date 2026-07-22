from __future__ import annotations

# Preset -> asset groups. tessara-cli keeps its own copy of this at
# apps/tessara-cli/src/tessara_cli/presets.py (deliberately duplicated, not
# imported) so a thin remote-mode install never has to pull in tessara-core's
# Pillow/cairosvg dependencies. Changing presets here means changing them
# there too — nothing currently checks the two stay in sync.
PRESETS: dict[str, tuple[str, ...]] = {
    "minimal": ("favicon",),
    "web": ("favicon", "apple"),
    "pwa": ("favicon", "apple", "android", "webmanifest"),
    "social": ("favicon", "opengraph"),
    "everything": ("favicon", "apple", "android", "webmanifest", "opengraph"),
}

# Presets that existed in a previous release and were removed since. Keeping
# a short note here (for roughly a year after removal) lets callers give a
# specific "this was removed, use X instead" message instead of a generic
# "unknown preset" one — safe to delete an entry once it's been gone that long.
REMOVED_PRESETS: dict[str, str] = {}


def describe_unknown_preset(name: str) -> str:
    """Explain why `name` isn't a valid preset, distinguishing removed from never-existed."""
    if name in REMOVED_PRESETS:
        return f"Preset {name!r} was removed: {REMOVED_PRESETS[name]}"
    return f"Unknown preset {name!r}; available: {', '.join(sorted(PRESETS))}"