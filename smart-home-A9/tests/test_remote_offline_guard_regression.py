from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets"


def test_device_remote_page_allows_commands_when_current_device_is_offline():
    source = REMOTE_PAGE.read_text(encoding="utf-8")

    assert "currentOnline(): boolean" in source
    assert ".enabled(!this.commandBusy)" in source
    assert ".enabled(this.currentOnline() && !this.commandBusy)" not in source
    assert "if (!current.online)" not in source
    slider_start = source.index("  queueSliderCommand(")
    slider_end = source.index("  tn(): string", slider_start)
    assert "if (!this.currentOnline())" not in source[slider_start:slider_end]
    assert "控制按钮已受保护" not in source
