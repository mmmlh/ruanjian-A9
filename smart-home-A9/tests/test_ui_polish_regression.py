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


def section_between(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    assert start_index >= 0, f"missing {start}"
    end_index = text.find(end, start_index + len(start))
    assert end_index >= 0, f"missing {end} after {start}"
    return text[start_index:end_index]


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


def test_auth_forms_use_visible_labels_and_shared_control_geometry():
    login = source("LoginPage.ets")
    register = source("RegisterPage.ets")

    for label in ["用户名", "密码"]:
        assert f"Text('{label}')" in login
    login_user = section_between(login, "TextInput({ placeholder: '请输入用户名'", "Text('密码')")
    login_password = section_between(login, "TextInput({ placeholder: '请输入密码'", "if (this.err)")
    login_submit = section_between(login, "Button(this.loading ? '登录中...' : '登录')", "Row() {")
    for control in [login_user, login_password, login_submit]:
        assert ".height(ControlCenterTheme.controlHeight)" in control
    assert ".height(50)" not in login
    assert ".height(52)" not in login

    for label in ["用户名", "密码", "确认密码"]:
        assert f"Text('{label}')" in register
    register_user = section_between(register, "TextInput({ placeholder: '请输入用户名'", "Text('密码')")
    register_password = section_between(register, "TextInput({ placeholder: '请输入密码（至少 6 位）'", "Text('确认密码')")
    register_confirm = section_between(register, "TextInput({ placeholder: '请再次输入密码'", "if (this.err)")
    register_submit = section_between(register, "Button(this.loading ? '注册中...' : '创建账号')", "Row() {")
    for control in [register_user, register_password, register_confirm, register_submit]:
        assert ".height(ControlCenterTheme.controlHeight)" in control
    assert ".height(52)" not in register


def test_auth_navigation_uses_accessible_native_buttons():
    login = source("LoginPage.ets")
    register = source("RegisterPage.ets")

    login_nav = section_between(login, "Button('立即注册')", ".margin({ top: 18 })")
    assert ".height(ControlCenterTheme.tapTarget)" in login_nav
    assert ".backgroundColor(Color.Transparent)" in login_nav
    assert "pushUrl({ url: 'pages/RegisterPage' })" in login_nav
    assert "Text(' 立即注册')" not in login

    register_nav = section_between(register, "Button('立即登录')", ".margin({ top: 18 })")
    assert ".height(ControlCenterTheme.tapTarget)" in register_nav
    assert ".backgroundColor(Color.Transparent)" in register_nav
    assert "getRouter().back()" in register_nav
    assert "Text(' 立即登录')" not in register


def test_dashboard_uses_shared_header_and_stable_chinese_category_marks():
    text = source("DashboardPage.ets")

    assert (
        "AppTopBar({ title: '我的家', subtitle: this.syncStatusLabel(), "
        "actionLabel: '刷新', onAction: () => this.rf() })" in text
    )
    for legacy_name in [
        "buildHomeHeader", "buildHeroCard", "heroIconButton", "buildHeroPortal",
        "buildOverviewSection", "buildSceneStrip", "buildMijiaBottomNav",
        "buildBottomNav", "bottomTab",
    ]:
        assert legacy_name not in text
    assert "SmartHomeLogoSmall" not in text

    for category_mark in [
        "case 'light': return '灯'",
        "case 'ac': return '空'",
        "case 'door_lock': return '锁'",
        "case 'temperature_sensor': return '温'",
        "case 'humidity_sensor': return '湿'",
        "case 'pir_sensor': return '人'",
        "case 'curtain': return '帘'",
        "case 'humidifier': return '雾'",
        "default: return '设'",
    ]:
        assert category_mark in text
    for scene_mark in [
        "'Home Mode': '家'", "'Away Mode': '离'", "'Sleep Mode': '眠'",
        "'回家模式': '家'", "'离家模式': '离'", "'睡眠模式': '眠'",
        "return '景'",
    ]:
        assert scene_mark in text

    emoji_escape = re.compile(r"\\uD83[0-9A-F]|\\u\{1F[0-9A-F]{3}\}|\\U0001F[0-9A-F]{3}", re.IGNORECASE)
    assert emoji_escape.search(text) is None


def test_dashboard_loading_content_keeps_fixed_navigation_visible():
    dashboard = source("DashboardPage.ets")

    loading = braced_section(dashboard, "@Builder buildLoading()")
    assert ".layoutWeight(1)" in loading
    assert ".height('100%')" not in loading


def test_dashboard_exposes_data_monitor_and_realtime_connection_status():
    dashboard = source("DashboardPage.ets")
    hero = braced_section(dashboard, "@Builder buildMijiaHomeHero()")
    kit = (COMMON / "ControlCenterKit.ets").read_text(encoding="utf-8")
    bottom_nav = braced_section(kit, "export struct AppBottomNav")

    monitor = section_between(hero, "Button('数据监测')", ".onClick(() => this.quickAction('pages/DataMonitorPage'))")
    assert ".height(ControlCenterTheme.tapTarget)" in monitor
    assert "Text(this.ok ? '实时连接正常' : '实时连接重连中')" in hero
    assert "firstDeviceIdByType" not in dashboard
    assert dashboard.count("AppTopBar(") == 1
    assert dashboard.count("AppBottomNav(") == 1
    assert bottom_nav.count("this.item(") == 4


def test_dashboard_refresh_ignores_duplicate_load_requests():
    dashboard = source("DashboardPage.ets")
    load = braced_section(dashboard, "async ld()")
    refresh = braced_section(dashboard, "rf()")

    assert "if (this.loading)" in load
    assert load.index("if (this.loading)") < load.index("this.loading = true")
    assert "this.ld()" in refresh


def test_dashboard_realtime_updates_replace_the_device_array():
    dashboard = source("DashboardPage.ets")
    update = braced_section(dashboard, "updateDeviceFromRealtime(topic: string")

    assert "let replacement = new Device()" in update
    for field in [
        "id", "room_id", "type", "name", "brand", "mqtt_topic", "status_json",
        "room_name", "updated_at", "last_seen_at", "status_summary", "online",
    ]:
        assert f"replacement.{field} = device.{field}" in update
    assert "replacement.status_json = JSON.stringify(mergedStatus)" in update
    assert "replacement.updated_at = now" in update
    assert "replacement.last_seen_at = now" in update
    assert "replacement.status_summary = ''" in update
    assert "replacement.online = true" in update
    assert "let updatedDevices: Device[] = this.devices.slice()" in update
    assert "updatedDevices[i] = replacement" in update
    assert "this.devices = updatedDevices" in update
    assert update.index("this.devices = updatedDevices") < update.index("this.syncClimate()")
    assert update.index("this.devices = updatedDevices") < update.index("this.recountOnline()")


def test_dashboard_scene_safety_checks_serialized_actions_with_name_fallback():
    dashboard = source("DashboardPage.ets")
    parser = braced_section(dashboard, "parseSceneActions")
    safety = braced_section(dashboard, "isSafetySensitiveScene")

    assert "JSON.parse(scene.actions_json)" in parser
    assert "Array.isArray(parsed)" in parser
    assert "as Array<Record<string, Object>>" in parser
    assert "as Record<string, Object>" in parser
    assert parser.count("actions.push(") >= 2
    assert "catch" in parser
    assert "this.parseSceneActions(scene)" in safety
    assert "['device_type']" in safety
    assert "['action']" in safety
    assert safety.count(".toLowerCase()") >= 2
    for value in ["door_lock", "security", "alarm"]:
        assert f"'{value}'" in safety
    for value in ["lock", "unlock", "arm", "disarm"]:
        assert f"'{value}'" in safety
    for name in ["离家", "安防", "门锁", "锁门"]:
        assert f"name.indexOf('{name}')" in safety


def test_dashboard_serializes_all_scene_execution_entry_points():
    dashboard = source("DashboardPage.ets")
    execute = braced_section(dashboard, "async ds")
    request = braced_section(dashboard, "requestScene")
    confirm = braced_section(dashboard, "confirmScene")
    card = braced_section(dashboard, "@Builder buildSceneQuickCard")
    confirmation = braced_section(dashboard, "@Builder buildSceneConfirmation")

    for method in [execute, request, confirm]:
        assert "if (this.exe >= 0)" in method
    assert execute.index("if (this.exe >= 0)") < execute.index("this.exe = sceneId")
    assert request.index("if (this.exe >= 0)") < request.index("let scene =")
    assert confirm.index("if (this.exe >= 0)") < confirm.index("let sceneId =")
    assert ".enabled(this.exe < 0)" in card
    assert ".opacity(this.exe < 0 ? 1 : 0.58)" in card
    card_click = braced_section(card, ".onClick(() =>")
    assert "if (this.exe < 0)" in card_click
    assert "this.requestScene(scene.id)" in card_click
    confirm_button = section_between(confirmation, "Button('确认执行')", ".onClick(() => this.confirmScene())")
    assert ".enabled(this.exe < 0)" in confirm_button


def test_device_modal_layers_do_not_displace_root_navigation():
    devices = source("DeviceManagePage.ets")

    device_build = braced_section(devices, "build()")
    assert "Stack() {" in device_build
    assert ".backgroundColor(ControlCenterTheme.overlay)" in device_build


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
    assert "actionType: 'add'" in top_bar_props
    assert "this.showAddFlow = true" in top_bar_props
    assert "this.scanCandidates(false)" in top_bar_props
    top_bar_component = braced_section(kit, "export struct AppTopBar")
    action_section = braced_section(top_bar_component, "if (this.actionLabel)")
    assert "height(ControlCenterTheme.tapTarget)" in action_section
    add_flow = braced_section(text, "if (this.showAddFlow)")
    assert "ForEach(this.discovered" in add_flow
    assert "Button('完成')" in add_flow
    done = section_between(add_flow, "Button('完成')", ".onClick(() => { this.showAddFlow = false })")
    assert ".height(ControlCenterTheme.tapTarget)" in done

    room_selector = braced_section(text, "@Builder roomSelector()")
    room_button = section_between(room_selector, "Button(room.name)", ".onClick(() => { this.bindRoomId = room.id })")
    assert ".height(ControlCenterTheme.tapTarget)" in room_button

    rescan = section_between(add_flow, "Button(this.scanning ? '扫描中...' : '重新扫描')", ".onClick(() => this.scanCandidates())")
    assert ".height(ControlCenterTheme.tapTarget)" in rescan

    bind = section_between(add_flow, "Button(this.binding && this.bindTargetId === candidate.id ? '绑定中...' : '绑定')", ".onClick(() => {")
    assert ".height(ControlCenterTheme.tapTarget)" in bind

    bound_view = braced_section(text, "if (!this.showAddFlow)")
    edit = section_between(bound_view, "Button('编辑')", ".onClick(() => this.oe(device))")
    delete = section_between(
        bound_view,
        "Button(this.deletingId === device.id ? '删除中...' : '删除')",
        ".onClick(() => { this.pendingDeleteId = device.id })",
    )
    for control in [edit, delete]:
        assert ".height(ControlCenterTheme.tapTarget)" in control
    assert ".onClick(() => this.doDel(device.id))" not in text


def test_device_bind_preserves_custom_name_and_serializes_bind_requests():
    text = source("DeviceManagePage.ets")
    add_flow = braced_section(text, "if (this.showAddFlow)")
    bind = braced_section(text, "async doBind")

    assert "if (this.bindTargetId !== candidate.id)" in add_flow
    assert ".enabled(!this.binding)" in add_flow
    assert "if (this.binding)" in bind
    assert bind.index("if (this.binding)") < bind.index("this.binding = true")


def test_device_discovery_ignores_duplicate_scan_requests():
    text = source("DeviceManagePage.ets")
    scan = braced_section(text, "async scanCandidates")

    assert "if (this.scanning)" in scan
    assert scan.index("if (this.scanning)") < scan.index("this.scanning = true")


def test_device_delete_dismisses_confirmation_before_async_request():
    text = source("DeviceManagePage.ets")
    delete_flow = braced_section(text, "async doDel")

    assert text.count("@State deletingId: number = -1") == 1
    assert "if (this.deletingId >= 0)" in delete_flow
    assert delete_flow.index("if (this.deletingId >= 0)") < delete_flow.index("this.deletingId = id")
    assert delete_flow.index("this.deletingId = id") < delete_flow.index("await deleteDevice(id)")
    assert delete_flow.index("this.pendingDeleteId = -1") < delete_flow.index("await deleteDevice(id)")
    assert "finally" in delete_flow
    assert "this.deletingId = -1" in delete_flow

    bound_view = braced_section(text, "if (!this.showAddFlow)")
    edit = section_between(bound_view, "Button('编辑')", ".onClick(() => this.oe(device))")
    delete = section_between(
        bound_view,
        "Button(this.deletingId === device.id ? '删除中...' : '删除')",
        ".onClick(() => { this.pendingDeleteId = device.id })",
    )
    assert ".enabled(this.deletingId < 0)" in edit
    assert ".enabled(this.deletingId < 0)" in delete


def test_device_add_flow_replaces_long_bound_list_while_open():
    text = source("DeviceManagePage.ets")
    bound_view = braced_section(text, "if (!this.showAddFlow)")

    assert "ForEach(this.devices" in bound_view
