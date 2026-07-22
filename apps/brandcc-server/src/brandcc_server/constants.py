from pathlib import Path

# apps/brandcc-server/src/brandcc_server/constants.py -> apps/brandcc-server/
#
# Scoped to this app's own directory, not the uv workspace root: brandcc-server
# is packaged/deployed independently, and nothing guarantees it stays nested
# under a brandcc/ checkout at runtime (e.g. a Docker build that only copies
# apps/brandcc-server + packages/brandcc-core).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
