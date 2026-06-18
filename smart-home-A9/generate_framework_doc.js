/**
 * 生成 A9 智能家居设备控制系统 — 项目框架文档 (Word)
 */
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType,
  TableLayoutType, ShadingType, PageBreak
} = require('docx');

// ── 辅助函数 ──
function heading(text, level = 1) {
  return new Paragraph({
    text,
    heading: HeadingLevel[`HEADING_${level}`],
    spacing: { before: level === 1 ? 300 : 200, after: 120 },
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 80, line: 360 },
    ...opts,
    children: [new TextRun({ text, size: 21, font: '微软雅黑', ...opts.run })],
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    spacing: { after: 40, line: 340 },
    bullet: { level },
    children: [new TextRun({ text, size: 20, font: '微软雅黑' })],
  });
}

function codeBlock(code) {
  const lines = code.trim().split('\n');
  return lines.map(line =>
    new Paragraph({
      spacing: { before: 0, after: 0, line: 260 },
      indent: { left: 360 },
      children: [new TextRun({ text: line || ' ', size: 17, font: 'Consolas', color: '2D2D2D' })],
    })
  );
}

function table(headers, rows) {
  const allRows = [
    new TableRow({
      tableHeader: true,
      children: headers.map(h =>
        new TableCell({
          shading: { type: ShadingType.SOLID, color: '1A3C6E' },
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: h, bold: true, size: 18, font: '微软雅黑', color: 'FFFFFF' })],
          })],
        })
      ),
    }),
    ...rows.map(row =>
      new TableRow({
        children: row.map(cell =>
          new TableCell({
            children: [new Paragraph({
              children: [new TextRun({ text: String(cell), size: 17, font: '微软雅黑' })],
            })],
          })
        ),
      })
    ),
  ];
  return new Table({
    rows: allRows,
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.AUTOFIT,
  });
}

function emptyPara() {
  return new Paragraph({ spacing: { after: 60 }, children: [] });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

// ═══════════════════════════════════════════════
//  文档内容
// ═══════════════════════════════════════════════
const children = [];

// ── 封面 ──
children.push(emptyPara(), emptyPara(), emptyPara());
children.push(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
    children: [new TextRun({ text: '第十五届"中国软件杯"大学生软件设计大赛', size: 36, bold: true, font: '微软雅黑', color: '1A3C6E' })],
  })
);
children.push(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
    children: [new TextRun({ text: 'A9 — 基于OpenHarmony的智能家居设备控制系统', size: 28, font: '微软雅黑', color: '2B579A' })],
  })
);
children.push(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 300 },
    children: [new TextRun({ text: '项 目 框 架 文 档', size: 44, bold: true, font: '微软雅黑', color: 'C0392B' })],
  })
);
children.push(emptyPara(), emptyPara());

// 封面信息表
const metaData = [
  ['项目名称', '基于OpenHarmony的智能家居设备控制系统'],
  ['赛题编号', 'A9（A组：本科/研究生/高职）'],
  ['出题企业', '苏州未来网络研究院有限公司'],
  ['文档版本', 'v1.0'],
  ['日期', '2026年05月20日'],
];
metaData.forEach(([k, v]) => {
  children.push(table([k, v], []));
  children.push(emptyPara());
});

children.push(pageBreak());

// ── 目录 ──
children.push(heading('目  录', 1));
const tocItems = [
  '一、项目概述',
  '二、赛题需求分析',
  '三、总体架构设计',
  '四、技术栈选型',
  '五、MQTT 主题设计',
  '六、数据库设计',
  '七、REST API 设计',
  '八、安全三层设计',
  '九、设备联动规则引擎',
  '十、多品牌空调兼容方案',
  '十一、项目文件结构',
  '十二、开发排期',
  '十三、部署方案',
];
tocItems.forEach(item => children.push(para(item)));
children.push(pageBreak());

// ── 一、项目概述 ──
children.push(heading('一、项目概述', 1));
children.push(para(
  '本项目为第十五届"中国软件杯"大学生软件设计大赛 A9 赛题——基于OpenHarmony操作系统的家居设备控制系统。系统采用云端模拟硬件 + OpenHarmony APP 的架构，将物联网设备（温湿度传感器、人体感应传感器、智能灯、空调、智能门禁）通过 Python 脚本在阿里云服务器上进行仿真模拟，通过 MQTT 协议与后端服务通信，最终由 OpenHarmony 原生应用（HAP）提供用户交互界面。'
));
children.push(heading('核心目标', 2));
[
  '实现照明中心：远程开关控制 + 人体感应自动开关灯',
  '实现温湿度控制中心：传感器数据采集 + 多品牌空调远程控制（海尔/格力/美的）',
  '实现智能门禁：APP 远程开锁/上锁',
  '实现设备联动：基于规则引擎的自动化场景（人来自动开灯、高温自动开空调等）',
  '实现三层安全加密：传输层 TLS + 数据层 AES + 密钥层 JWT',
  '提交完整作品：HAP 安装包 + 源码 + 设计文档 + PPT + 演示视频',
].forEach(g => children.push(bullet(g)));
children.push(emptyPara());

