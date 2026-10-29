# 项目计划：平面图 → Gazebo 世界 → 文字任务驱动机器人

> 课程：Agentic AI and Foundation Models（WS2026/27）
> 整理日期：2026-10-29
> 预算：约 50 小时

---

## 1. 项目一句话

输入一张建筑平面图（PDF/图片），VLM agent 自动识别墙、门、房间和尺寸，生成 RMF 的 `.building.yaml`，再用现成工具转成 Gazebo 世界；然后用户用一句话下达任务，LLM 把它转成结构化计划，机器人在生成的建筑里通过 Nav2 执行。

**Demo 叙事**：一张平面图、一句话，机器人在自动生成的建筑里自己走到目的地。

---

## 2. 确定的任务流程

### 阶段一（核心）：平面图 → Gazebo 世界

```
平面图图片
   ↓  [原本：人在 traffic_editor 里手动点]
   ↓  [本项目：VLM 识别墙角、墙、门、尺寸标注 → 自动写出这个 yaml]
.building.yaml
   ↓  building_map_generator（现成工具）
Gazebo .world
```

### 阶段二（加分项）：文字任务 → 机器人执行

```
building.yaml（墙/门/房间名+坐标）
                         │
                         ▼ 作为语义地图提供给 LLM
"先去厨房，再检查 2 号门是否关着，最后回到入口"
                         ↓  [LLM 任务规划]
[{"action":"navigate","target":"Kitchen"},
 {"action":"inspect","target":"Door_2"},
 {"action":"navigate","target":"Entrance"}]
                         ↓  [确定性代码]
房间名 → 坐标 → Nav2 NavigateToPose / FollowWaypoints
                         ↓
TurtleBot3 在仿真里执行
```

**设计原则**：LLM 只负责“理解”并输出结构化数据（yaml / JSON 计划），几何转换、SDF 生成、导航执行全部交给确定性代码。

---

## 3. LLM 组件设计

### 3.1 平面图解析 agent（借鉴 arXiv 2604.23970 的 self-critic 循环）

1. **预处理（可选）**：OCR 识别尺寸标注和房间名；墙/门检测模型给出 bbox，作为 VLM 的定位依据（grounding），减少坐标幻觉。
2. **Parser（VLM）**：看图 + 检测结果 → 输出顶点、墙、门、房间名、比例尺（measurement）。
3. **Self-Critic（确定性检查 + 可选 LLM 检查）**，不通过则带错误信息让 Parser 重试（例如最多 2 次）：
   - 墙端点能否闭合 / 房间多边形是否闭合
   - 每扇门是否落在某段墙上
   - 提取尺寸与图上标注尺寸的偏差
   - 房间连通性（BFS），是否有孤立房间
4. **Writer（确定性代码）**：结构化结果 → `.building.yaml`。

对照实验：单次调用 VLM 输出 vs 带 self-critic 循环的 agentic 流程。

### 3.2 任务规划 agent（阶段二）

- 输入：用户文字指令 + 语义地图（房间名、门 ID、坐标）。
- 输出：只能从固定动作集合中选择，如 `navigate`、`inspect`、`wait`、`report`。
- 目标必须是地图中存在的房间/门，校验代码拒绝不存在的目标（拦截幻觉）。
- 执行：房间名 → 坐标 → Nav2 `NavigateToPose` / `FollowWaypoints`。
- 最小版本：只实现 `navigate` 一个动作即可完成 demo。
- 可选扩展：输出 RMF 任务请求（patrol / delivery），由 RMF 调度，可扩展到多机器人（工作量大，50 小时内不建议）。

### 3.3 模型

- Gemini Flash 或 GLM Flash（便宜），也可用任何兼容 OpenAI 接口的模型。

---

## 4. `.building.yaml` 说明

`.building.yaml` 原本由 **traffic_editor**（Open-RMF 的 Qt GUI）**人工描图**得到：

1. 导入平面图图片作为底图；
2. 标比例尺：选一段已知长度的线，点两个端点，输入实际长度（米）；
3. 点墙角顶点 → 两两连成墙；门 = 两个顶点之间的门洞，设类型（hinged / sliding）和开门方向；还可画地面、车道（lanes）；
4. 保存为 `.building.yaml`。

**本项目用 VLM agent 替代第 3 步的人工描图。** 好处：

- 输出格式简单（顶点、墙、门、比例尺），适合 LLM 输出；
- LLM 生成的 yaml 能在 traffic_editor 里打开、叠在底图上检查，手动修正后即为 ground truth；
- 可量化对比“人工描图 vs agent 描图”的时间和精度。

简化示意（**字段细节未核实，需读源码或文档确认**）：

```yaml
name: my_building
levels:
  L1:
    elevation: 0
    drawing: {filename: floorplan.png}   # 背景底图
    vertices:                            # 顶点，坐标是底图像素
      - [100, 200, 0, ""]
      - [600, 200, 0, ""]
      - [600, 500, 0, ""]
    measurements:                        # 比例尺：顶点0到1实际是5米
      - [0, 1, {distance: [3, 5.0]}]
    walls:                               # 墙 = 两个顶点的连线
      - [0, 1, {}]
      - [1, 2, {}]
    doors:                               # 门 = 两个顶点之间的门洞
      - [3, 4, {name: [1, door_1], type: [1, hinged], motion_degrees: [3, 90]}]
```

