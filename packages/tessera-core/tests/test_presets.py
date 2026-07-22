from __future__ import annotations

from tessera import presets


def test_describe_unknown_preset_for_never_existed():
    message = presets.describe_unknown_preset("not-a-real-preset")
    assert "not-a-real-preset" in message
    assert "Unknown preset" in message
    for name in presets.PRESETS:
        assert name in message


def test_describe_unknown_preset_for_removed(monkeypatch):
    monkeypatch.setitem(presets.REMOVED_PRESETS, "legacy", "use 'web' instead")
    message = presets.describe_unknown_preset("legacy")
    assert message == "Preset 'legacy' was removed: use 'web' instead"