// ── 二、赛题需求分析 ──
children.push(heading('二、赛题需求分析', 1));
children.push(heading('2.1 功能需求对照', 2));
children.push(table(
  ['赛题要求', '实现方案', '技术路径'],
  [
    ['控制中心：国产主板+网关', '阿里云ECS模拟网关+Python设备模拟器\n文档说明对应国产主板方案', 'FastAPI + MQTT Broker'],
    ['照明中心：远程开关+人体感应', '灯模拟器订阅MQTT指令+PIR传感器\n发布状态，规则引擎联动', 'MQTT pub/sub + Rule Engine'],
    ['温湿度中心：传感器+多品牌空调', '温湿度模拟器定时上报+空调模拟器\n内置海尔/格力/美的指令翻译表', 'Brand Translator Pattern'],
    ['智能门禁：远程开锁/上锁', '门禁模拟器订阅MQTT+状态反馈\n加密认证码验证', 'MQTT + AES加密'],
    ['协议传输安全', 'TLS 1.3 + AES-256-CBC + JWT\n三层加密独立密钥', 'HTTPS + MQTT over TLS'],
  ]
));
children.push(emptyPara());

children.push(heading('2.2 评分标准', 2));
children.push(table(
  ['评分项', '分值', '我们的策略'],
  [
    ['功能完整度', '60分', '4大功能全部实现，设备模拟器覆盖所有硬件类型'],
    ['界面美观', '10分', '鸿蒙原生UI，卡片式布局，实时数据可视化'],
    ['可扩展性', '10分', '设备基类抽象，新增设备只需继承BaseDevice；规则引擎支持热加载'],
    ['协议安全性', '10分', 'TLS+AES+JWT 三层独立设计，演示时可抓包验证'],
    ['文档质量', '10分', '设计文档+使用手册+部署说明+代码注释完整'],
  ]
));
children.push(emptyPara());

// ── 三、总体架构设计 ──
children.push(heading('三、总体架构设计', 1));
children.push(heading('3.1 架构分层图', 2));
children.push(para(
  '系统采用四层架构：展示层（OpenHarmony APP）→ 云端服务层（FastAPI + 规则引擎 + 安全模块）→ 消息中间件层（MQTT Broker）→ 设备模拟层（Python 设备模拟器）。所有组件通过 Docker Compose 在阿里云 ECS 上一键部署。'
));
children.push(heading('3.2 架构分层说明', 2));
children.push(table(
  ['层级', '技术', '职责', '关键组件'],
  [
    ['展示层', 'ArkTS + DevEco Studio\nOpenHarmony SDK', '用户交互界面\n实时数据显示\n设备远程控制', 'DashboardPage\nLightControlPage\nACControlPage\nDoorLockPage'],
    ['云端服务层', 'Python 3.11 + FastAPI\n+ WebSocket', 'REST API\n用户认证\n规则引擎\n数据加密\n历史数据存储', 'auth.py\nrule_engine.py\nsecurity.py\nmqtt_client.py'],
    ['消息中间件', 'Mosquitto MQTT Broker\n端口1883/8883(TLS)', '设备消息路由\n发布/订阅管理\nQoS保障', 'docker-compose部署\nTLS证书配置'],
    ['设备模拟层', 'Python asyncio\n+ paho-mqtt', '模拟传感器数据\n响应控制指令\n状态上报', 'temperature_sensor.py\nac_controller.py\ndoor_lock.py等'],
  ]
));
children.push(emptyPara());

children.push(heading('3.3 数据流', 2));
children.push(para('上行数据流（传感器 → APP）：'));
[
  '设备模拟器定时生成传感器数据（温度/湿度/人体感应/设备状态）',
  '通过 paho-mqtt 客户端发布到 MQTT Broker 对应主题',
  'FastAPI 后端订阅 MQTT 主题，收到数据后：存入 SQLite + 触发规则引擎检查',
  '通过 WebSocket 推送给已连接的 OpenHarmony APP',
  'APP 收到实时数据，更新仪表盘/控制页面的 UI 状态',
].forEach(f => children.push(bullet(f)));

