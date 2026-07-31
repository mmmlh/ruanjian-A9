from pathlib import Path


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
        'id="event-list"',
        'id="toast-region" aria-live="polite"',
    ]:
        assert marker in html
