from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME_FILE = ROOT / "openharmony/entry/src/main/ets/common/ControlCenterTheme.ets"
KIT_FILE = ROOT / "openharmony/entry/src/main/ets/common/ControlCenterKit.ets"
PAGES = {
    "DashboardPage": ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets",
    "DeviceRemotePage": ROOT / "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets",
    "RulesPage": ROOT / "openharmony/entry/src/main/ets/pages/RulesPage.ets",
    "LoginPage": ROOT / "openharmony/entry/src/main/ets/pages/LoginPage.ets",
}

INTERIOR_PAGES = {
    "DashboardPage": ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets",
    "DeviceManagePage": ROOT / "openharmony/entry/src/main/ets/pages/DeviceManagePage.ets",
    "DeviceRemotePage": ROOT / "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets",
    "RulesPage": ROOT / "openharmony/entry/src/main/ets/pages/RulesPage.ets",
    "DataMonitorPage": ROOT / "openharmony/entry/src/main/ets/pages/DataMonitorPage.ets",
    "ProfilePage": ROOT / "openharmony/entry/src/main/ets/pages/ProfilePage.ets",
}


def test_control_center_theme_and_kit_exist_with_shared_tokens():
    assert THEME_FILE.exists(), "expected a shared OpenHarmony control-center theme file"
    assert KIT_FILE.exists(), "expected shared UI helper components for the control-center redesign"

    theme_source = THEME_FILE.read_text(encoding="utf-8")
    kit_source = KIT_FILE.read_text(encoding="utf-8")

    assert "export class ControlCenterTheme" in theme_source
    assert "static readonly pageBg" in theme_source
    assert "static readonly heroBg" in theme_source
    assert "static readonly accent" in theme_source
    assert "export struct SectionTitle" in kit_source
    assert "export struct StatusBanner" in kit_source
    assert "export struct MetricChip" in kit_source


def test_core_pages_use_shared_theme_or_kit_instead_of_only_local_color_constants():
    for name, path in PAGES.items():
        source = path.read_text(encoding="utf-8")
        assert "ControlCenterTheme" in source or "StatusBanner" in source or "SectionTitle" in source, (
            f"{name} should use the shared control-center visual system"
        )


def test_interior_pages_share_the_mijia_style_green_theme():
    theme_source = THEME_FILE.read_text(encoding="utf-8")

    assert "static readonly pageBg: string = '#F4F6F5'" in theme_source
    assert "static readonly accent: string = '#14875B'" in theme_source
    assert "static readonly accentSoft: string = '#E4F3EC'" in theme_source

    for name, path in INTERIOR_PAGES.items():
        source = path.read_text(encoding="utf-8")
        assert "ControlCenterTheme" in source, f"{name} should use the shared interior visual theme"


def test_dashboard_uses_the_compact_shared_hierarchy():
    dashboard_source = INTERIOR_PAGES["DashboardPage"].read_text(encoding="utf-8")

    assert (
        "AppTopBar({ title: '我的家', subtitle: this.syncStatusLabel(), "
        "actionLabel: '刷新', onAction: () => this.rf() })" in dashboard_source
    )
    assert "this.buildSceneQuickCard(" in dashboard_source
    for legacy_name in [
        "buildHomeHeader", "buildHeroCard", "heroIconButton", "buildHeroPortal",
        "buildOverviewSection", "buildSceneStrip", "buildMijiaBottomNav",
        "buildBottomNav", "bottomTab",
    ]:
        assert legacy_name not in dashboard_source


def test_device_management_uses_semantic_shared_controls():
    source = INTERIOR_PAGES["DeviceManagePage"].read_text(encoding="utf-8")

    for component in ["AppTopBar", "AppBottomNav", "StatusBanner", "EmptyState", "ConfirmPanel"]:
        assert component in source
    assert "AppTopBar({ title: '设备'" in source
    assert "actionLabel: '添加设备'" in source
    assert "actionType: 'add'" in source
    assert "Button('编辑')" in source
    assert "Button(this.deletingId === device.id ? '删除中...' : '删除')" in source
    assert "ControlCenterTheme.tapTarget" in source
    assert "ControlCenterTheme.controlHeight" in source
    assert "ControlCenterTheme.overlay" in source
    assert "DEVICE_ACTION_PRIMARY" not in source
    assert "DEVICE_ACTION_SECONDARY_BG" not in source
    assert "DEVICE_ACTION_SECONDARY_FG" not in source


def test_device_management_hides_mqtt_topics_and_uses_accessible_bind_target():
    source = INTERIOR_PAGES["DeviceManagePage"].read_text(encoding="utf-8")

    assert "Text(candidate.mqtt_topic)" not in source
    assert "height(ControlCenterTheme.tapTarget)" in source