children.push(para('下行控制流（APP → 设备）：'));
[
  '用户在 OpenHarmony APP 上操作（开关灯/调空调/开门）',
  'APP 通过 HTTPS POST 发送指令到 FastAPI 后端',
  '后端验证 JWT 身份 → 加密敏感指令 → 通过 MQTT 发布到设备命令主题',
  '设备模拟器订阅命令主题，收到指令后执行模拟动作',
  '设备模拟器发布响应到状态主题 → 后端更新数据库 → WebSocket 通知 APP 更新 UI',
].forEach(f => children.push(bullet(f)));
children.push(emptyPara());

// ── 四、技术栈选型 ──
children.push(heading('四、技术栈选型', 1));
children.push(table(
  ['层级', '技术选型', '版本', '选型理由'],
  [
    ['APP开发', 'ArkTS + DevEco Studio', 'OpenHarmony SDK 4.x', '赛题强制要求，提交HAP包'],
    ['后端框架', 'FastAPI', '0.111+', '异步高性能，原生WebSocket，自动生成API文档'],
    ['消息队列', 'Mosquitto MQTT', '2.0+', 'IoT标准协议，轻量级，完善的TLS支持'],
    ['数据库', 'SQLite', '3.x', '开发期零配置，单文件存储，可随时迁移至MySQL'],
    ['设备模拟', 'Python asyncio + paho-mqtt', 'paho 1.6+', '异步并发模拟多设备，官方MQTT库'],
    ['加密', 'pycryptodome + PyJWT', '-', 'AES-256加解密 + JWT令牌管理'],
    ['部署', 'Docker + Docker Compose', '-', '一键部署，环境隔离，方便评委复现'],
    ['反向代理', 'Nginx', '-', 'HTTPS终端，反向代理FastAPI，负载均衡'],
  ]
));
children.push(emptyPara());

// ── 五、MQTT 主题设计 ──
children.push(heading('五、MQTT 主题设计', 1));
children.push(para(
  'MQTT 主题采用 home/{room_id}/{device_type}/{direction} 的分层结构，方向分为 sensor（上报）、status（状态）、command（指令）、response（响应）四类。'
));

children.push(heading('5.1 传感器数据上报主题', 2));
children.push(...codeBlock(`
# 温度传感器 — 每5秒上报一次
主题: home/{room_id}/sensor/temperature
载荷: {"value": 26.5, "unit": "celsius", "device_id": "temp_001", "ts": 1716200000}

# 湿度传感器 — 每5秒上报一次
主题: home/{room_id}/sensor/humidity
载荷: {"value": 65.0, "unit": "percent", "device_id": "hum_001", "ts": 1716200000}

# 人体感应传感器 — 状态变化时上报
主题: home/{room_id}/sensor/pir
载荷: {"presence": true, "device_id": "pir_001", "ts": 1716200000}
`));

children.push(heading('5.2 设备状态上报主题', 2));
children.push(...codeBlock(`
# 灯光状态
主题: home/{room_id}/light/status
载荷: {"power": "on", "brightness": 80, "color": "warm", "device_id": "light_001"}

# 空调状态
主题: home/{room_id}/ac/status
载荷: {"power": "on", "mode": "cool", "temp": 24, "fan": "auto", "brand": "gree",
       "device_id": "ac_001", "ts": 1716200000}

# 门禁状态
主题: home/{room_id}/door/status
载荷: {"locked": true, "device_id": "door_001", "ts": 1716200000}
`));

children.push(heading('5.3 控制指令主题', 2));
children.push(...codeBlock(`
# 灯控指令
主题: home/{room_id}/light/command
载荷: {"action": "on", "brightness": 70, "color": "warm"}
     {"action": "off"}

# 空调指令（统一指令模型，由后端翻译为品牌协议）
主题: home/{room_id}/ac/command
载荷: {"action": "set", "mode": "cool", "temp": 24, "fan": "auto"}
     {"action": "off"}

# 门禁指令（含加密认证码）
主题: home/{room_id}/door/command
载荷: {"action": "unlock", "auth_code": "<AES加密的一次性认证码>"}
     {"action": "lock"}
`));

children.push(heading('5.4 控制响应主题', 2));
children.push(...codeBlock(`
主题: home/{room_id}/light/response
载荷: {"success": true, "state": {"power": "on", "brightness": 70}}

主题: home/{room_id}/ac/response
载荷: {"success": true, "state": {"power": "on", "mode": "cool", "temp": 24}}

主题: home/{room_id}/door/response
载荷: {"success": true, "state": {"locked": false}}
`));

