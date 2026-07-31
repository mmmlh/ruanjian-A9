# 智能家居 gpt-image-2 专属图标包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用 `gpt-image-2` 生成 18 张候选图，筛选并交付 9 枚统一的智能家居 PNG 图标及多尺寸素材包。

**Architecture:** 在 Git 已忽略的 `tmp/icon-pack-work/` 中建立一次性、可恢复的 Python 生成管线。目录中的目录清单模块只负责图标语义和提示词，生成模块只负责安全调用 API 并持久化候选，打包模块只负责联系表、选择、透明度处理、缩放、清单、报告、校验和 ZIP；最终结果写入同样已忽略的 `output/generated-icons/`，不修改应用源码和已打包资源。

**Tech Stack:** Python 3.11、标准库 `urllib.request`、Pillow 12.3、OpenAI 兼容图片生成 API、PowerShell、PNG/JSON/ZIP

---

## 文件结构

实施时创建以下一次性文件：

- `tmp/icon-pack-work/icon_catalog.py`：9 个图标的稳定 ID、中文名称、主体语义、背景规则和统一提示词。
- `tmp/icon-pack-work/generate_candidates.py`：认证、请求、退避重试、Base64 解码、原子写入和断点续跑。
- `tmp/icon-pack-work/build_pack.py`：候选联系表、背景规范化、尺寸导出、清单、报告、ZIP 和自动验收。
- `tmp/icon-pack-work/test_icon_pack_pipeline.py`：不调用付费接口的本地单元测试。
- `tmp/icon-pack-work/run-state.json`：18 个生成任务的成功或失败状态，不含认证信息。
- `tmp/icon-pack-work/selection.json`：视觉检查后写入的 9 项 A/B 选择。

最终创建 `output/generated-icons/` 下设计规格规定的素材目录和交付文件。`tmp/` 和 `output/` 均由仓库根 `.gitignore` 排除；不强制加入 Git。

### Task 1: 锁定图标清单和提示词契约

**Files:**
- Create: `tmp/icon-pack-work/test_icon_pack_pipeline.py`
- Create: `tmp/icon-pack-work/icon_catalog.py`

- [ ] **Step 1: 写入清单失败测试**

测试必须验证 9 个稳定 ID、每个 ID 恰好两个候选任务、设备透明背景、应用图标不透明背景，以及提示词的无文字约束：

```python
import unittest

from icon_catalog import ASSETS, build_jobs


class CatalogTests(unittest.TestCase):
    def test_catalog_has_exactly_the_approved_assets(self):
        self.assertEqual(
            [asset["id"] for asset in ASSETS],
            [
                "app_home_beacon",
                "device_light",
                "device_ac",
                "device_door_lock",
                "device_curtain",
                "device_humidifier",
                "device_temperature_sensor",
                "device_humidity_sensor",
                "device_pir_sensor",
            ],
        )

    def test_build_jobs_creates_two_candidates_per_asset(self):
        jobs = build_jobs()
        self.assertEqual(len(jobs), 18)
        self.assertEqual({job["variant"] for job in jobs}, {"a", "b"})
        self.assertEqual(len({job["filename"] for job in jobs}), 18)

    def test_prompts_are_text_free_and_background_specific(self):
        for job in build_jobs():
            prompt = job["prompt"].lower()
            self.assertIn("no text", prompt)
            self.assertIn("no letters", prompt)
            self.assertIn("no watermark", prompt)
            if job["asset_id"] == "app_home_beacon":
                self.assertIn("opaque graphite rounded-square background", prompt)
                self.assertNotIn("a9", prompt)
            else:
                self.assertIn("true transparent background", prompt)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
python -m unittest tmp/icon-pack-work/test_icon_pack_pipeline.py -v
```

Expected: FAIL，原因是 `icon_catalog` 尚不存在。

- [ ] **Step 3: 实现清单和统一提示词**

`icon_catalog.py` 使用 9 项明确语义：

