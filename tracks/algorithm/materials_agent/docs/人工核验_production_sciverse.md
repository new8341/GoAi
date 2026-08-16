# Sciverse 本轮人工核验指南

> 对应运行目录：`outputs/production_sciverse`  
> 用户端：http://127.0.0.1:8765/  
> 调试端：http://127.0.0.1:8765/debug/?run=production_sciverse  
> 本轮状态：`production_verification.json` = **PASS**（parsed≈4/5，GROBID；Sciverse 检索 + 缓存 OA PDF）

目的：用人眼确认「检索来源、全文证据、Gap 可行动性」是否可信，而不是只看自动 PASS。

> 说明：本轮为便于人工核验，解析主路径为 **GROBID**（MinerU 在 Windows 上易被残留 `fast_api` 挂死）。新写入 `fulltext_source=grobid`；读路径仍兼容旧 `grobid_fusion`。

---

## 0. 打开界面（30 秒）

| 步骤 | 操作 | 意义 |
|------|------|------|
| 0.1 | 浏览器打开用户端 `/` | 黑盒视角：评委/用户看到的最终叙事 |
| 0.2 | 在「打开已有运行」选 `production_sciverse ★` → **打开** | 加载本轮结果，无需再跑任务 |
| 0.3 | 点右上角「调试视图」或直接打开 debug URL | 工程师视角：verify、解析源、audit、原文定位 |

两边对照看同一轮产物，避免只信摘要。

---

## 1. 用户端核验（黑盒）

### 1.1 摘要条

| 检查 | 通过标准 | 意义 |
|------|----------|------|
| 文献数 | ≥ 5（本配置 `max_papers=10`） | 检索是否真正召回 |
| 研究空白数 | ≥ 1 | Gap 模块是否产出可审内容 |
| 含全文 | 尽量 ≥ 半数 | 证据是否可能来自全文而非摘要冒充 |
| 一致性 | 显示「通过」更佳 | 交叉引用/证据自洽门禁 |

### 1.2 「研究空白」页（核心）

对 **每一条 Gap** 做：

1. **读标题 + 描述**  
   - 意义：是否像「真缺口」而不是复述已知常识。  
   - 红旗：与教科书常识无差别、或与主题无关。

2. **看类型 pill**（如 `underexplored` / `contradiction`）  
   - 意义：类型是否与描述一致；`contradiction` 必须暗示跨文冲突。

3. **核「证据摘录」**  
   - 读 `quote`：是否像论文原句；`paper_id` 是否在「相关文献」里存在。  
   - 意义：竞赛硬要求——Gap 必须可回源。  
   - 红旗：空证据、口号式 paraphrase、quote 明显不像论文措辞。

4. **核「下一步」与「如何证伪」**  
   - 意义：可行动性与科学可检验性；答辩时会被问。  
   - 红旗：空洞「需要更多研究」、无法设计实验/计算证伪。

5. **抽 1–2 条 Gap 做「反向抽查」**（见 §3）  
   - 意义：防止 quote 幻觉；自动门禁无法替代领域判断。

### 1.3 「相关文献」页

| 检查 | 通过标准 | 意义 |
|------|----------|------|
| 标题是否贴题 | SnSe / 导热 / vacancy 等相关 | Sciverse 召回相关性 |
| 有 DOI | 多数有 | 可外部核对 |
| 「全文可用」标记 | 与摘要条「含全文」大致一致 | 后续证据可信度 |

### 1.4 「报告」页

- 通读首段与 Gap 列表是否与面板一致。  
- 意义：报告是否可作为提交物，而不是与 JSON 矛盾的另一套话术。

---

## 2. 调试端核验（白盒）

打开：http://127.0.0.1:8765/debug/?run=production_sciverse  
顶部确认 run 下拉为 `production_sciverse`（若有 verify 状态会显示 PASS/FAIL）。

### 2.1 Overview / Verify

| 检查 | 通过标准 | 意义 |
|------|----------|------|
| `production_verification` | **PASS** | 自动化生产门槛（解析率、全文证据等） |
| 全文解析比例 | 接近生产基线（如 ≥50%） | MinerU/GROBID 是否工作 |
| 主题与配置 | SnSe vacancy / sciverse | 确认看的是本轮，不是旧 `production` |

### 2.2 文献页

| 检查 | 操作 | 意义 |
|------|------|------|
| `source=sciverse` | 过滤或翻条目 | 确认没用 OpenAlex 回退冒充「已接 Sciverse」 |
| `fulltext_source` | 看 mineru / grobid | 证据来自哪条解析链 |
| OA / pdf | 有路径或 hash | 可追溯物理文件 |

若大量 `source=openalex` 且 audit 写 fallback：Token/API 本轮未真正生效。

### 2.3 Gaps 页（与用户端对照）

| 检查 | 操作 | 意义 |
|------|------|------|
| evidence provenance | 看 chunk / location / paper_id | 比用户端更细的回源信息 |
| quote 定位 | 对照 papers / fulltext 面板 | 人工确认 quote 真在文中 |
| review_status | 记录你的判断 | 可写入 `experiments/reviews/` 作为人工抽检 |

### 2.4 Audit（关键）

在产物或调试加载的 `audit.json` 中找 `tool=sciverse`：

| 期望 | 意义 |
|------|------|
| `output_summary` 含 `N papers`，**无** `fallback openalex` | 本轮检索后端是 Sciverse |
| `meta.mode` = `meta`（或你配置的 mode） | 模式符合预期 |

---

## 3. 反向抽查（强烈建议做 2 条）

任选 Gap 的一条 quote：

1. 记下 `paper_id` 与 quote 关键词（5–8 个连续词）。  
2. 调试端打开该文献全文/解析文本，或在 `data/fulltext/parsed/` 中搜索。  
3. **必须能搜到原句（允许空白/换行差异）**。  

| 结果 | 意义 |
|------|------|
| 搜到 | 证据链可信，可给人工「接受」 |
| 搜不到 | 记为缺陷；填 `experiments/reviews/` 拒收并说明原因 |

---

## 4. 可选：填写正式人工评审

按 [`experiments/reviews/README.md`](../experiments/reviews/README.md)：

1. 复制模板，针对 ≥3 条 Gap。  
2. 字段建议：`accept` / `reject`、理由、quote 是否在原文、下一步是否可执行。  
3. 意义：满足「科学意义」维度的真人抽检证据，比只跑脚本更有说服力。

---

## 5. 核验结论怎么记

建议在笔记或评审 JSON 里用一行结论：

```text
run=production_sciverse | sciverse_audit=ok | verify=PASS|FAIL |
gaps_reviewed=N | quote_ok=A/B | actionability_ok=A/B | notes=...
```

---

## 6. 常见问题

| 现象 | 可能原因 | 怎么办 |
|------|----------|--------|
| 用户端下拉没有 `production_sciverse` | 流水线未写完 / 服务器未刷新 | 等跑完后刷新页面；确认 `outputs/production_sciverse/bundle.json` 存在 |
| 调试端 source 不是 sciverse | Token 失效或 API 失败回退 | 看 audit；重新探测 Token |
| 含全文很少 | OA 下载失败或解析失败 | 调试端看 fulltext；确认 GROBID/MinerU/Qdrant |
| 用户端与调试端 Gap 数不一致 | 看了不同 run | 两侧都选 `production_sciverse` |