// ── 六、数据库设计 ──
children.push(heading('六、数据库设计', 1));
children.push(heading('6.1 ER 关系', 2));
children.push(para('User (1) ──< (N) Room (1) ──< (N) Device  |  Device (1) ──< (N) SensorData  |  Device (1) ──< (N) DeviceLog  |  AutomationRule 独立实体，通过 JSON 字段关联设备 ID'));

children.push(heading('6.2 建表 SQL', 2));
children.push(...codeBlock(`
-- 用户表
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'user',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 房间表
CREATE TABLE rooms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    floor       INTEGER DEFAULT 1,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 设备表
CREATE TABLE devices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     INTEGER NOT NULL REFERENCES rooms(id),
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    brand       TEXT,
    mqtt_topic  TEXT NOT NULL,
    status_json TEXT DEFAULT '{}',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- type: temperature_sensor | humidity_sensor | pir_sensor | light | ac | door_lock
-- brand: 仅ac类型使用 (haier/gree/midea/generic)

-- 传感器数据表（历史记录）
CREATE TABLE sensor_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   INTEGER NOT NULL REFERENCES devices(id),
    data_type   TEXT NOT NULL,
    value       REAL,
    extra_json  TEXT DEFAULT '{}',
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sensor_data_device_ts ON sensor_data(device_id, timestamp);

-- 设备操作日志表
CREATE TABLE device_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   INTEGER NOT NULL REFERENCES devices(id),
    action      TEXT NOT NULL,
    detail      TEXT,
    user_id     INTEGER REFERENCES users(id),
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 联动规则表
CREATE TABLE automation_rules (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    condition_json TEXT NOT NULL,
    action_json    TEXT NOT NULL,
    enabled        INTEGER DEFAULT 1,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
`));

children.push(heading('6.3 初始数据示例', 2));
children.push(...codeBlock(`
-- 客厅设备
INSERT INTO rooms VALUES (1, '客厅', 1, '家庭客厅区域', datetime('now'));
INSERT INTO devices VALUES (1,1,'temperature_sensor','客厅温度',NULL,
    'home/livingroom/sensor/temperature','{}',datetime('now'));
INSERT INTO devices VALUES (2,1,'humidity_sensor','客厅湿度',NULL,
    'home/livingroom/sensor/humidity','{}',datetime('now'));
INSERT INTO devices VALUES (3,1,'pir_sensor','客厅人体感应',NULL,
    'home/livingroom/sensor/pir','{}',datetime('now'));
INSERT INTO devices VALUES (4,1,'light','客厅主灯',NULL,
    'home/livingroom/light','{"power":"off","brightness":0}',datetime('now'));
INSERT INTO devices VALUES (5,1,'ac','客厅空调','gree',
    'home/livingroom/ac','{"power":"off","mode":"cool","temp":26}',datetime('now'));

-- 联动规则
INSERT INTO automation_rules VALUES (1,'人来开灯',
    '{"trigger":"pir_sensor","field":"presence","operator":"eq","value":true,
      "and":[{"trigger":"light","field":"power","operator":"eq","value":"off"}]}',
    '[{"device_type":"light","action":"on","params":{"brightness":80}}]',1,datetime('now'));

INSERT INTO automation_rules VALUES (2,'人走关灯',
    '{"trigger":"pir_sensor","field":"presence","operator":"eq","value":false,
      "and":[{"trigger":"light","field":"power","operator":"eq","value":"on"},
             {"trigger":"light","field":"on_duration_sec","operator":"gt","value":300}]}',
    '[{"device_type":"light","action":"off","params":{}}]',1,datetime('now'));

INSERT INTO automation_rules VALUES (3,'高温自动制冷',
    '{"trigger":"temperature_sensor","field":"value","operator":"gt","value":28,
      "and":[{"trigger":"ac","field":"power","operator":"eq","value":"off"}]}',
    '[{"device_type":"ac","action":"set","params":{"power":"on","mode":"cool","temp":26}}]',
    1,datetime('now'));

INSERT INTO automation_rules VALUES (4,'高湿自动除湿',
    '{"trigger":"humidity_sensor","field":"value","operator":"gt","value":80,
      "and":[{"trigger":"ac","field":"power","operator":"eq","value":"off"}]}',
    '[{"device_type":"ac","action":"set","params":{"power":"on","mode":"dehumidify"}}]',
    1,datetime('now'));
`));

