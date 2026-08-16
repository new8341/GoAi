# submissions/ · 提交物总览

按赛事阶段存放**定稿**提交材料；日常开发仍在 `tracks/` 与 `docs/`。

| 子目录 | 阶段 | 截止（规划） | 当前状态 |
|--------|------|--------------|----------|
| [`preliminary/`](preliminary/) | 初赛 | ~8.16 | **已定稿**（方案/路线/可行性/开源 + 上传说明） |
| [`semi_final/`](semi_final/) | 复赛 | ~9.3 | 清单已预填；代码包可作雏形 |
| [`final/`](final/) | 决赛 | ~9.22 | 待路演材料 |
| [`packages/`](packages/) | 打包产物 | — | zip 输出目录 |
| [`scripts/`](scripts/) | 打包脚本 | — | `build_submission_packages.ps1` |

## 一键打包

```powershell
cd <repo>\submissions\scripts
powershell -ExecutionPolicy Bypass -File .\build_submission_packages.ps1
```

## 上传门户

**https://goaihz.com**（以当周页面与社群/邮件通知为准）

官方手册：`document/AI_for_reserach.pdf`
