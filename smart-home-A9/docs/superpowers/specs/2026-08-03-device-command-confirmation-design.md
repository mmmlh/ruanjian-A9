# 17 台模拟设备真实执行闭环设计

## 目标

让现有 17 台 Python 模拟设备以与真实 MQTT 硬件相同的协议完成上线、能力声明、心跳、命令执行和执行确认。后端只在收到设备确认后更新设备的最终状态。

## 范围

- 覆盖现有 17 台设备，不处理已绑定但没有模拟器的 18--20 号设备。
- 保留现有 REST、场景、规则和 Home Assistant 兼容入口。
- 为未来真实硬件提供公开、稳定的 MQTT 主题与 JSON 载荷约定。

## MQTT 协议

设备根主题保持为 `home/{room}/{device_type}`。

- `{root}/hello`：设备启动后上报 `hardware_id`、`protocol_version` 和 `capabilities`。
- `{root}/heartbeat`：设备每 30 秒上报 `hardware_id` 和时间戳。
- `{root}/command`：后端下发 `command_id`、`action` 和 `params`。
- `{root}/ack`：设备对每条命令回复同一 `command_id`，并携带 `success`、`state` 和可选 `error_code`。
- 现有 `{root}/sensor`、`{root}/status` 和 `{root}/response` 继续被后端接收，以保持旧设备和旧客户端兼容。

## 数据模型

`devices` 增加：`hardware_id`、`protocol_version`、`capabilities_json`、`last_seen_at` 和 `connection_state`。

新增 `device_commands`：`command_id`、`device_id`、`action`、`params_json`、`status`、`sent_at`、`acknowledged_at`、`response_json`、`error_code` 和 `attempt_count`。状态仅允许 `pending`、`acknowledged`、`failed`、`timed_out`。

`status_json` 只存设备已确认状态；发布命令不会立即修改它。`last_seen_at` 只由 hello、heartbeat、sensor、status 或 ack 更新。

## 后端行为

1. 接收 hello 时按 `mqtt_topic` 找到已有设备，校验硬件编号，保存能力和连接信息；未知设备不自动建库。
2. 下发指令前，以设备的能力声明校验动作和参数；创建 `pending` 指令记录并发布带 `command_id` 的命令。
3. 收到 ack 时以 `command_id` 匹配指令。成功时更新指令、确认状态和最后在线时间；失败时只更新指令失败原因，不伪造设备状态。
4. 指令超过固定时限仍为 `pending` 时，在查询和新命令前标记为 `timed_out`。
5. 场景和规则复用同一个下发服务，因此同样获得可追踪命令记录。

## 17 台设备能力

- 温度传感器：上报温度；`set_config` 调整采样间隔、校准值、上报开关。
- 湿度传感器：上报湿度；`set_config` 调整采样间隔、校准值、上报开关。
- PIR：上报有人/无人；`set_config` 调整检测间隔、上报开关。
- 灯：`on`、`off`、`set`，参数为 brightness 和 color。
- 空调：`on`、`off`、`set`，参数为 mode、temp、fan 和 swing。
- 门锁：`lock`、`unlock`，解锁需要 auth_code。
- 窗帘：`open`、`close`、`set(position)`；状态包含 motion。
- 加湿器：`on`、`off`、`set(level, target_humidity)`；状态包含 water_level。

## 验证

- 后端测试覆盖 hello、heartbeat、ACK 成功、ACK 失败、超时及不应提前更新 status_json。
- 模拟器单元测试覆盖能力声明和每种设备的成功、失败回执。
- Docker 运行后通过 MQTT 命令检查 17 台设备都返回带 command_id 的 ACK，并核对数据库指令状态与设备状态。