生成 world 的命令：

```bash
ros2 run rmf_building_map_tools building_map_generator gazebo \
  ${building_map_path} ${output_world_path} ${output_model_dir}
# 把 gazebo 换成 ignition 可生成 Ignition 世界
```

参考文档：https://osrf.github.io/ros2multirobotbook/traffic-editor.html

---

## 5. 可借用的仓库（已核对许可证，2026-10）

### 推荐使用

| 仓库 | 许可证 | 用途 | 接入方式 |
|---|---|---|---|
| [open-rmf/rmf_traffic_editor](https://github.com/open-rmf/rmf_traffic_editor)（`rmf_building_map_tools`） | Apache-2.0 | `.building.yaml` → Gazebo/Ignition `.world`；traffic_editor GUI 用于检查和制作 ground truth | ROS 包，colcon 编译；Humble 可能可以 apt 安装（**未核实**）。Python 依赖：`python3-shapely python3-yaml python3-requests` |
| [robotics-upo/gazebo_world_generator](https://github.com/robotics-upo/gazebo_world_generator) | MIT | `src/utils/sdf_utils.py`（SDF 工具）、`src/utils/json_validator.py`、`src/llm/interface.py`（OpenAI 兼容 LLM 封装）、`gazebo_ros2_2dmap_plugin`（world → 占据栅格地图）、测试结构 | git 子模块或 `pip install -e`；可不装 ROS 用 Python 跑；支持 Humble/Gazebo Classic 11 和 Jazzy/Harmonic |
| [linorobot/linorobot2](https://github.com/linorobot/linorobot2) 中的 `world_creator` | Apache-2.0 | **Baseline**：像素挤出（深色像素 → STL 墙 → SDF），无语义 | 单独运行 `ros2 run linorobot2_gazebo world_creator`，不进仓库 |

建议的仓库结构：

```
your_project/
├── external/gazebo_world_generator   (git submodule, MIT)
├── (apt / colcon) rmf_building_map_tools
└── baseline: linorobot2 world_creator（单独跑）
```

### 可用但有限制

| 仓库 | 说明 |
|---|---|
| [secorolab/scenery_builder](https://github.com/secorolab/scenery_builder) | 输出最全（SDF、占据地图、门动画、launch），但**没有 LICENSE 文件**，默认不能复用；输入为 JSON-LD，依赖 Python 3.11 + Blender |
| [secorolab/FloorPlan-DSL](https://github.com/secorolab/FloorPlan-DSL) | MIT，可借鉴 DSL 设计作为中间表示 |
| [aliasstudio/mitunet](https://github.com/aliasstudio/mitunet) | MIT，墙体分割模型，可作 CV 对照组或 grounding；不检测门 |
| [xmarva/floorplan-detection](https://github.com/xmarva/floorplan-detection) | MIT，墙/房间检测，不检测门 |

### 仅作数据或参考

- [CubiCasa/CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k)：约 5000 张平面图、80+ 类标注；**CC BY-NC 4.0**（课程可用，不可商用）；代码基于 Python 3.6 / PyTorch 1.0，太老，只用数据。
- [agaitanis/msc_thesis](https://github.com/agaitanis/msc_thesis)：Apache-2.0，Panoptic-DeepLab 识别墙/房间/门 + 图寻路，2024 年后未更新。
- CVC-FP 数据集：有墙体结构标注，可作几何 ground truth。
- FloorPlanCAD（ICCV 2021）：大规模 CAD 平面图数据集，若支持 DXF 输入可参考。

### 阶段二待调研（未核实）

- NASA JPL **ROSA**：LLM agent 通过自然语言操作 ROS。
- **ROS-LLM**（Auromix）：自然语言 → ROS 指令框架。

---

## 6. 相关工作（写 related work 用）

| 工作 | 内容 | 与本项目区别 |
|---|---|---|
| **arXiv 2604.23970** — LLM-Guided Agentic Floor Plan Parsing for Accessible Indoor Navigation of BLV People（Ayanzadeh & Oates, UMBC, 2026-04） | 5 个 agent：Parser（LLM + YOLOv12 检测作为 grounding）→ Graph Builder（门连最近两个房间）→ Self-Critic（BFS 连通、门-边一致、矩阵对称、孤立节点，失败重试 ≤2 次）→ Planner（BFS + LLM 生成指令）→ Safety Evaluator（窄通道 <90cm、死胡同等，severity ≥4 重新规划）；三层 RAG（NetworkX + ChromaDB + 视觉上下文）；ArUco 定位。CVC-FP 成功率 89.4/83.2/71.5%；真实楼 MP-1、MP-3 各 13 条路线，人工走 | 只抽取**拓扑图**（房间=节点、门=边），无度量几何、无 SDF、无仿真、无机器人；评测样本很小 |
| Floorplan2Guide（arXiv 2512.12177） | 上文同一作者前作 | 无公开代码 |
| Vision Language Models Can Parse Floor Plan Maps（arXiv 2409.12842） | GPT-4o / Claude 3.5 Sonnet 看平面图直接输出导航动作序列，9 步任务成功率 0.96，大空间表现下降 | 不重建几何 |
| Coffrini et al., IPIN 2025 | MLLM 从平面图生成导航指令，转成图结构后效果大幅提升 | 图结构是人工构造的 |
| WAFFLE（WACV 2025） | 多模态平面图理解 | — |
| Blueprint-Bench（arXiv 2509.25229） | 评测 LLM 空间理解，让模型输出 SVG 平面图 | eval 方法可借鉴 |
| GzScenic（arXiv 2104.08625） | 场景描述 → Gazebo .world | 后端参考 |
| LIRS-WCT | 灰度图 → 高度图 → SDF | 物体多了仿真卡死，说明显式墙体优于高度图 |
| robotics-upo/gazebo_world_generator | 英文描述 → LLM → Gazebo 世界 + 家具 + 导航地图 | 输入是文字，不对应真实建筑 |
| traffic_editor | 人工描图 → yaml → world | 本项目自动化其人工步骤 |
| linorobot2 world_creator | 像素挤出 | 无语义，文字/标注也会变成墙 |
| arXiv 2308.05443 | IFC → IfcConvert → Collada → Gazebo，碰撞/视觉模型分开，玻璃从碰撞模型去掉 | IFC 路线，可作上限对照 |
| Automation in Construction vol.127 | BIM 机器人任务规划，含 IFC→SDF 转换器（刷墙机器人） | — |

**Novelty 表述**：现有工作要么像素挤出（linorobot2）、要么人工描图（traffic_editor）、要么输入是文字（gazebo_world_generator）、要么 VLM 只做拓扑/导航不重建几何（2409.12842、2604.23970）。“VLM agent 抽取带语义的度量几何 → SDF → 机器人仿真验证”的完整组合未见实现。

---

## 7. Eval 设计

### 阶段一

- **几何误差**：提取的墙长 / 房间尺寸 vs 图纸标注；门位置误差（cm）。
- **结构正确率**：墙、门的 precision / recall；房间连通性正确率（Nav2 在仿真里能否到达各房间）。
- **对照组**：
  1. linorobot2 `world_creator`（像素挤出，无语义）
  2. CubiCasa5k / MitUNet 分割模型（传统 CV）
  3. 单次 VLM 调用 vs agentic self-critic 循环
  4. IFC 直接转换 / 人工 traffic_editor 描图（上限）
- **数据**：
  - 自己 4D viewer 项目里的 Revit/IFC 模型：导出楼层平面图 PDF 作为输入，同一 IFC 提供精确 ground truth（无需人工标注，是本项目特色）
  - CVC-FP、CubiCasa5k 补充样本

### 阶段二

- 任务解析正确率：20～30 条文字任务，人工写标准动作序列，与 LLM 输出比对。
- 执行成功率：Gazebo 中是否到达正确房间。
- 端到端：平面图解析误差如何传递到任务执行（如门漏识别 → 房间不连通 → 任务失败）。

---

## 8. 机器人与环境

- ROS 2 Humble + Gazebo（Classic 11）；或 Jazzy + Harmonic。
- TurtleBot3（推荐，资料最多）：

```bash
sudo apt install ros-humble-turtlebot3*
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
# 把 world 参数换成生成的 .world 路径
```

- 可选：Clearpath Husky（`ros-humble-husky-simulator`，更像工地巡检）、Spot（`spot_ros2`）。

---

## 9. 时间安排（约 50 小时）

| 周 | 内容 |
|---|---|
| 1–2 | 环境搭建（ROS 2、rmf_building_map_tools、TurtleBot3）；读懂 `.building.yaml` schema；VLM 稳定输出正确结构；unit test |
| 3–4 | Self-critic 循环；yaml → world；在 Gazebo 里验证几张真实平面图 |
| 5–6 | Eval 脚本 + 报告；边界情况（弧形墙、楼梯先跳过） |
| 有余力 | 阶段二：文字任务 → Nav2（先只做 `navigate`） |

---

## 10. 待办

- [x] 确认 `rmf_building_map_tools` 安装方式：apt 有 1.6.3，但项目改用 Data 盘上的 RoboStack conda 环境（`environment.yml`，1.5.0）；traffic_editor 在 conda 上没有（2026-10-29）
- [ ] 读 `rmf_building_map_tools` 源码，整理 `.building.yaml` 真实字段规范（房间名怎么存、门参数）
- [ ] 跑通 traffic_editor 手工描一张图 → world → TurtleBot3，确认后端链路
- [ ] 从 IFC 导出测试平面图 + ground truth
- [ ] 调研 ROSA / ROS-LLM 的现状和许可证（阶段二）
