from __future__ import annotations

GROUP_SNIPPETS: dict[str, tuple[str, ...]] = {
    "favicon": (
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">',
        '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">',
    ),
    "apple": ('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">',),
    "android": (
        '<link rel="icon" type="image/png" sizes="192x192" href="/android-chrome-192x192.png">',
        '<link rel="icon" type="image/png" sizes="512x512" href="/android-chrome-512x512.png">',
    ),
    "webmanifest": ('<link rel="manifest" href="/site.webmanifest">',),
    "opengraph": (
        '<meta property="og:image" content="/opengraph.png">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:image" content="/opengraph.png">',
    ),
}


def html_snippets(groups: list[str]) -> list[str]:
    """Return the <head> tags relevant to `groups`, deduped and in a stable order."""
    lines: list[str] = []
    for group in groups:
        for line in GROUP_SNIPPETS.get(group, ()):
            if line not in lines:
                lines.append(line)
    return lines
