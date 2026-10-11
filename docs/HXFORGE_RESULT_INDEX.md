# HXForge 结果索引（单一入口）

## 文件

| 路径 | 用途 |
|------|------|
| `docs/HXFORGE_RESULT_INDEX.jsonl` | 追加式任务/运行记录（每行一个 JSON 对象） |
| `docs/CURSOR_CLOUD_PERSISTENCE.md` | Cursor Cloud 持久化规则全文 |

## 检索

```bash
# 按 TASK_ID
rg '"task_id": "V07_TASK173' docs/HXFORGE_RESULT_INDEX.jsonl

# 按 RUN_ID
rg '"run_id": "run_' docs/HXFORGE_RESULT_INDEX.jsonl
```

## 追加新记录

1. 在独立分支完成工作与测试。
2. `git push` 成功后，在索引末尾追加一行 JSON（字段见 `CURSOR_CLOUD_PERSISTENCE.md`）。
3. 再次 commit + push（索引与证据在同一或后续 commit；`remote_commit_sha` 填**含证据的最终** commit）。
4. 任务回复中粘贴第六节交付块。

## `result` 语义

| 值 | 含义 |
|----|------|
| `PASS` | 任务目标已达成且证据已远端持久化 |
| `BLOCKED` | 因策略/环境/依赖无法完成（附 `blockers`） |
| `FAIL` | 执行失败（测试、校验、计算未通过） |
| `INTERRUPTED` | 人为或环境中断 |
| `NOT_EXECUTED` | 未运行（仅设计/文档） |

原型 mock、遥测演练不等于 `engineering` 正式 Rating/Sizing 结果；须在 `kind` 与 `summary` 中写明。
