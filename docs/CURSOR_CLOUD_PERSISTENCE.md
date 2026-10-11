# HXForge — Cursor Cloud 开发与成果持久化规则

**生效：** 自 2026-10-11 起，所有 HXForge Cursor Cloud 开发任务必须遵守本文与 `docs/HXFORGE_RESULT_INDEX.jsonl`。

## 一、GitHub 是正式持久化位置

- **仓库：** `xuezhiorange-png/hxforge-agent`
- Cursor Cloud 工作目录与 `/opt/cursor/artifacts` 均为**临时**；不得仅以本地 commit、临时路径或文字总结作为交付完成依据。
- 关键开发成果、输入、计算结果与验证证据必须 **git push** 至 GitHub，并确认远端可读取（`git ls-remote` 或 raw URL）。

## 二、每次任务保留原始结果

在 `docs/HXFORGE_RESULT_INDEX.jsonl` 追加一行（只追加；取代旧记录时在新行 `supersedes_run_id` 指向被取代的 `RUN_ID`）。

每条记录至少包含：

| 字段 | 说明 |
|------|------|
| `task_id` | 任务标识 |
| `run_id` | 本次运行唯一 ID |
| `source_head_sha` | 执行开始时检出 commit |
| `remote_branch` | 推送分支 |
| `remote_commit_sha` | 证据所在远端 commit |
| `inputs` | 输入路径与 SHA256 列表（无则 `[]`） |
| `commands` | 实际执行命令 |
| `environment` | 运行环境摘要 |
| `started_at_utc` / `ended_at_utc` / `duration_s` | 时间 |
| `result` | `PASS` / `BLOCKED` / `FAIL` / `INTERRUPTED` / `NOT_EXECUTED` |
| `raw_result_path` | 原始结果 JSON 等路径（仓库内相对路径；无则 `NONE`） |
| `raw_result_sha256` | 原始结果哈希；无则 `NONE` |
| `summary` / `blockers` / `next_action` | 完成内容、阻断、下一步 |
| `kind` | `policy` / `prototype` / `engineering` / `audit` 等 |

不得将计划结果、模拟结果或部分计算冒充正式工程计算结果。未完成计算必须标明**无最终结果**。

## 三、关键阶段立即保存

重要计算结果、阶段完成、确定性回归、阻断证据产生后应及时 **commit + push**。长时间任务在可用阶段边界持久化中间结果。推送失败须立即报告，不得声称已保存。

## 四、单一结果入口

- **索引文件：** `docs/HXFORGE_RESULT_INDEX.jsonl`
- **说明：** `docs/HXFORGE_RESULT_INDEX.md`
- 按 `task_id`、`run_id`、`remote_commit_sha` 检索；历史只追加或 `supersedes_run_id` 标记取代，不覆盖、不混淆不同请求或数值身份。

## 五、Git 分支管理

- 开发与证据保存在独立工作分支（`cursor/<name>-1201`）。
- 未经授权不得修改 PR #283 状态、合并或更改冻结工程数值 Authority。
- 禁止提交大型临时缓存、重复日志、密钥或敏感数据。

## 六、任务结束交付块（必填）

```
TASK_ID=
RUN_ID=
RESULT=
REMOTE_BRANCH=
REMOTE_COMMIT_SHA=
SOURCE_HEAD_SHA=
INPUT_PATH=
RAW_RESULT_PATH=
RAW_RESULT_SHA256=
EVIDENCE_INDEX_PATH=
REMOTE_PERSISTENCE_VERIFIED=
NEXT_ACTION=
```

未产生的项写 `NONE`，禁止编造。

## 七、与 AGENTS.md 的关系

工程计算约束仍以 `AGENTS.md` 与 `docs/MASTER_DEVELOPMENT_SPEC.md` 为准；本文规定 **Cursor Cloud 会话外** 如何找回源码、证据与任务进度。
