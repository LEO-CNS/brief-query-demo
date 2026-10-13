# 招聘需求简报 · 最小集查询 Demo

案例：招聘需求澄清与面试协同（合成演练数据，不代表任何企业真实经营数据）。

## 最小集 → 实现对照

| 最小集要素 | 实现位置 | 说明 |
|---|---|---|
| 任务：查当前简报「必备/偏好」 | `query` 命令 | 只取当前有效版本，输出答案+来源（版本号+字段+类型） |
| 当前有效版本；作废与旧版本排除 | `active_version()` | 双条件：版本有效期 + 确认状态；排除轨迹进 `audit.excluded_versions` |
| 合同硬约束与内部附加条件分列 | 条件 `type` 字段 | 每条来源标注「合同硬约束 / 内部附加条件 / 客户口径」 |
| 客户内部筛选标准与财务预算不开放 | `restricted_fields` | 访问返回 `field_not_open`，并给出走客户口径流程的提示 |
| 新增只读任务：只查本人批次 | `status` 命令 | 只返回 `owner == 本人` 的批次；不写回、不发外部消息 |
| 五个角色 | `raci` 命令 | 顾明岚/唐映秋/秦芮/傅景/叶书 |
| 验收：来源支持答案 | 答案每条带 `来源` | 版本号 + 字段名 + 类型，可直接回溯原文 |
| 验收：权限正确 | 不开放字段拦截 + 他人批次不可见 | 失败都带 reason |
| 验收：失败可解释 | 所有 `_fail()` | error code + 中文原因 + 排除轨迹 |
| 验收：能按手册维护 | `manual` 命令 | 新增/改版/作废/调权限/排错五类操作说明 |

## 运行

```bash
python3 brief_demo.py serve                # 页面版：浏览器打开 http://127.0.0.1:8010
python3 brief_demo.py query J-2026-001                 # 主任务（CLI）
python3 brief_demo.py query J-2026-001 --field 财务预算 # 试探不开放字段
python3 brief_demo.py status                           # 只读查本人批次
python3 brief_demo.py status --as-user E002            # 换人（只见自己的）
python3 brief_demo.py query J-2026-003                 # 只有作废版本
python3 brief_demo.py query J-2026-004                 # 有效但未确认
python3 brief_demo.py raci                             # 角色分工
python3 brief_demo.py manual                           # 维护手册
python3 brief_demo.py demo                             # 一键全部场景（CLI）
```

页面版 API：`GET /api/query?job=...&as_user=E001[&field=...]`、`GET /api/status?as_user=E001`、`GET /api/raci`。页面与 CLI 复用同一套核心函数（`cmd_query` / `cmd_status`），不存在两套逻辑。

零依赖，Python 3.9+ 标准库即可。

## 验收四条对照

1. **来源支持答案**：答案中每条必备/偏好都有 `来源`（版本号+字段+类型），如 `版本 v2 · 字段「工作经验」· 类型 合同硬约束`。
2. **权限正确**：不开放字段返回 `field_not_open`；`status` 只显示本人批次（E001 查不到 E002 的 J-2026-002）。
3. **失败可解释**：`brief_not_found` / `no_active_version` / `field_not_open` / `unknown_user`，每个都带原因与排除轨迹；未确认版本不静默，带 `warning`。
4. **能按手册维护**：`manual` 命令给出新增、改版、作废、调权限、排错五类维护操作步骤。

## 边界（刻意不做）

- 不写回任何系统；不发外部消息；不自动筛除或录用候选人
- 身份由 CLI 参数模拟，不是真实鉴权；生产环境须接正式 IdP
- 数据为合成演练样本