// ── 七、REST API 设计 ──
children.push(heading('七、REST API 设计', 1));
children.push(heading('7.1 认证模块', 2));
children.push(table(
  ['方法', '路径', '说明', '认证'],
  [
    ['POST', '/api/auth/login', '用户登录，返回JWT token', '否'],
    ['POST', '/api/auth/register', '用户注册', '否'],
    ['GET', '/api/auth/me', '获取当前用户信息', 'JWT'],
  ]
));
children.push(emptyPara());

children.push(heading('7.2 房间管理', 2));
children.push(table(
  ['方法', '路径', '说明', '认证'],
  [
    ['GET', '/api/rooms', '获取房间列表（含设备数量）', 'JWT'],
    ['GET', '/api/rooms/{id}', '获取房间详情（含设备实时状态）', 'JWT'],
    ['POST', '/api/rooms', '添加房间', 'JWT'],
    ['PUT', '/api/rooms/{id}', '修改房间信息', 'JWT'],
    ['DELETE', '/api/rooms/{id}', '删除房间', 'JWT'],
  ]
));
children.push(emptyPara());

children.push(heading('7.3 设备管理', 2));
children.push(table(
  ['方法', '路径', '说明', '认证'],
  [
    ['GET', '/api/devices', '设备列表（可按room_id/type筛选）', 'JWT'],
    ['GET', '/api/devices/{id}', '设备详情 + 当前状态', 'JWT'],
    ['POST', '/api/devices/{id}/command', '发送控制指令', 'JWT'],
    ['PUT', '/api/devices/{id}', '修改设备信息', 'JWT'],
  ]
));
children.push(emptyPara());

children.push(heading('7.4 历史数据', 2));
children.push(table(
  ['方法', '路径', '说明', '认证'],
  [
    ['GET', '/api/data/sensors', '传感器历史数据?device_id=&type=&start=&end=&limit=', 'JWT'],
    ['GET', '/api/data/logs', '设备操作日志?device_id=&user_id=&start=&end=', 'JWT'],
  ]
));
children.push(emptyPara());

children.push(heading('7.5 联动规则', 2));
children.push(table(
  ['方法', '路径', '说明', '认证'],
  [
    ['GET', '/api/rules', '规则列表', 'JWT'],
    ['POST', '/api/rules', '创建规则', 'JWT'],
    ['PUT', '/api/rules/{id}', '更新规则', 'JWT'],
    ['DELETE', '/api/rules/{id}', '删除规则', 'JWT'],
    ['POST', '/api/rules/{id}/toggle', '启用/禁用规则', 'JWT'],
  ]
));
children.push(emptyPara());

children.push(heading('7.6 WebSocket 实时数据', 2));
children.push(...codeBlock(`
连接: ws://<server>:8000/ws/realtime?token=<jwt_token>

服务端推送格式:
{
    "type": "sensor_update",
    "device_id": 4,
    "room_id": 1,
    "data": {"temperature": 26.5, "humidity": 65.0, "presence": true},
    "timestamp": 1716200000
}

{
    "type": "device_state",
    "device_id": 5,
    "state": {"power": "on", "mode": "cool", "temp": 24},
    "timestamp": 1716200000
}

{
    "type": "rule_triggered",
    "rule_id": 1,
    "rule_name": "人来开灯",
    "result": {"device_id": 4, "action": "on", "success": true},
    "timestamp": 1716200000
}
`));

// ── 八、安全三层设计 ──
children.push(heading('八、安全三层设计', 1));
children.push(para(
  '对应评分标准中"协议传输安全性"10分，系统从传输层、数据层、密钥层三个维度独立设计安全方案，层层递进，每层不共享密钥。'
));
children.push(table(
  ['安全层', '技术方案', '密钥来源', '保护范围'],
  [
    ['传输层', 'HTTPS (TLS 1.3)\nMQTT over TLS (端口8883)', 'CA签发的SSL/TLS证书\n（开发期自签名）', 'APP↔后端全链路加密\n后端↔MQTT Broker加密'],
    ['数据层', 'AES-256-CBC对称加密\n敏感字段载荷加密', 'JWT payload中的\naes_key字段', '门禁认证码、空调控制\n指令等敏感操作载荷'],
    ['密钥层', 'JWT (HS256)身份令牌\n用户独立AES密钥\n密钥定期轮换', '服务端master_secret\n每个用户aes_key独立', '用户身份认证\nAES密钥安全分发'],
  ]
));
children.push(emptyPara());

