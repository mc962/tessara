from pathlib import Path

# apps/tessara-server/src/tessara_server/constants.py -> apps/tessara-server/
#
# Scoped to this app's own directory, not the uv workspace root: tessara-server
# is packaged/deployed independently, and nothing guarantees it stays nested
# under a tessara/ checkout at runtime (e.g. a Docker build that only copies
# apps/tessara-server + packages/tessara-core).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
