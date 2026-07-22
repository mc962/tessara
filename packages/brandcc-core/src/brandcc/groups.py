from __future__ import annotations

from .specs import CanvasImageSpec, IcoSpec, ImageSpec

WHITE = (255, 255, 255, 255)

FAVICON_GROUP: tuple[ImageSpec | IcoSpec, ...] = (
    ImageSpec("favicon-16x16.png", 16),
    ImageSpec("favicon-32x32.png", 32),
    ImageSpec("favicon-48x48.png", 48),
    IcoSpec("favicon.ico", (16, 32, 48)),
)

# iOS renders transparent pixels as black on the home screen, so this one
# gets an opaque white background instead of the default transparent canvas.
APPLE_GROUP: tuple[ImageSpec, ...] = (ImageSpec("apple-touch-icon.png", 180, background=WHITE),)

ANDROID_GROUP: tuple[ImageSpec, ...] = (
    ImageSpec("android-chrome-192x192.png", 192),
    ImageSpec("android-chrome-512x512.png", 512),
)

# Standard OpenGraph/Twitter card size. The logo is centered with generous
# padding on an opaque background (transparency + social platforms is unreliable,
# and a full-bleed logo alone doesn't read well as a social preview).
OPENGRAPH_GROUP: tuple[CanvasImageSpec, ...] = (
    CanvasImageSpec("opengraph.png", 1200, 630, padding=0.3, background=WHITE),
)

ASSET_GROUPS: dict[str, tuple[ImageSpec | IcoSpec | CanvasImageSpec, ...]] = {
    "favicon": FAVICON_GROUP,
    "apple": APPLE_GROUP,
    "android": ANDROID_GROUP,
    "opengraph": OPENGRAPH_GROUP,
}

# "webmanifest" isn't in ASSET_GROUPS above because it isn't a plain list of
# image specs (it's a JSON file built from builder-level metadata) - it's
# handled specially in BrandAssetBuilder. It still needs the android icons to
# exist and to be named consistently, so it's declared as depending on them.
GROUP_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "webmanifest": ("android",),
}

KNOWN_GROUPS: frozenset[str] = frozenset(ASSET_GROUPS) | {"webmanifest"}