children.push(heading('8.1 加密流程示意', 2));
children.push(...codeBlock(`
【APP 开门禁流程】
1. APP请求开门 → 携带JWT token
2. 后端验证JWT → 提取用户aes_key
3. 后端生成一次性认证码 → AES-256-CBC(auth_code, aes_key)
4. 后端通过MQTT over TLS发布加密后的auth_code到门禁指令主题
5. 门禁模拟器解密验证 → 执行开锁/上锁

【密钥轮换策略】
- 用户AES密钥在登录时生成，token过期（24h）后自动轮换
- 旧密钥保留1小时用于解密仍在传输中的消息
- 服务端master_secret通过环境变量注入，不写入代码
`));

// ── 九、设备联动规则引擎 ──
children.push(heading('九、设备联动规则引擎', 1));
children.push(para(
  '规则引擎是系统的智能核心，监听 MQTT 传感器数据流，当条件满足时自动触发设备动作。支持热加载（通过 API 增删改规则后立即生效，无需重启服务）。'
));
children.push(heading('9.1 引擎架构', 2));
children.push(...codeBlock(`
RuleEngine (单例)
├── _rules: List[Rule]              # 内存中的规则列表
├── _device_states: Dict            # 设备当前状态缓存
├── reload_rules()                  # 从数据库重新加载规则
├── on_sensor_data(topic, payload)  # 收到传感器数据时触发
│   ├── 更新 _device_states 缓存
│   ├── 遍历所有启用的规则
│   ├── evaluate(rule.condition) → True/False
│   └── execute(rule.actions)       → 通过MQTT下发指令
└── execute_actions(actions)        # 执行动作列表
`));

children.push(heading('9.2 规则定义格式', 2));
children.push(...codeBlock(`
# 规则条件 (condition_json)
{
    "trigger": "temperature_sensor",    # 触发源设备类型
    "field": "value",                   # 比较字段
    "operator": "gt",                   # gt | lt | eq | neq | changed
    "value": 28,                        # 阈值
    "room_id": null,                    # null=全局，指定则只在该房间生效
    "and": [                            # 附加条件（全部满足才触发）
        {"trigger": "ac", "field": "power", "operator": "eq", "value": "off"}
    ]
}

# 规则动作 (action_json) — 支持多动作顺序执行
[
    {
        "device_type": "ac",
        "room_id": "same",              # same=与触发源同房间 | 具体房间ID
        "action": "set",
        "params": {"power": "on", "mode": "cool", "temp": 26}
    }
]
`));

// ── 十、多品牌空调兼容方案 ──
children.push(heading('十、多品牌空调兼容方案', 1));
children.push(para(
  '赛题明确要求兼容海尔、格力、美的三个品牌。本方案采用"统一指令模型 + 品牌翻译器"设计模式。APP 和后端只操作统一指令模型，由设备模拟器内部的品牌翻译器将统一指令转换为各品牌特有的控制协议。'
));
children.push(heading('10.1 统一指令模型', 2));
children.push(...codeBlock(`
# 后端和APP统一使用的指令格式
{
    "power": "on" | "off",
    "mode": "cool" | "heat" | "dehumidify" | "fan_only" | "auto",
    "temp": 16-30,              # 目标温度（摄氏度）
    "fan": "auto" | "low" | "medium" | "high",
    "swing": "on" | "off"       # 摆风
}
`));

children.push(heading('10.2 品牌翻译表', 2));
children.push(...codeBlock(`
# ac_brand.py — 品牌指令翻译表

UNIVERSAL_TO_BRAND = {
    "gree": {
        "power": {"on": "PWR_ON", "off": "PWR_OFF"},
        "mode":  {"cool": "MODE_COOL", "heat": "MODE_HEAT",
                  "dehumidify": "MODE_DRY", "fan_only": "MODE_FAN",
                  "auto": "MODE_AUTO"},
        "fan":   {"auto": "FAN_AUTO", "low": "FAN_1",
                  "medium": "FAN_2", "high": "FAN_3"},
        "temp":  lambda t: f"TEMP_{t}",
    },
    "haier": {
        "power": {"on": "POWER=1", "off": "POWER=0"},
        "mode":  {"cool": "MODE=COOLING", "heat": "MODE=HEATING",
                  "dehumidify": "MODE=DRY", "fan_only": "MODE=FAN",
                  "auto": "MODE=SMART"},
        "fan":   {"auto": "FAN=AUTO", "low": "FAN=LOW",
                  "medium": "FAN=MED", "high": "FAN=HIGH"},
        "temp":  lambda t: f"SET_TEMP={t}",
    },
    "midea": {
        "power": {"on": 1, "off": 0},
        "mode":  {"cool": 2, "heat": 3, "dehumidify": 4,
                  "fan_only": 1, "auto": 0},
        "fan":   {"auto": 1024, "low": 40, "medium": 60, "high": 80},
        "temp":  lambda t: t,
    },
}
`));

