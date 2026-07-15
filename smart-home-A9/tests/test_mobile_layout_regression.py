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


def test_login_page_uses_scroll_and_mijia_style_brand_hierarchy():
    login_source = LOGIN_PAGE.read_text(encoding="utf-8")
    theme_source = THEME_FILE.read_text(encoding="utf-8")

    assert "Scroll()" in login_source
    assert "Text('智居')" in login_source
    assert "Text('连接家的每一刻')" in login_source
    assert "ControlCenterTheme.loginAccent" in login_source
    assert "static readonly loginAccent: string = '#07C160'" in theme_source
    assert "static readonly loginAccentSoft: string = '#E8F8EE'" in theme_source
    assert "其他方式登录" not in login_source


def test_dashboard_hero_does_not_render_four_top_action_buttons_anymore():
    source = DASHBOARD_PAGE.read_text(encoding="utf-8")

    assert source.count("this.heroIconButton(") <= 3


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

    for path in (DASHBOARD_PAGE, DEVICE_MANAGE_PAGE, RULES_PAGE, PROFILE_PAGE):
        source = path.read_text(encoding="utf-8")
        assert "AppBottomNav" in source


def test_registration_page_uses_the_shared_visual_system_and_scrolls_with_keyboard():
    source = REGISTER_PAGE.read_text(encoding="utf-8")

    assert "Scroll()" in source
    assert "ControlCenterTheme" in source
    assert "StatusBanner" in source


def test_profile_account_switch_label_matches_the_logout_based_flow():
    source = PROFILE_PAGE.read_text(encoding="utf-8")

    assert "Button('退出当前账号并登录其他账号')" in source
