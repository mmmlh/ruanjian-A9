from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "cloud" / "simulator-ui" / "public"


def read(relative: str) -> str:
    return (UI / relative).read_text(encoding="utf-8")


def test_simulator_console_static_entrypoint_exists():
    html = read("index.html")

    assert '<html lang="zh-CN">' in html
    assert '<link rel="stylesheet" href="./styles.css">' in html
    assert '<script src="./vendor/lucide.min.js"></script>' in html
    assert '<script type="module" src="./js/app.js"></script>' in html
    assert (UI / "vendor" / "lucide.min.js").stat().st_size > 10_000


def test_simulator_console_exposes_accessible_workbench_regions():
    html = read("index.html")

    for marker in [
        'id="startup-status"',
        'id="device-search"',
        'id="room-filter"',
        'id="type-filter"',
        'id="online-filter"',
        'id="device-list"',
        'id="device-inspector"',
        'id="event-collapse-button"',
        'id="event-list"',
        'id="toast-region" aria-live="polite"',
    ]:
        assert marker in html


def test_console_uses_only_the_frozen_browser_transport():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (UI / "js").glob("*.js")
    )

    for forbidden in [
        "mqtt://",
        "ws://localhost",
        "/api/auth/register",
        "sqlite",
        "DATABASE_URL",
    ]:
        assert forbidden not in combined

    config = read("js/config.js")
    for endpoint in [
        'ready: "/api/ready"',
        'login: "/api/login"',
        'states: "/api/states"',
        'logs: "/api/data/logs?limit=100"',
        'realtime: "/ws/realtime"',
    ]:
        assert endpoint in config

    assert "fetch(" not in read("js/app.js")
    assert "new WebSocket" not in read("js/app.js")


def test_console_has_controller_and_read_only_sensor_views():
    app = read("js/app.js")

    for device_type in ["light", "ac", "door_lock", "curtain", "humidifier"]:
        assert f'case "{device_type}"' in app
    for device_type in ["temperature_sensor", "humidity_sensor", "pir_sensor"]:
        assert device_type in app

    assert "只读传感器" in app
    assert "buildCommand" in app
    assert "EVENT_LIMIT" in app
    assert "STATE_POLL_INTERVAL_MS" in app
    assert ".innerHTML" not in app

    for instructional_copy in [
        "设备状态和控制项会显示在这里",
        "数据由 Python 模拟器自动生成",
        "参数确认后统一发送",
        "启用时随命令一并发送",
    ]:
        assert instructional_copy not in app


def test_console_styles_define_stable_responsive_workbench():
    css = read("styles.css")

    assert "grid-template-columns: minmax(0, 1fr) 300px" in css
    assert "grid-template-rows: 50px minmax(0, 1fr) 164px" in css
    assert "@media (max-width: 820px)" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "font-size: clamp(" not in css
    assert "radial-gradient" not in css
    assert "linear-gradient" not in css

    radii = [int(value) for value in re.findall(r"border-radius:\s*(\d+)px", css)]
    assert radii
    assert max(radii) <= 8


def test_console_icon_buttons_are_named():
    html = read("index.html")
    icon_buttons = re.findall(
        r'<button[^>]*class="[^"]*icon-button[^"]*"[^>]*>',
        html,
    )

    assert icon_buttons
    for button in icon_buttons:
        assert "title=" in button
        assert "aria-label=" in button