```python
STYLE = (
    "A single isolated smart-home icon in a coherent soft dimensional dual-material style. "
    "Matte ceramic white main body, graphite black #16212D and #213142 structural details, "
    "pine green #14875B status accent, subtle pale green #E4F3EC glow, soft upper-left studio light, "
    "slight front-facing top view, restrained short shadow, centered square 1:1 composition, "
    "approximately 14 percent safe margin, one object only, consistent visual weight. "
    "No text, no letters, no numbers, no logo, no watermark, no people, no room scene, no extra props."
)

ASSETS = [
    {"id": "app_home_beacon", "name": "应用图标", "subject": (
        "Create a text-free app icon called Home Beacon: a simple ceramic-white house outline "
        "containing one pine-green glowing core point, on an opaque graphite rounded-square background."
    ), "transparent": False},
    {"id": "device_light", "name": "灯光", "subject": "A modern ceiling light or light bulb with one clear luminous element.", "transparent": True},
    {"id": "device_ac", "name": "空调", "subject": "A compact modern wall-mounted air conditioner with one clean air outlet.", "transparent": True},
    {"id": "device_door_lock", "name": "门锁", "subject": "A modern vertical smart door-lock panel with a clear handle and status light.", "transparent": True},
    {"id": "device_curtain", "name": "窗帘", "subject": "A symmetrical pair of smart curtains with a clear central opening seam.", "transparent": True},
    {"id": "device_humidifier", "name": "加湿器", "subject": "A compact tabletop humidifier with one restrained soft mist plume.", "transparent": True},
    {"id": "device_temperature_sensor", "name": "温度传感器", "subject": "A round wall temperature sensor with an abstract thermometer groove, without digits.", "transparent": True},
    {"id": "device_humidity_sensor", "name": "湿度传感器", "subject": "A round wall humidity sensor with one abstract droplet groove, without digits.", "transparent": True},
    {"id": "device_pir_sensor", "name": "人体感应器", "subject": "A compact wall-mounted PIR presence sensor with one faceted sensing window.", "transparent": True},
]


def build_jobs():
    jobs = []
    for asset in ASSETS:
        background = (
            "Use an opaque graphite rounded-square background that fills the canvas."
            if not asset["transparent"]
            else "Use a true transparent background with no floor or backdrop; keep only a tight soft object shadow."
        )
        for variant in ("a", "b"):
            jobs.append({
                "asset_id": asset["id"],
                "name": asset["name"],
                "variant": variant,
                "filename": f"{asset['id']}_{variant}.png",
                "transparent": asset["transparent"],
                "prompt": f"{asset['subject']} {STYLE} {background}",
            })
    return jobs
```

- [ ] **Step 4: 运行清单测试并确认通过**

Run:

```powershell
python -m unittest tmp/icon-pack-work/test_icon_pack_pipeline.py -v
```

Expected: 3 tests PASS，不产生网络请求或输出图片。

### Task 2: 实现安全、可恢复的 API 生成器

**Files:**
- Modify: `tmp/icon-pack-work/test_icon_pack_pipeline.py`
- Create: `tmp/icon-pack-work/generate_candidates.py`

- [ ] **Step 1: 为请求体、密钥保护和断点续跑写失败测试**

新增测试，使用 `unittest.mock` 替代真实网络：

```python
import base64
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from generate_candidates import build_payload, generate_all


class GeneratorTests(unittest.TestCase):
    def test_payload_matches_documented_contract(self):
        payload = build_payload("example prompt")
        self.assertEqual(payload, {
            "model": "gpt-image-2",
            "prompt": "example prompt",
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
        })

    def test_generation_resumes_without_repeating_existing_success(self):
        image_buffer = io.BytesIO()
        Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)).save(image_buffer, "PNG")
        encoded = base64.b64encode(image_buffer.getvalue()).decode("ascii")

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps({"data": [{"b64_json": encoded}]}).encode("utf-8")

        with tempfile.TemporaryDirectory() as tmp, patch("generate_candidates.urlopen", return_value=FakeResponse()) as mocked:
            os.environ["CHIYI_API_KEY"] = "test-secret-not-for-output"
            jobs = [{"asset_id": "sample", "variant": "a", "filename": "sample_a.png", "prompt": "p", "transparent": True, "name": "示例"}]
            generate_all(jobs, Path(tmp))
            generate_all(jobs, Path(tmp))
            self.assertEqual(mocked.call_count, 1)
            combined = "".join(path.read_text("utf-8") for path in Path(tmp).glob("*.json"))
            self.assertNotIn("test-secret-not-for-output", combined)
```

