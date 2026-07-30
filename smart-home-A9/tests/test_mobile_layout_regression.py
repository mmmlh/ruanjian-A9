from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/LoginPage.ets"
DASHBOARD_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets"
REGISTER_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/RegisterPage.ets"
DEVICE_MANAGE_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DeviceManagePage.ets"
RULES_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/RulesPage.ets"
PROFILE_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/ProfilePage.ets"
LOGO_FILE = ROOT / "openharmony/entry/src/main/ets/common/SmartHomeLogo.ets"
THEME_FILE = ROOT / "openharmony/entry/src/main/ets/common/ControlCenterTheme.ets"
KIT_FILE = ROOT / "openharmony/entry/src/main/ets/common/ControlCenterKit.ets"


def test_login_page_uses_scroll_and_compact_shared_form_hierarchy():
    login_source = LOGIN_PAGE.read_text(encoding="utf-8")

    assert "Scroll()" in login_source
    assert "Text('智居')" in login_source
    assert "Text('连接家的每一刻')" in login_source
    assert "Text('用户名')" in login_source
    assert "Text('密码')" in login_source
    assert "ControlCenterTheme.pageBg" in login_source
    assert "ControlCenterTheme.surfaceMuted" in login_source
    assert "ControlCenterTheme.controlHeight" in login_source


def test_dashboard_uses_shared_top_bar_without_legacy_header_or_navigation():
    source = DASHBOARD_PAGE.read_text(encoding="utf-8")

    assert (
        "AppTopBar({ title: '我的家', subtitle: this.syncStatusLabel(), "
        "actionLabel: '刷新', onAction: () => this.rf() })" in source
    )
    assert "buildHomeHeader" not in source
    assert "heroIconButton" not in source
    assert "bottomTab" not in source


def test_root_pages_use_the_shared_four_item_bottom_navigation_outside_scroll_content():
    kit_source = KIT_FILE.read_text(encoding="utf-8")

    assert "export struct AppBottomNav" in kit_source
    assert "'首页'" in kit_source
    assert "'设备'" in kit_source
    assert "'自动化'" in kit_source
    assert "'我的'" in kit_source
    assert "let selected = this.active === key" not in kit_source
    assert "this.getUIContext().getRouter().replaceUrl" in kit_source
    assert "try {" in kit_source.split("private navigate", 1)[1].split("@Builder", 1)[0]
    for key, route in [
        ("home", "pages/DashboardPage"),
        ("devices", "pages/DeviceManagePage"),
        ("automation", "pages/RulesPage"),
        ("profile", "pages/ProfilePage"),
    ]:
        assert f"key === '{key}'" in kit_source
        assert f"route = '{route}'" in kit_source

    expected_active = {
        DASHBOARD_PAGE: "home",
        DEVICE_MANAGE_PAGE: "devices",
        RULES_PAGE: "automation",
        PROFILE_PAGE: "profile",
    }
    for path, active in expected_active.items():
        source = path.read_text(encoding="utf-8")
        assert f"AppBottomNav({{ active: '{active}' }})" in source


def test_registration_page_uses_the_shared_visual_system_and_scrolls_with_keyboard():
    source = REGISTER_PAGE.read_text(encoding="utf-8")

    assert "Scroll()" in source
    assert "ControlCenterTheme" in source
    assert "StatusBanner" in source
    assert "Text('用户名')" in source
    assert "Text('密码')" in source
    assert "Text('确认密码')" in source
    assert "ControlCenterTheme.controlHeight" in source


def test_profile_exposes_one_confirmed_logout_action():
    source = PROFILE_PAGE.read_text(encoding="utf-8")

    assert "退出当前账号并登录其他账号" not in source
    assert source.count("'退出登录'") == 1
    assert "Button(this.loggingOut ? '退出中...' : '退出登录')" in source
    assert ".onClick(() => { this.confirmLogout = true })" in source
    assert ".onClick(() => this.doOut())" not in source
