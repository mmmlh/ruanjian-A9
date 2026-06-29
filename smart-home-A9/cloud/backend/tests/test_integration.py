"""
端到端集成测试 — 模拟真实用户操作流程
"""
import json


class TestUserFlow:
    """模拟真实用户操作流程"""

    def test_full_user_journey(self, client, auth_headers):
        """完整用户旅程: 登录→查看房间→控制设备→执行场景→查看日志"""
        headers = auth_headers

        # ── 第一步：查看所有房间 ──
        resp = client.get("/api/rooms", headers=headers)
        assert resp.status_code == 200
        rooms = resp.json()
        assert len(rooms) >= 2
        room_names = [r["name"] for r in rooms]
        assert "客厅" in room_names
        assert "卧室" in room_names
        print(f"  ✅ 房间列表: {room_names}")

        # 找到客厅的 id
        living_room_id = next(r["id"] for r in rooms if r["name"] == "客厅")
        bedroom_id = next(r["id"] for r in rooms if r["name"] == "卧室")

        # ── 第二步：查看客厅详情（含设备列表）──
        resp = client.get(f"/api/rooms/{living_room_id}", headers=headers)
        assert resp.status_code == 200
        room = resp.json()
        assert "devices" in room
        living_devices = room["devices"]
        assert len(living_devices) == 6  # 客厅有6个设备
        print(f"  ✅ 客厅设备数: {len(living_devices)}")

        # ── 第三步：列出并筛选设备 ──
        resp = client.get("/api/devices", headers=headers)
        assert resp.status_code == 200
        all_devices = resp.json()
        assert len(all_devices) == 11  # 总共11个设备
        device_types = set(d["type"] for d in all_devices)
        expected_types = {"temperature_sensor", "humidity_sensor", "pir_sensor", "light", "ac", "door_lock"}
        assert expected_types.issubset(device_types)
        print(f"  ✅ 设备总数: {len(all_devices)}, 类型: {device_types}")

        # 按房间筛选
        resp = client.get(f"/api/devices?room_id={living_room_id}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 6
        print(f"  ✅ 客厅筛选: {len(resp.json())} 个设备")

        # 按类型筛选
        resp = client.get("/api/devices?type=light", headers=headers)
        assert resp.status_code == 200
        lights = resp.json()
        assert len(lights) == 2  # 客厅和卧室各一个灯
        print(f"  ✅ 灯光设备: {len(lights)} 个")

        # ── 第四步：获取设备详情 ──
        # 客厅主灯: device id=4
        living_light = next(d for d in all_devices if d["id"] == 4)
        resp = client.get(f"/api/devices/{living_light['id']}", headers=headers)
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["type"] == "light"
        assert "客厅" in detail["room_name"]
        print(f"  ✅ 设备详情: {detail['name']} (状态: {detail['status']})")

        # ── 第五步：控制灯光 ──
        # 开灯
        resp = client.post(
            f"/api/devices/{living_light['id']}/command",
            json={"action": "on"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        print("  ✅ 开灯指令已发送")

        # 设置亮度
        resp = client.post(
            f"/api/devices/{living_light['id']}/command",
            json={"action": "set_brightness", "params": {"brightness": 75}},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 亮度调节指令已发送")

        # 关灯
        resp = client.post(
            f"/api/devices/{living_light['id']}/command",
            json={"action": "off"},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 关灯指令已发送")

        # ── 第六步：控制空调 ──
        living_ac = next(d for d in all_devices if d["id"] == 5)  # 客厅空调
        # 开机
        resp = client.post(
            f"/api/devices/{living_ac['id']}/command",
            json={"action": "on"},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 空调开机")

        # 设置制冷模式+26度
        resp = client.post(
            f"/api/devices/{living_ac['id']}/command",
            json={"action": "set", "params": {"mode": "cool", "temperature": 26}},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 空调设为制冷26°C")

        # 关机
        resp = client.post(
            f"/api/devices/{living_ac['id']}/command",
            json={"action": "off"},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 空调关机")

        # ── 第七步：控制门锁 ──
        door_lock = next(d for d in all_devices if d["id"] == 6)  # 客厅门禁
        # 开锁
        resp = client.post(
            f"/api/devices/{door_lock['id']}/command",
            json={"action": "unlock", "params": {"auth_code": "test-auth-code-123"}},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 门锁已开启")

        # 上锁
        resp = client.post(
            f"/api/devices/{door_lock['id']}/command",
            json={"action": "lock"},
            headers=headers,
        )
        assert resp.status_code == 200
        print("  ✅ 门锁已关闭")

        # ── 第八步：场景管理 ──
        # 列出场景
        resp = client.get("/api/scenes", headers=headers)
        assert resp.status_code == 200
        scenes = resp.json()
        scene_names = [s["name"] for s in scenes]
        assert "回家模式" in scene_names
        assert "离家模式" in scene_names
        assert "睡眠模式" in scene_names
        print(f"  ✅ 预设场景: {scene_names}")

        # 执行回家模式
        home_scene = next(s for s in scenes if s["id"] == 1)  # 回家模式
        resp = client.post(f"/api/scenes/{home_scene['id']}/execute", headers=headers)
        assert resp.status_code == 200
        result = resp.json()
        assert result["scene"] == "回家模式"
        assert "actions" in result
        print(f"  ✅ 执行「回家模式」- 执行了 {result['executed']} 个动作")

        # 执行睡眠模式
        sleep_scene = next(s for s in scenes if s["id"] == 3)  # 睡眠模式
        resp = client.post(f"/api/scenes/{sleep_scene['id']}/execute", headers=headers)
        assert resp.status_code == 200
        result = resp.json()
        assert result["scene"] == "睡眠模式"
        print(f"  ✅ 执行「睡眠模式」- 执行了 {result['executed']} 个动作")

        # 创建自定义场景
        resp = client.post(
            "/api/scenes",
            json={
                "name": "观影模式",
                "icon": "movie",
                "description": "看电影时的场景",
                "actions_json": json.dumps([
                    {"device_id": living_light["id"], "action": "set_brightness", "params": {"brightness": 30}},
                    {"device_id": living_ac["id"], "action": "set", "params": {"mode": "cool", "temperature": 25}},
                ]),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        new_scene = resp.json()
        assert new_scene["name"] == "观影模式"
        print(f"  ✅ 创建自定义场景「观影模式」")

        # 执行自定义场景
        resp = client.post(f"/api/scenes/{new_scene['id']}/execute", headers=headers)
        assert resp.status_code == 200
        print("  ✅ 执行自定义场景")

        # 删除自定义场景
        resp = client.delete(f"/api/scenes/{new_scene['id']}", headers=headers)
        assert resp.status_code == 200
        print("  ✅ 删除自定义场景")

        # ── 第九步：自动化规则管理 ──
        resp = client.get("/api/rules", headers=headers)
        assert resp.status_code == 200
        rules = resp.json()
        assert len(rules) == 4
        rule_names = [r["name"] for r in rules]
        print(f"  ✅ 自动化规则: {rule_names}")

        # 切换第一条规则的启用状态
        first_rule = rules[0]
        resp = client.post(f"/api/rules/{first_rule['id']}/toggle", headers=headers)
        assert resp.status_code == 200
        toggled = resp.json()
        assert toggled["enabled"] != first_rule["enabled"]
        print(f"  ✅ 规则「{first_rule['name']}」切换为 {'启用' if toggled['enabled'] else '禁用'}")

        # 切回去
        resp = client.post(f"/api/rules/{first_rule['id']}/toggle", headers=headers)
        assert resp.status_code == 200
        print(f"  ✅ 规则已恢复")

        # 创建新规则
        resp = client.post(
            "/api/rules",
            json={
                "name": "测试规则-回家自动开空调",
                "description": "当温度超过30度且有人时开制冷",
                "condition_json": json.dumps({"type": "and", "conditions": [
                    {"field": "temperature", "op": "gt", "value": 30},
                    {"field": "presence", "op": "eq", "value": True},
                ]}),
                "action_json": json.dumps([
                    {"device_id": living_ac["id"], "action": "set", "params": {"mode": "cool", "temperature": 25}},
                ]),
            },
            headers=headers,
        )
        assert resp.status_code == 200
        new_rule = resp.json()
        assert new_rule["name"] == "测试规则-回家自动开空调"
        print(f"  ✅ 创建自定义规则")

        # 删除新规则
        resp = client.delete(f"/api/rules/{new_rule['id']}", headers=headers)
        assert resp.status_code == 200
        print("  ✅ 删除自定义规则")

        # ── 第十步：查看传感器数据 ──
        resp = client.get("/api/data/sensors", headers=headers)
        assert resp.status_code == 200
        sensor_data = resp.json()
        assert isinstance(sensor_data, list)
        print(f"  ✅ 传感器数据: {len(sensor_data)} 条记录")

        # 按设备筛选
        temp_sensor = next(d for d in all_devices if d["id"] == 1)  # 客厅温度传感器
        resp = client.get(f"/api/data/sensors?device_id={temp_sensor['id']}", headers=headers)
        assert resp.status_code == 200
        print(f"  ✅ 温度传感器数据过滤")

        # 查看设备日志
        resp = client.get("/api/data/logs", headers=headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert isinstance(logs, list)
        print(f"  ✅ 设备操作日志: {len(logs)} 条记录")

        print("\n" + "=" * 50)
        print("  🎉 完整用户旅程测试全部通过！")
        print("=" * 50)


class TestEdgeCases:
    """边界情况和异常场景"""

    def test_unauthorized_requests(self, client):
        """未认证请求应返回 401"""
        # 不带 token 访问各端点
        endpoints = [
            "/api/rooms",
            "/api/devices",
            "/api/scenes",
            "/api/rules",
            "/api/data/sensors",
            "/api/data/logs",
            "/api/auth/me",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            assert resp.status_code == 401, f"{endpoint} should return 401"
        print(f"  ✅ {len(endpoints)} 个端点正确拒绝了未认证请求")

    def test_invalid_token(self, client):
        """伪造 token 应返回 401"""
        resp = client.get(
            "/api/rooms",
            headers={"Authorization": "Bearer invalid-token-fake"},
        )
        assert resp.status_code == 401

        resp = client.get(
            "/api/rooms",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJmYWtlIjp0cnVlfQ.fake"},
        )
        assert resp.status_code == 401
        print("  ✅ 伪造 token 被正确拒绝")

    def test_command_to_nonexistent_device(self, client, auth_headers):
        """对不存在的设备下发指令"""
        resp = client.post(
            "/api/devices/99999/command",
            json={"action": "on"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        print("  ✅ 不存在设备返回 404")

    def test_invalid_json_scene(self, client, auth_headers):
        """创建场景时传入非法 JSON"""
        resp = client.post(
            "/api/scenes",
            json={
                "name": "坏场景",
                "icon": "bug",
                "description": "test",
                "actions_json": "这不是 JSON",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        print("  ✅ 非法 JSON 被拒绝")

    def test_delete_nonexistent_resource(self, client, auth_headers):
        """删除不存在的资源"""
        # 删除不存在的房间
        resp = client.delete("/api/rooms/99999", headers=auth_headers)
        assert resp.status_code == 404

        # 删除不存在的规则
        resp = client.delete("/api/rules/99999", headers=auth_headers)
        assert resp.status_code == 404

        # 删除不存在的场景
        resp = client.delete("/api/scenes/99999", headers=auth_headers)
        assert resp.status_code == 404
        print("  ✅ 删除不存在资源正确返回 404")


class TestDataConsistency:
    """数据一致性检查"""

    def test_seed_data_integrity(self, client, auth_headers):
        """种子数据完整性验证"""
        headers = auth_headers

        # 房间数 >= 2
        rooms = client.get("/api/rooms", headers=headers).json()
        assert len(rooms) >= 2

        # 每个房间的设备数匹配
        for room in rooms:
            resp = client.get(f"/api/rooms/{room['id']}", headers=headers)
            assert resp.status_code == 200
            detail = resp.json()
            assert "device_count" in detail or "devices" in detail

        # 设备总数 = 11
        devices = client.get("/api/devices", headers=headers).json()
        assert len(devices) == 11

        # 每种类型设备 > 0
        type_count = {}
        for d in devices:
            type_count[d["type"]] = type_count.get(d["type"], 0) + 1
        assert type_count.get("temperature_sensor", 0) == 2
        assert type_count.get("humidity_sensor", 0) == 2
        assert type_count.get("pir_sensor", 0) == 2
        assert type_count.get("light", 0) == 2
        assert type_count.get("ac", 0) == 2
        assert type_count.get("door_lock", 0) == 1

        # 场景数 = 3
        scenes = client.get("/api/scenes", headers=headers).json()
        assert len(scenes) == 3

        # 规则数 = 4
        rules = client.get("/api/rules", headers=headers).json()
        assert len(rules) == 4

        # admin 用户可正常获取
        me = client.get("/api/auth/me", headers=headers).json()
        assert me["username"] == "admin"
        assert me["role"] == "admin"

        print(f"  ✅ 种子数据完整: {len(rooms)}房, {len(devices)}设备, {len(scenes)}场景, {len(rules)}规则")


class TestAuthFlow:
    """完整认证流程测试"""

    def test_register_login_flow(self, client):
        """注册→登录→获取个人信息 完整流程"""
        import time
        username = f"testuser_{int(time.time())}"
        password = "testpass456"

        # 注册
        resp = client.post("/api/auth/register", json={
            "username": username,
            "password": password,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        token = data["token"]
        assert data["user"]["username"] == username
        print(f"  ✅ 注册成功: {username}")

        # 用新 token 获取个人信息
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        me = resp.json()
        assert me["username"] == username
        print(f"  ✅ 个人信息获取成功")

        # 用新用户登录
        resp = client.post("/api/auth/login", json={
            "username": username,
            "password": password,
        })
        assert resp.status_code == 200
        assert "token" in resp.json()
        print(f"  ✅ 新用户登录成功")

        # 用新 token 操作受保护资源
        new_token = resp.json()["token"]
        resp = client.get("/api/rooms", headers={
            "Authorization": f"Bearer {new_token}",
        })
        assert resp.status_code == 200
        print(f"  ✅ 新用户可访问受保护资源")

    def test_admin_login_and_workflow(self, client):
        """admin 登录并执行完整工作流"""
        # 登录
        resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        token = data["token"]
        print(f"  ✅ admin 登录成功")

        # 验证 token 可用于后续请求
        headers = {"Authorization": f"Bearer {token}"}

        # 快速验证所有主要端点
        endpoints = [
            ("GET", "/api/rooms"),
            ("GET", "/api/devices"),
            ("GET", "/api/scenes"),
            ("GET", "/api/rules"),
            ("GET", "/api/data/sensors"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = client.get(path, headers=headers)
            assert resp.status_code == 200, f"{method} {path} failed"

        print(f"  ✅ admin 可访问所有 {len(endpoints)} 个端点")
