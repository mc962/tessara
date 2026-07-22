from __future__ import annotations

# Preset -> asset groups. Shared by tessera-cli and tessera-server so both
# expose the exact same set of presets.
PRESETS: dict[str, tuple[str, ...]] = {
    "web": ("favicon", "apple"),
    "pwa": ("favicon", "apple", "android", "webmanifest"),
    "social": ("favicon", "opengraph"),
    "everything": ("favicon", "apple", "android", "webmanifest", "opengraph"),
}
