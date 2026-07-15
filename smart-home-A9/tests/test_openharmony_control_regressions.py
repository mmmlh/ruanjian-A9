from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets"
DEVICE_REMOTE_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets"
CRYPTO_UTIL = ROOT / "openharmony/entry/src/main/ets/common/CryptoUtil.ets"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dashboard_realtime_updates_patch_local_device_state_instead_of_flagging_manual_refresh():
    source = _source(DASHBOARD_PAGE)

    assert "@State realtimeDirty: boolean = false" not in source
    assert "this.realtimeDirty = true" not in source
    assert "this.queueRefresh()" not in source
    assert "this.updateDeviceFromRealtime(topic, payload)" in source
    assert "updateDeviceFromRealtime(topic: string, payload: Record<string, Object>): void" in source


def test_dashboard_header_uses_sync_state_instead_of_static_environment_copy():
    source = _source(DASHBOARD_PAGE)

    assert "@State lastSynced: string = ''" in source
    assert "this.lastSynced = this.syncTime()" in source
    assert "最后同步 " in source
    assert "周日 · 上海 · 26°C · 空气良" not in source


def test_dashboard_confirms_safety_sensitive_scenes_before_execution():
    source = _source(DASHBOARD_PAGE)

    assert "@State pendingSceneId: number = -1" in source
    assert "isSafetySensitiveScene(scene: Scene): boolean" in source
    assert "requestScene(sceneId: number): void" in source
    assert "this.buildSceneConfirmation()" in source


def test_dashboard_marks_stale_sync_state_and_limits_recent_activity():
    source = _source(DASHBOARD_PAGE)

    assert "@State lastSyncedAt: number = 0" in source
    assert "syncStatusLabel(): string" in source
    assert "数据可能延迟" in source
    assert "this.recentLogs.slice(0, 3)" in source


def test_device_remote_uses_real_power_actions_and_writes_humidifier_changes_back():
    source = _source(DEVICE_REMOTE_PAGE)

    ac_panel = source.split("@Builder buildAcPanel() {", 1)[1].split("@Builder buildLockPanel()", 1)[0]
    ac_power_button = ac_panel.split("this.buildPrimaryButton(this.acOn ? '关闭空调' : '开启空调'", 1)[1].split("})", 1)[0]
    humidifier_panel = source.split("@Builder buildHumidifierPanel() {", 1)[1].split("@Builder buildMetricCard(", 1)[0]

    assert "this.cmdCurrent('on', p)" in ac_power_button
    assert "p.target_humidity = this.huTg" in humidifier_panel
    assert "this.queueSliderCommand(current.id, 'set', p)" in humidifier_panel


def test_crypto_util_handles_sym_key_generation_exceptions_for_arkts_compiler():
    source = _source(CRYPTO_UTIL)
    create_sym_key = source.split("async function createSymKey(keyBase64: string): Promise<cryptoFramework.SymKey> {", 1)[1] \
        .split("export async function aesEncrypt", 1)[0]

    assert "try {" in create_sym_key
    assert "cryptoFramework.createSymKeyGenerator('AES256')" in create_sym_key
    assert "await keyGenerator.convertKey(keyBlob)" in create_sym_key
    assert "throw err" in create_sym_key or "throw new Error(" in create_sym_key
