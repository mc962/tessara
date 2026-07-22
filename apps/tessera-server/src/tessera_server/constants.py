from pathlib import Path

# apps/tessera-server/src/tessera_server/constants.py -> apps/tessera-server/
#
# Scoped to this app's own directory, not the uv workspace root: tessera-server
# is packaged/deployed independently, and nothing guarantees it stays nested
# under a tessera/ checkout at runtime (e.g. a Docker build that only copies
# apps/tessera-server + packages/tessera-core).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
