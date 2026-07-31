# UTC 时间统一显示设计

## 目标

OpenHarmony 客户端中的业务时间统一按 UTC 显示，并明确标注 `UTC`，避免模拟器本地时区与后端 SQLite UTC 时间混用。后端接口和数据库字段保持不变。

## 范围

- 设备最近上报时间：`MM-DD HH:mm UTC`
- 数据监测历史记录和运行日志：`MM-DD HH:mm UTC`
- 首页活动日志：`MM-DD HH:mm UTC`
- 首页最近同步时间：`HH:mm UTC`
- 桌面服务卡片更新时间：`HH:mm UTC`
- 历史记录查询起始参数：使用 UTC 的 `YYYY-MM-DD HH:mm:ss`

登录、认证令牌时间戳、MQTT 消息时间戳和后端数据库结构不在本次修改范围内。

## 设计

新增 `common/UtcTimeUtil.ets`，集中提供以下纯函数：

- `formatUtcTimestamp(value, fallback)`：解析 SQLite 的 `YYYY-MM-DD HH:mm:ss`、ISO 8601 `Z` 时间和带偏移时间，统一输出 `MM-DD HH:mm UTC`。
- `formatUtcClock(date)`：输出 `HH:mm UTC`。
- `toUtcApiTimestamp(date)`：输出后端历史查询使用的 `YYYY-MM-DD HH:mm:ss`。

SQLite 无时区字符串按 UTC 解析。无效或空时间不抛异常：空值返回调用方提供的 fallback，无法解析的非空值返回原字符串，保证旧数据仍可见。

页面只调用公共工具，不再自行截取时间字符串或使用本地 `getHours()`。修改点包括：

- `DashboardPage.ets`
- `DeviceManagePage.ets`
- `DataMonitorPage.ets`
- `EntryFormAbility.ets`

`WidgetCard.ets` 继续展示 `EntryFormAbility` 写入的格式化结果，无需改动。

## 数据流

1. 后端继续返回当前时间字段。
2. API 模型保持原始字符串。
3. 页面渲染时调用 `UtcTimeUtil` 转换并添加 `UTC` 标识。
4. 历史查询从当前绝对时间减去范围时长，再序列化为 UTC 参数。

## 错误处理

- 空值使用当前页面已有的提示文案，例如“等待首次上报”。
- 无效非空值保留原始文本，避免界面空白。
- 格式化函数不修改全局时区，也不依赖设备时区。

## 测试

1. 先新增失败的 Python 回归测试，要求公共工具存在、包含 UTC 解析和格式化契约，并要求四个调用点导入该工具。
2. 实现后运行 UTC 定向测试及现有前端回归测试。
3. 使用 Hvigor 构建 OpenHarmony 应用，验证 ArkTS 类型与 API 兼容性。
4. 在模拟器中检查首页、设备页、数据历史、运行日志和桌面服务卡片，确认显示带 `UTC` 且不再混用本地小时。

## 验收标准

- 所有用户可见的业务时间均明确带 `UTC`。
- SQLite 时间、ISO 时间和带偏移时间转换结果一致。
- 历史查询范围以 UTC 生成。
- 原有页面布局、后端接口和数据库内容不变。
- 定向测试、前端回归测试和 OpenHarmony 构建全部通过。
