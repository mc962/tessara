"""tessera-core: brand asset generation logic.

No dependency on CLI or web frameworks — this package is a plain Python API
that apps/tessera-cli and apps/tessera-server build on top of.
"""

from .builder import BrandAssetBuilder, UnknownAssetGroupError
from .groups import ASSET_GROUPS, KNOWN_GROUPS
from .presets import PRESETS, REMOVED_PRESETS, describe_unknown_preset
from .source import UnsupportedSourceFormatError

__all__ = [
    "ASSET_GROUPS",
    "KNOWN_GROUPS",
    "PRESETS",
    "REMOVED_PRESETS",
    "BrandAssetBuilder",
    "UnknownAssetGroupError",
    "UnsupportedSourceFormatError",
    "describe_unknown_preset",
]