- [ ] **Step 2: 运行生成器测试并确认失败**

Run:

```powershell
python -m unittest tmp/icon-pack-work/test_icon_pack_pipeline.py -v
```

Expected: FAIL，原因是 `generate_candidates` 尚不存在。

- [ ] **Step 3: 实现请求和恢复逻辑**

`generate_candidates.py` 必须：

- 从 `CHIYI_API_KEY` 读取密钥，缺失时在任何文件写入前退出；
- 请求 `https://chiyicn.com/v1/images/generations`；
- 使用 `build_payload()` 返回固定字段；
- 每张成功图片先写临时文件，再用 `Path.replace()` 原子落盘；
- 在 `run-state.json` 中只保存 asset、variant、status、attempts、HTTP 状态和错误摘要；
- 已存在且能被 Pillow 解码为 1024x1024 PNG 的候选直接跳过；
- `401/403` 立即抛错；`429/5xx` 和解码错误最多重试 3 次，等待 5、15、30 秒；
- 不打印认证头、密钥或完整响应体。

核心接口固定为：

```python
API_URL = "https://chiyicn.com/v1/images/generations"


def build_payload(prompt: str) -> dict:
    return {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json",
    }


def generate_all(jobs: list[dict], work_dir: Path) -> None:
    key = os.environ.get("CHIYI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CHIYI_API_KEY is required")
    candidates = work_dir / "candidates"
    candidates.mkdir(parents=True, exist_ok=True)
    for index, job in enumerate(jobs, 1):
        target = candidates / job["filename"]
        if valid_png(target, (1024, 1024)):
            print(f"[{index}/18] skip {job['filename']}")
            continue
        generate_one(job, target, key, work_dir / "run-state.json")
        print(f"[{index}/18] saved {job['filename']}")
```

- [ ] **Step 4: 运行生成器单元测试**

Run:

```powershell
python -m unittest tmp/icon-pack-work/test_icon_pack_pipeline.py -v
```

Expected: 所有本地测试 PASS；网络 mock 只被调用一次；临时 JSON 中不含测试密钥。

### Task 3: 实现候选联系表和最终打包器

**Files:**
- Modify: `tmp/icon-pack-work/test_icon_pack_pipeline.py`
- Create: `tmp/icon-pack-work/build_pack.py`

- [ ] **Step 1: 为透明度、缩放、清单和 ZIP 写失败测试**

使用 Pillow 创建合成的 1024px 图标，并验证：

```python
from build_pack import normalize_device_icon, resize_exports, sha256_file, verify_zip_members


class PackBuilderTests(unittest.TestCase):
    def test_device_normalization_makes_corners_transparent(self):
        image = Image.new("RGB", (1024, 1024), "white")
        normalized = normalize_device_icon(image)
        self.assertEqual(normalized.mode, "RGBA")
        for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            self.assertEqual(normalized.getpixel(point)[3], 0)

    def test_resize_exports_have_exact_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Image.new("RGBA", (1024, 1024), (20, 135, 91, 255))
            paths = resize_exports("sample", image, Path(tmp), (512, 256, 128, 64))
            self.assertEqual([Image.open(path).size for path in paths], [(512, 512), (256, 256), (128, 128), (64, 64)])

    def test_sha256_is_stable(self):
        with tempfile.NamedTemporaryFile() as file:
            file.write(b"smart-home")
            file.flush()
            self.assertEqual(len(sha256_file(Path(file.name))), 64)
```

- [ ] **Step 2: 运行打包器测试并确认失败**

Run:

```powershell
python -m unittest tmp/icon-pack-work/test_icon_pack_pipeline.py -v
```

Expected: FAIL，原因是 `build_pack` 尚不存在。

- [ ] **Step 3: 实现确定性图片处理和交付构建**