children.push(heading('10.3 APP 品牌切换体验', 2));
children.push(para(
  '在 APP 空调控制页面，用户可以从下拉框中选择空调品牌（海尔/格力/美的/通用）。切换品牌后，APP 发送同样的控制指令，后端自动路由到对应品牌的空调模拟器，模拟器内部使用品牌翻译器转换指令。用户无感知，但设备状态返回不同品牌格式，体现系统的多品牌兼容能力。'
));

// ── 十一、项目文件结构 ──
children.push(heading('十一、项目文件结构', 1));
children.push(...codeBlock(`
smart-home-A9/
├── cloud/                              # 阿里云服务器端（全部Python）
│   ├── backend/                        # FastAPI后端服务
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                 # FastAPI入口+生命周期管理
│   │   │   ├── config.py               # 配置（数据库/MQTT/JWT密钥）
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py             # POST /api/auth/login, /register
│   │   │   │   ├── rooms.py            # CRUD /api/rooms
│   │   │   │   ├── devices.py          # GET /api/devices + POST command
│   │   │   │   ├── data.py             # GET /api/data/sensors, /logs
│   │   │   │   └── rules.py            # CRUD /api/rules
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── device.py
│   │   │   │   ├── room.py
│   │   │   │   └── sensor_data.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── mqtt_client.py      # MQTT连接管理+主题订阅
│   │   │   │   ├── rule_engine.py      # 联动规则引擎（核心）
│   │   │   │   ├── security.py         # JWT + AES加密
│   │   │   │   └── ac_brand.py         # 多品牌空调指令翻译
│   │   │   └── database/
│   │   │       ├── __init__.py
│   │   │       ├── connection.py       # SQLite连接管理
│   │   │       └── init_db.py          # 建表+初始数据
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── simulators/                     # 硬件设备模拟器
│   │   ├── __init__.py
│   │   ├── base_device.py              # 设备基类（抽象类）
│   │   ├── temperature_sensor.py       # 温度传感器
│   │   ├── humidity_sensor.py          # 湿度传感器
│   │   ├── pir_sensor.py               # 人体感应传感器
│   │   ├── light_controller.py         # 灯控制器
│   │   ├── ac_controller.py            # 空调控制器（多品牌）
│   │   ├── door_lock.py                # 门禁控制器
│   │   └── simulator_manager.py        # 统一启停管理
│   └── docker-compose.yml              # 一键部署编排
├── openharmony/                        # 鸿蒙APP源码
│   └── entry/src/main/ets/
│       ├── entryability/EntryAbility.ets
│       ├── pages/
│       │   ├── Index.ets               # 启动/引导页
│       │   ├── LoginPage.ets           # 登录页
│       │   ├── DashboardPage.ets       # 仪表盘（总览+实时数据）
│       │   ├── LightControlPage.ets    # 照明控制
│       │   ├── ACControlPage.ets       # 空调控制（含品牌切换）
│       │   └── DoorLockPage.ets        # 门禁控制
│       ├── model/
│       │   └── DeviceModel.ets         # 数据模型定义
│       └── common/
│           ├── ApiClient.ets           # HTTP请求封装
│           └── MqttClient.ets          # MQTT客户端封装
└── docs/                               # 提交文档
    ├── 产品设计文档.md
    ├── 使用手册.md
    ├── 部署说明.md
    └── PPT大纲.md
`));

