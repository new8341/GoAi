# 商业 API / 闭源模型披露（材料 Agent）

| 服务或模型 | 调用环节 | 费用假设 | 权限范围 | 可替代方案 | 对可复现性的影响 |
|------------|----------|----------|----------|------------|------------------|
| OpenAI 兼容 Chat API（`.env` 中 `OPENAI_*`，含 Minimax 等） | 抽取 / Gap / 报告 / Route A SCORE | 按 token / 套餐计费；免费代理可能限流 | 仅本机 `.env` | `llm.enabled: false` 启发式 | 关 LLM 仍可跑证据链金标；消融见 `ablate_route_a.py` |
| Cursor SDK（可选） | 同上 | 按 Cursor 套餐 | `CURSOR_API_KEY` | 回退 OpenAI 或启发式 | Windows 桥失败时自动降级并写 audit |
| Materials Project API | Route A 外验 | 免费 Key | `MP_API_KEY` | 不可用则外验失败（禁止静默 offline） | 无 Key 时勿宣称 MP 外验 |
| Sciverse API | 检索 | Token 自备 | `SCIVERSE_API_TOKEN` | OpenAlex（仅当 `allow_backend_fallback: true`） | 生产金标禁止静默回退 |
| OpenAlex / Unpaywall | 检索 / OA 定位 | 免费（建议邮箱/Key） | 公开 API | local_json demo | demo 可完全离线 |

密钥**永不**进入 git / 提交 zip。