`build_pack.py` 必须提供：

```python
def normalize_device_icon(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    if rgba.getextrema()[3] != (255, 255):
        return rgba
    corner_colors = [rgba.getpixel(point)[:3] for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023))]
    background = tuple(sum(color[channel] for color in corner_colors) // 4 for channel in range(3))
    return clear_edge_connected_background(rgba, background, threshold=28)


def resize_exports(asset_id: str, image: Image.Image, output: Path, sizes=(512, 256, 128, 64)) -> list[Path]:
    paths = []
    for size in sizes:
        directory = output / "sizes" / str(size)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{asset_id}.png"
        image.resize((size, size), Image.Resampling.LANCZOS).save(path, "PNG", optimize=True)
        paths.append(path)
    return paths
```

`clear_edge_connected_background()` 只能从四条边开始 flood fill，并只清除与四角平均背景色 RGB 欧氏距离不超过 28 的连通像素。它不能对全图做颜色替换。

打包器还必须：

- 生成 `candidate-contact-sheet.png`，每行一个 asset，A/B 并排，使用棋盘格展示透明度并附文件名；
- 从 `selection.json` 读取 9 个明确的 `a` 或 `b`；
- 设备图标执行透明背景规范化，应用图标只转换为 RGBA、不清除背景；
- 保存 `masters/` 和 4 组尺寸；
- 生成包含模型、接口、选择、尺寸、模式和 SHA-256 的 `manifest.json`；
- 生成不含密钥的 `generation-report.md`；
- 生成 `final-contact-sheet.png`，每个图标同时展示常规缩略图和 64px 预览；
- 创建 ZIP，并只加入 `masters/`、`sizes/`、最终联系表、清单和报告。

- [ ] **Step 4: 运行全部本地管线测试**

Run:

```powershell
python -m unittest tmp/icon-pack-work/test_icon_pack_pipeline.py -v
```

Expected: 所有测试 PASS，不调用付费接口。

### Task 4: 执行 18 张候选图生成

**Files:**
- Create: `output/generated-icons/candidates/*.png`
- Create: `tmp/icon-pack-work/run-state.json`

- [ ] **Step 1: 验证凭证未写入文件**

由当前任务进程把用户已提供的凭证注入 `CHIYI_API_KEY`，不创建 `.env`、明文凭证文件或带密钥的脚本。执行前运行：

```powershell
rg -n --hidden -S 'sk-[A-Za-z0-9]{20,}' tmp/icon-pack-work output/generated-icons
```

Expected: 无匹配；目录尚不存在时允许 `rg` 返回 2。

- [ ] **Step 2: 执行可恢复生成器**

Run:

```powershell
python tmp/icon-pack-work/generate_candidates.py --output output/generated-icons --state tmp/icon-pack-work/run-state.json
```

Expected: 依次显示 `[1/18]` 到 `[18/18]`，成功文件立即落盘；重跑会 skip 已完成项，不重复付费生成。

- [ ] **Step 3: 验证候选数量和图片契约**

Run:

```powershell
python tmp/icon-pack-work/build_pack.py verify-candidates --input output/generated-icons/candidates --state tmp/icon-pack-work/run-state.json
```

Expected: `18 candidate PNG files; all decodable; all 1024x1024; run state contains no secrets`。

- [ ] **Step 4: 生成候选联系表**

Run:

```powershell
python tmp/icon-pack-work/build_pack.py contact-sheet --input output/generated-icons/candidates --output output/generated-icons/candidate-contact-sheet.png
```

Expected: 一张 9 行、A/B 两列的联系表，标签位于图像外部。

### Task 5: 视觉选择并生成最终素材包

**Files:**
- Create: `tmp/icon-pack-work/selection.json`
- Create: `output/generated-icons/masters/*.png`
- Create: `output/generated-icons/sizes/{512,256,128,64}/*.png`
- Create: `output/generated-icons/final-contact-sheet.png`
- Create: `output/generated-icons/manifest.json`
- Create: `output/generated-icons/generation-report.md`
- Create: `output/generated-icons/smart-home-icon-pack.zip`

