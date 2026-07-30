import re
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "openharmony/entry/src/main/ets/pages"
COMMON = ROOT / "openharmony/entry/src/main/ets/common"
MEDIA = ROOT / "openharmony/entry/src/main/resources/base/media"


def source(name: str) -> str:
    return (PAGES / name).read_text(encoding="utf-8")


def braced_section(text: str, marker: str) -> str:
    marker_index = text.find(marker)
    assert marker_index >= 0, f"missing {marker}"
    brace_index = text.find("{", marker_index + len(marker))
    assert brace_index >= 0, f"missing block for {marker}"
    depth = 0
    for index in range(brace_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[marker_index:index + 1]
    raise AssertionError(f"unterminated block for {marker}")


def test_compact_semantic_theme_and_shared_components_exist():
    theme = (COMMON / "ControlCenterTheme.ets").read_text(encoding="utf-8")
    kit = (COMMON / "ControlCenterKit.ets").read_text(encoding="utf-8")

    bottom_nav = braced_section(kit, "export struct AppBottomNav")
    nav_item = braced_section(bottom_nav, "private item")
    assert "Button() {" in nav_item
    assert "height(ControlCenterTheme.tapTarget)" in nav_item
    assert ".accessibilityText(this.active === key ? label + '，当前页面' : label)" in nav_item
    assert (
        ".fontColor(this.active === key ? ControlCenterTheme.textPrimary : "
        "ControlCenterTheme.textSecondary)" in nav_item
    )

    top_bar = braced_section(kit, "export struct AppTopBar")
    assert "@Prop actionType: string = 'refresh'" in top_bar
    back_action = braced_section(top_bar, "if (this.showBack)")
    assert "Button() {" in back_action
    assert ".accessibilityText('返回')" in back_action
    assert ".onClick(() => this.getUIContext().getRouter().back())" in back_action
    top_bar_action = braced_section(top_bar, "if (this.actionLabel)")
    assert "Button() {" in top_bar_action
    assert "if (this.actionType === 'add')" in top_bar_action
    assert "this.actionLabel ===" not in top_bar_action
    icon_mapping = re.search(
        r"if \(this\.actionType === 'add'\) \{(?P<add>.*?)\} else \{(?P<refresh>.*?)\}",
        top_bar_action,
        re.DOTALL,
    )
    assert icon_mapping is not None
    assert "$r('app.media.action_add')" in icon_mapping.group("add")
    assert "$r('app.media.action_refresh')" not in icon_mapping.group("add")
    assert "$r('app.media.action_refresh')" in icon_mapping.group("refresh")
    assert "$r('app.media.action_add')" not in icon_mapping.group("refresh")
    assert ".fontColor(ControlCenterTheme.textPrimary)" in top_bar_action
    assert ".accessibilityText(this.actionLabel)" in top_bar_action
    assert ".onClick(() => this.onAction())" in top_bar_action

    assert "export struct PrimaryButton" in kit
    assert "export struct SecondaryButton" in kit
    primary_button = braced_section(kit, "export struct PrimaryButton")
    secondary_button = braced_section(kit, "export struct SecondaryButton")
    assert "height(ControlCenterTheme.tapTarget)" in primary_button
    assert ".fontSize(14)" in primary_button
    assert ".fontWeight(FontWeight.Bold)" in primary_button
    assert "height(ControlCenterTheme.tapTarget)" in secondary_button

    empty_state = braced_section(kit, "export struct EmptyState")
    assert "@Prop actionLabel: string = ''" in empty_state
    assert "@Prop actionEnabled: boolean = true" in empty_state
    assert "@Prop onAction: () => void = () => {}" in empty_state
    empty_action = braced_section(empty_state, "if (this.actionLabel)")
    assert "Button(this.actionLabel)" in empty_action
    assert ".height(ControlCenterTheme.tapTarget)" in empty_action
    assert ".enabled(this.actionEnabled)" in empty_action
    assert ".onClick(() => this.onAction())" in empty_action

    confirm_panel = braced_section(kit, "export struct ConfirmPanel")
    confirm_detail = braced_section(confirm_panel, "if (this.detail)")
    assert ".fontColor(ControlCenterTheme.textPrimary)" in confirm_detail

    section_title = braced_section(kit, "export struct SectionTitle")
    trailing = braced_section(section_title, "if (this.trailing)")
    assert ".fontColor(ControlCenterTheme.textPrimary)" in trailing

    status_banner = braced_section(kit, "export struct StatusBanner")
    tone_label = braced_section(status_banner, "private toneLabel")
    for label in ["成功", "警告", "错误", "提示"]:
        assert f"return '{label}'" in tone_label
    assert status_banner.index("Text(this.toneLabel())") < status_banner.index("Text(this.message)")
    assert status_banner.count(".fontColor(ControlCenterTheme.textPrimary)") >= 3
    assert ".opacity(0.72)" not in status_banner

    metric_chip = braced_section(kit, "export struct MetricChip")
    label_color = braced_section(metric_chip, "private labelColor")
    assert (
        "return this.inverse ? ControlCenterTheme.textOnDarkMuted : "
        "ControlCenterTheme.textPrimary" in label_color
    )

    assert ".fontSize(11)" not in kit
    assert "static readonly pageBg: string = '#F4F6F5'" in theme
    assert "static readonly accent: string = '#14875B'" in theme
    assert "static readonly radiusCard: number = 8" in theme
    assert "export struct AppTopBar" in kit
    assert "export struct EmptyState" in kit
    assert "export struct ConfirmPanel" in kit


def test_navigation_and_action_svg_assets_are_bundled():
    names = [
        "nav_home.svg", "nav_devices.svg", "nav_automation.svg", "nav_profile.svg",
        "action_back.svg", "action_add.svg", "action_refresh.svg",
    ]
    kit = (COMMON / "ControlCenterKit.ets").read_text(encoding="utf-8")
    for name in names:
        path = MEDIA / name
        assert path.is_file(), f"{name} is not bundled"
        text = path.read_text(encoding="utf-8")
        svg_text = text.lstrip("\ufeff")
        assert svg_text.startswith("<svg")
        svg = ElementTree.fromstring(svg_text)
        assert svg.tag.rsplit("}", 1)[-1] == "svg"
        assert svg.attrib.get("viewBox") == "0 0 24 24"
        assert svg.attrib.get("fill") == "none"
        assert svg.attrib.get("stroke") == "#14875B"
        assert svg.attrib.get("stroke-width") == "1.8"
        assert svg.attrib.get("stroke-linecap") == "round"
        assert svg.attrib.get("stroke-linejoin") == "round"
        assert f"$r('app.media.{path.stem}')" in kit


def test_root_pages_use_root_navigation_without_back_controls():
    expected = {
        "DashboardPage.ets": "home",
        "DeviceManagePage.ets": "devices",
        "RulesPage.ets": "automation",
        "ProfilePage.ets": "profile",
    }
    for name, active in expected.items():
        text = source(name)
        assert f"AppBottomNav({{ active: '{active}' }})" in text
        assert f"AppTopBar({{ title:" in text
        assert "showBack: true" not in text
        assert "getRouter().back()" not in text
        assert "app.media.action_back" not in text


def test_destructive_flows_have_explicit_confirmation_state():
    devices = source("DeviceManagePage.ets")
    rules = source("RulesPage.ets")
    profile = source("ProfilePage.ets")

    assert "@State pendingDeleteId: number = -1" in devices
    assert "this.pendingDeleteId = device.id" in devices
    assert "this.doDel(this.pendingDeleteId)" in devices
    assert "onConfirm: () => this.doDel(this.pendingDeleteId)" in devices
    assert ".onClick(() => this.doDel(device.id))" not in devices
    assert "ConfirmPanel" in devices

    assert "@State pendingDeleteId: number = -1" in rules
    assert "this.pendingDeleteId = rule.id" in rules
    assert "this.dD(this.pendingDeleteId)" in rules
    assert "onConfirm: () => this.dD(this.pendingDeleteId)" in rules
    assert ".onClick(() => this.dD(rule.id))" not in rules
    assert "ConfirmPanel" in rules

    assert "@State confirmLogout: boolean = false" in profile
    assert "this.confirmLogout = true" in profile
    assert "onConfirm: () => this.doOut()" in profile
    assert ".onClick(() => this.doOut())" not in profile
    assert "ConfirmPanel" in profile


def test_user_facing_pages_do_not_contain_development_copy_or_emoji_escapes():
    forbidden = ["便于答辩", "更像完整产品", "长 JSON"]
    emoji_pattern = re.compile(
        r"\\uD83[0-9A-F]|\\u\{1F[0-9A-F]{3}\}|\\U0001F[0-9A-F]{3}|"
        r"[\U0001F300-\U0001FAFF]",
        re.IGNORECASE,
    )
    for path in PAGES.glob("*.ets"):
        text = path.read_text(encoding="utf-8")
        for item in forbidden:
            assert item not in text, f"{path.name} still contains {item}"
        match = emoji_pattern.search(text)
        assert match is None, f"{path.name} still contains emoji {match.group(0)!r}"


def test_device_add_flow_is_secondary_and_touch_targets_are_accessible():
    text = source("DeviceManagePage.ets")
    kit = (COMMON / "ControlCenterKit.ets").read_text(encoding="utf-8")
    assert "@State showAddFlow: boolean = false" in text
    assert "if (this.showAddFlow)" in text
    ld_section = re.search(
        r"async ld\(\): Promise<void>(.*?)async scanCandidates",
        text,
        re.DOTALL,
    )
    assert ld_section is not None, "DeviceManagePage.ets must define ld before scanCandidates"
    assert "scanCandidates" not in ld_section.group(1)
    top_bar_call = re.search(r"AppTopBar\(\{(.*?)\}\)", text, re.DOTALL)
    assert top_bar_call is not None, "DeviceManagePage.ets must use AppTopBar"
    top_bar_props = top_bar_call.group(1)
    assert "actionLabel: '添加设备'" in top_bar_props
    assert "this.showAddFlow = true" in top_bar_props
    assert "this.scanCandidates(false)" in top_bar_props
    top_bar_component = braced_section(kit, "export struct AppTopBar")
    action_section = braced_section(top_bar_component, "if (this.actionLabel)")
    assert "height(ControlCenterTheme.tapTarget)" in action_section
    add_flow = braced_section(text, "if (this.showAddFlow)")
    assert "ForEach(this.discovered" in add_flow
