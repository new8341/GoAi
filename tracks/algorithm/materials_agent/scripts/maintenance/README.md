# Maintenance scripts (not the reproduce path)

这些脚本曾用于修补 `outputs/production_sciverse`。**答辩复现不要跑它们。**

正式入口：

```text
scripts/reproduce_production_sciverse.ps1
scripts/reproduce_production_sciverse.sh
```

| 脚本 | 历史用途 |
|------|----------|
| `build_sciverse_verify_bundle.py` | 注入缓存 SV PDF 做核验包 |
| `reground_production_gaps.py` | 重接地噪声证据 |
| `upgrade_sciverse_expert_rounds.py` | 六轮中途改标题/Gap |
| `finish_sciverse_expert_rounds.py` | TEI 标题与 temporal 恢复 |

包根是 `materials_agent/`（本目录的上两级），没有独立的 `src/` 树。