- [ ] **Step 1: 检查候选联系表和必要的原图**

用图像查看工具检查 `candidate-contact-sheet.png`，并对小尺寸难以判断的候选打开对应 1024px 原图。逐项依据 64px 识别度、结构正确性、材质、视角、留白、透明度和全套一致性选择 A 或 B。

- [ ] **Step 2: 写入并验证 9 项实际选择**

依据真实候选视觉检查结果创建 `selection.json`。根对象必须包含 `ASSETS` 中的 9 个且仅包含这 9 个 asset ID；每个值必须是包含 `variant` 和 `reason` 的对象，`variant` 只能是 `a` 或 `b`，`reason` 必须记录该候选在小尺寸识别度、结构或全套一致性方面胜出的具体原因。

`build_pack.py` 使用以下校验函数拒绝缺项、额外项、非法候选或空理由：

```python
def validate_selection(selection: dict, asset_ids: set[str]) -> None:
    if set(selection) != asset_ids:
        raise ValueError("selection must contain exactly the approved asset ids")
    for asset_id, choice in selection.items():
        if set(choice) != {"variant", "reason"}:
            raise ValueError(f"{asset_id}: selection requires variant and reason")
        if choice["variant"] not in {"a", "b"}:
            raise ValueError(f"{asset_id}: variant must be a or b")
        if len(choice["reason"].strip()) < 12:
            raise ValueError(f"{asset_id}: reason must describe the visual decision")
```

写入后运行：

```powershell
python tmp/icon-pack-work/build_pack.py validate-selection --selection tmp/icon-pack-work/selection.json
```

Expected: `PASS: 9 reviewed selections with reasons`。

- [ ] **Step 3: 构建最终素材**

Run:

```powershell
python tmp/icon-pack-work/build_pack.py build --input output/generated-icons/candidates --selection tmp/icon-pack-work/selection.json --output output/generated-icons
```

Expected: 9 张 1024px 母版、36 张尺寸导出、最终联系表、清单、报告和 ZIP 均创建成功。

- [ ] **Step 4: 检查最终联系表和 64px 输出**

视觉检查必须确认应用图标没有 “A9” 或其他文字，8 个设备图标互不混淆，白色陶瓷主体没有被背景清除算法侵蚀，九枚图标视觉重量协调。

如同一图标两个候选均不合格，停止该任务并报告，不增加成功生成次数，不继续打包不合格素材。

### Task 6: 最终自动验收与交付

**Files:**
- Verify: `output/generated-icons/**`
- Verify only: `openharmony/**`
- Verify only: `cloud/**`

- [ ] **Step 1: 运行完整验收器**

Run:

```powershell
python tmp/icon-pack-work/build_pack.py verify-final --output output/generated-icons
```

Expected:

```text
PASS: 9 masters at 1024x1024
PASS: 36 exact-size PNG exports
PASS: 8 device masters have transparent corners
PASS: app_home_beacon has an opaque background
PASS: manifest paths and SHA-256 values match
PASS: ZIP members match the delivery allowlist
PASS: no credential-like token found
```

- [ ] **Step 2: 验证没有修改应用和云端代码**

Run:

```powershell
git status --short -- openharmony cloud
```

Expected: 只显示实施前已存在的用户修改；本任务不新增这些目录的差异。

- [ ] **Step 3: 验证 ZIP 可读取并抽查文件**

Run:

```powershell
python -c "import zipfile; p='output/generated-icons/smart-home-icon-pack.zip'; z=zipfile.ZipFile(p); bad=z.testzip(); print('members', len(z.namelist()), 'bad', bad); assert bad is None"
```

Expected: `bad None`，成员数量与 `masters/`、`sizes/`、最终联系表、清单和报告的允许列表一致。

- [ ] **Step 4: 保留可恢复信息并交付**

保留 `tmp/icon-pack-work/run-state.json` 和 `selection.json`，以便用户需要针对单个图标继续工作时不重复生成。因为 `tmp/` 和 `output/` 已被 Git 忽略，不创建素材提交；最终回复提供最终联系表、ZIP 和输出目录的绝对路径。
