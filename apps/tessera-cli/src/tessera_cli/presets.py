from __future__ import annotations

# Deliberately duplicated from tessera-core's copy at
# packages/tessera-core/src/tessera/presets.py, not imported: tessera-cli's
# base install has no dependency on tessera-core (only the "local" extra does),
# since remote/web mode never touches Pillow/cairosvg — it just needs these
# preset names to validate --preset and build the request. Changing presets
# there means changing them here too — nothing currently checks the two stay
# in sync.
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