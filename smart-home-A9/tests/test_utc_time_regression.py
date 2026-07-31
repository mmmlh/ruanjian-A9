import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UTC_UTIL = ROOT / "openharmony/entry/src/main/ets/common/UtcTimeUtil.ets"
DASHBOARD = ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets"
DEVICES = ROOT / "openharmony/entry/src/main/ets/pages/DeviceManagePage.ets"
MONITOR = ROOT / "openharmony/entry/src/main/ets/pages/DataMonitorPage.ets"
FORM_ABILITY = ROOT / "openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets"


def _run_utc_time_behavior_matrix() -> dict[str, str]:
    source = UTC_UTIL.read_text(encoding="utf-8")
    javascript = source.replace("export ", "")
    javascript = re.sub(r":\s*(?:number|string|Date)(?=\s*[,)=])", "", javascript)
    javascript = re.sub(r"\):\s*(?:string|Date\s*\|\s*null)(?=\s*\{)", ")", javascript)
    javascript += """
const offsetDate = new Date('2025-03-04T05:06:07+08:00')
const results = {
  sqliteWithoutSeconds: formatUtcTimestamp('2025-03-04 05:06'),
  sqliteWithSeconds: formatUtcTimestamp('2025-03-04 05:06:07'),
  zTimestamp: formatUtcTimestamp('2025-03-04T05:06:07Z'),
  millisecondZTimestamp: formatUtcTimestamp('2025-03-04T05:06:07.123Z'),
  microsecondZTimestamp: formatUtcTimestamp('2025-03-04T05:06:07.123456Z'),
  positiveOffset: formatUtcTimestamp('2025-03-04T05:06:07+08:00'),
  fractionalPositiveOffset: formatUtcTimestamp('2025-03-04T05:06:07.123456+08:00'),
  negativeOffsetAcrossDay: formatUtcTimestamp('2025-03-04T23:30:00-02:00'),
  blankFallback: formatUtcTimestamp('   ', 'missing'),
  invalidCalendarDate: formatUtcTimestamp('2025-02-30 05:06:07'),
  invalidZCalendarDate: formatUtcTimestamp('2025-02-30T05:06:07Z'),
  invalidOffsetCalendarDate: formatUtcTimestamp('2025-02-30T05:06:07+08:00'),
  invalidFractionalCalendarDate: formatUtcTimestamp('2025-02-30T05:06:07.123456Z'),
  unsupportedFractionPrecision: formatUtcTimestamp('2025-03-04T05:06:07.1234567Z'),
  apiTimestamp: toUtcApiTimestamp(offsetDate),
  utcClock: formatUtcClock(offsetDate),
}
process.stdout.write(JSON.stringify(results))
"""
    node = shutil.which("node")
    assert node is not None, "node.exe is required for the ArkTS behavior regression test"
    completed = subprocess.run(
        [node, "-"],
        input=javascript,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def test_utc_time_utility_defines_display_and_api_contracts():
    assert UTC_UTIL.exists()

    source = UTC_UTIL.read_text(encoding="utf-8")

    assert "export function formatUtcTimestamp(" in source
    assert "export function formatUtcClock(" in source
    assert "export function toUtcApiTimestamp(" in source
    assert "getUTCMonth()" in source
    assert "getUTCDate()" in source
    assert "getUTCHours()" in source
    assert "getUTCMinutes()" in source
    assert " UTC" in source


def test_utc_time_utility_executes_behavior_matrix():
    results = _run_utc_time_behavior_matrix()

    assert results == {
        "sqliteWithoutSeconds": "03-04 05:06 UTC",
        "sqliteWithSeconds": "03-04 05:06 UTC",
        "zTimestamp": "03-04 05:06 UTC",
        "millisecondZTimestamp": "03-04 05:06 UTC",
        "microsecondZTimestamp": "03-04 05:06 UTC",
        "positiveOffset": "03-03 21:06 UTC",
        "fractionalPositiveOffset": "03-03 21:06 UTC",
        "negativeOffsetAcrossDay": "03-05 01:30 UTC",
        "blankFallback": "missing",
        "invalidCalendarDate": "2025-02-30 05:06:07",
        "invalidZCalendarDate": "2025-02-30T05:06:07Z",
        "invalidOffsetCalendarDate": "2025-02-30T05:06:07+08:00",
        "invalidFractionalCalendarDate": "2025-02-30T05:06:07.123456Z",
        "unsupportedFractionPrecision": "2025-03-04T05:06:07.1234567Z",
        "apiTimestamp": "2025-03-03 21:06:07",
        "utcClock": "21:06 UTC",
    }


def test_business_timestamp_displays_use_the_shared_utc_formatter():
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    devices = DEVICES.read_text(encoding="utf-8")
    monitor = MONITOR.read_text(encoding="utf-8")

    assert "import { formatUtcClock, formatUtcTimestamp } from '../common/UtcTimeUtil'" in dashboard
    assert "return formatUtcTimestamp(value, value)" in dashboard

    assert "import { formatUtcTimestamp } from '../common/UtcTimeUtil'" in devices
    assert re.search(
        r"static seenText\(value: string, fallback: string\): string \{\s*"
        r"if \(!value\) \{\s*return fallback\s*\}\s*"
        r"return '最近上报 ' \+ formatUtcTimestamp\(value, value\)\s*\}",
        devices,
    ) is not None
    assert "return '最近上报 ' + formatUtcTimestamp(value, value)" in devices

    assert "import { formatUtcTimestamp, toUtcApiTimestamp } from '../common/UtcTimeUtil'" in monitor
    assert "return formatUtcTimestamp(ts, ts)" in monitor

    for source in (dashboard, devices, monitor):
        assert "substring(5, 16)" not in source
