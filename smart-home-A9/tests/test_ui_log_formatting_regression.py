from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets"
MONITOR_PAGE = ROOT / "openharmony/entry/src/main/ets/pages/DataMonitorPage.ets"


def test_dashboard_page_does_not_render_raw_log_detail_directly():
    source = DASHBOARD_PAGE.read_text(encoding="utf-8")

    assert "Text(item.detail || 'Command executed successfully')" not in source
    assert "formatLogDetail(item)" in source


def test_data_monitor_page_does_not_render_raw_log_detail_directly():
    source = MONITOR_PAGE.read_text(encoding="utf-8")

    assert "Text(item.detail)" not in source
    assert "formatLogDetail(item)" in source


def test_data_monitor_supports_a_time_range_and_history_summary():
    api_source = (ROOT / "openharmony/entry/src/main/ets/common/ApiClient.ets").read_text(encoding="utf-8")
    source = MONITOR_PAGE.read_text(encoding="utf-8")

    assert "start?: string" in api_source
    assert "@State historyHours: number = 24" in source
    assert "this.rangeChip('24小时'" in source
    assert "this.rangeChip('7天'" in source
    assert "this.historySummary()" in source


def test_data_monitor_surfaces_a_human_readable_environment_alert():
    source = MONITOR_PAGE.read_text(encoding="utf-8")

    assert "historyInsight(): string" in source
    assert "湿度偏低" in source
    assert "温度偏高" in source
    assert "this.historyInsight()" in source