// ── 十二、开发排期 ──
children.push(heading('十二、开发排期（共5周）', 1));
children.push(table(
  ['周次', '日期', '阶段', '任务内容', '产出物'],
  [
    ['W1', '5/20-5/26', '基础设施',
     '1.阿里云ECS申请+环境配置\n2.Python项目骨架搭建\n3.数据库建表+初始数据\n4.FastAPI启动+认证模块\n5.Mosquitto MQTT Broker部署',
     '可运行的后端骨架\n用户能登录注册\nMQTT服务器通'],
    ['W2', '5/27-6/2', '设备模拟',
     '1.BaseDevice基类设计\n2.温湿度传感器模拟器\n3.PIR人体感应模拟器\n4.灯/空调/门禁控制器\n5.设备管理API\n6.WebSocket实时推送',
     '全部6种设备模拟器\n能通过API查看设备状态\nAPP能收到实时推送'],
    ['W3', '6/3-6/9', '核心逻辑',
     '1.规则引擎开发\n2.安全模块:TLS+AES+JWT\n3.多品牌空调翻译器\n4.鸿蒙APP项目创建\n5.登录页+仪表盘页',
     '规则引擎可工作\n三层加密完成\n鸿蒙APP能登录'],
    ['W4', '6/10-6/16', 'APP+联调',
     '1.照明控制页+空调控制页+门禁页\n2.前后端全链路联调\n3.品牌切换功能验证\n4.规则引擎端到端测试\n5.UI优化美化',
     'APP全部页面完成\n前后端联调通过'],
    ['W5', '6/17-6/23', '收尾',
     '1.全系统集成测试\n2.Bug修复\n3.录制演示视频(≤7分钟)\n4.编写产品设计文档\n5.编写使用手册\n6.制作答辩PPT',
     '作品完整可提交'],
    ['缓冲', '6/24-6/30', '提交',
     '1.最后修bug\n2.打包HAP\n3.整理提交材料\n4.6月30日15:00前提交',
     '提交完成'],
  ]
));
children.push(emptyPara());

// ── 十三、部署方案 ──
children.push(heading('十三、部署方案', 1));
children.push(heading('13.1 阿里云ECS配置建议', 2));
children.push(table(
  ['配置项', '建议值', '说明'],
  [
    ['实例规格', '2 vCPU / 4 GB内存', 'ecs.c7.large 或 ecs.g7.large'],
    ['操作系统', 'Ubuntu 22.04 LTS', 'Python 3.11原生支持好'],
    ['系统盘', '40 GB ESSD', '系统和Docker镜像足够'],
    ['带宽', '按量计费 5 Mbps', '开发期够用，后期可调'],
    ['安全组', '开放22/80/443/8000/8883', 'SSH/HTTP/HTTPS/API/MQTT TLS'],
  ]
));
children.push(emptyPara());

children.push(heading('13.2 Docker Compose 一键部署', 2));
children.push(...codeBlock(`
# docker-compose.yml
version: '3.8'
services:
  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "8883:8883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/certs:/mosquitto/certs
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/smart_home.db
      - MQTT_BROKER=mqtt
      - MQTT_PORT=1883
      - JWT_SECRET=\${JWT_SECRET}
      - JWT_EXPIRE_HOURS=24
    volumes:
      - ./data:/app/data
    depends_on:
      - mqtt
    restart: unless-stopped

  simulators:
    build: ./simulators
    environment:
      - MQTT_BROKER=mqtt
      - MQTT_PORT=1883
    depends_on:
      - mqtt
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/certs:/etc/nginx/certs
    depends_on:
      - backend
    restart: unless-stopped
`));

children.push(heading('13.3 启动命令', 2));
children.push(...codeBlock(`
# 1.上传代码到阿里云ECS
scp -r ./smart-home-A9 root@<ECS公网IP>:/opt/

# 2.SSH登录后启动
cd /opt/smart-home-A9/cloud
docker compose up -d

# 3.验证
curl http://localhost:8000/docs          # FastAPI自动文档页
mosquitto_sub -h localhost -t 'home/#'   # 查看MQTT消息流
`));

// ── 附录 ──
children.push(heading('附录：关键风险与应对', 1));
children.push(table(
  ['风险', '等级', '应对措施'],
  [
    ['OpenHarmony开发学习曲线陡', '高', '先做Web前端验证所有接口，再迁移到ArkTS；使用DevEco Studio模板加速开发'],
    ['时间紧张（5周）', '高', '严格按排期执行，每周日检查进度；砍掉非核心功能，优先保证评分项'],
    ['阿里云费用', '低', '使用学生优惠/免费试用套餐；开发期用本地环境，提交前再迁移云上'],
    ['MQTT+TLS配置复杂', '中', '先用非TLS开发调试，最后一周再加TLS；参考Mosquitto官方TLS文档'],
    ['多品牌空调协议差异', '低', '只需模拟指令格式差异，不需要对接真实空调；翻译器模式改动成本低'],
  ]
));

// ═══════════════════════════════════════════════
//  生成文档
// ═══════════════════════════════════════════════
const doc = new Document({ sections: [{ children }] });

Packer.toBuffer(doc).then(buffer => {
  const outputPath = 'C:/Mycode/smart-home-A9/A9智能家居项目框架文档.docx';
  fs.writeFileSync(outputPath, buffer);
  console.log('✅ 文档已生成: ' + outputPath);
});
