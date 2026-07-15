from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets"


def test_device_remote_page_disables_primary_actions_when_current_device_is_offline():
    source = REMOTE_PAGE.read_text(encoding="utf-8")

    assert "currentOnline(): boolean" in source
    assert ".enabled(this.currentOnline() && !this.commandBusy)" in source
    assert "设备当前离线，请恢复连接后再发送指令。" in source
