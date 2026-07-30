from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOTE_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets"


def test_device_remote_page_refreshes_and_displays_room_environment():
    source = REMOTE_PAGE.read_text(encoding="utf-8")

    assert "@State roomDevices: Device[] = []" in source
    assert "async refreshRoomEnvironment(): Promise<void>" in source
    assert "await getDevicesForUi(current.room_id)" in source
    assert "private environmentTimer: number = -1" in source
    assert "setInterval(() => {" in source
    assert "this.refreshRoomEnvironment()" in source
    assert "室内温度" in source
    assert "室内湿度" in source
    assert "湿度未采集" in source


def test_device_remote_page_includes_room_environment_in_current_status_text():
    source = REMOTE_PAGE.read_text(encoding="utf-8")

    assert "currentStatusLabel(): string" in source
    assert "return this.stateLabel() + ' · ' + this.roomTemperature() + ' · ' + this.roomHumidity()" in source
    assert source.count("Text(this.currentStatusLabel())") == 2
