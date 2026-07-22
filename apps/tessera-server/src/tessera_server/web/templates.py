import json
import os
from pathlib import Path

from fastapi.templating import Jinja2Templates

from tessera_server.constants import PROJECT_ROOT

_MANIFEST_PATH = Path(PROJECT_ROOT) / "static" / "js" / "dist" / "manifest.json"
_DEV = os.environ.get("APP_ENV", "").lower() in ("lcl", "tst")

_FALLBACKS = {
    "app.js": "/static/js/src/app.js",
    "app.css": "/static/js/src/app.css",
}

try:
    _manifest: dict[str, str] = json.loads(_MANIFEST_PATH.read_text())
except FileNotFoundError:
    _manifest = {}


def asset(name: str) -> str:
    """Return the fingerprinted URL for a bundled asset, falling back to the unbuilt source."""
    if _DEV:
        try:
            manifest = json.loads(_MANIFEST_PATH.read_text())
        except FileNotFoundError:
            manifest = {}
        return str(manifest.get(name, _FALLBACKS.get(name, f"/static/{name}")))
    return _manifest.get(name, _FALLBACKS.get(name, f"/static/{name}"))


templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))
templates.env.globals["asset"] = asset
