const els = {
  form: document.getElementById("surveyForm"),
  topic: document.getElementById("topic"),
  topicPreset: document.getElementById("topicPreset"),
  topicPresetHint: document.getElementById("topicPresetHint"),
  profile: document.getElementById("profile"),
  routeA: document.getElementById("routeA"),
  hint: document.getElementById("profileHint"),
  submit: document.getElementById("submitBtn"),
  progress: document.getElementById("progress"),
  progressTitle: document.getElementById("progressTitle"),
  progressMsg: document.getElementById("progressMsg"),
  formError: document.getElementById("formError"),
  compose: document.getElementById("compose"),
  results: document.getElementById("results"),
  summary: document.getElementById("summary"),
  alignBar: document.getElementById("alignBar"),
  again: document.getElementById("againBtn"),
  reportText: document.getElementById("reportText"),
  existingRun: document.getElementById("existingRun"),
  openRunBtn: document.getElementById("openRunBtn"),
  composeDocs: document.getElementById("composeDocs"),
  resultLinks: document.getElementById("resultLinks"),
  headerDebugLink: document.getElementById("headerDebugLink"),
};

let profiles = [];
let topicPresets = [];
let pollTimer = null;
let topicFromPreset = false;

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatBytes(n) {
  const v = Number(n) || 0;
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB`;
}

function renderDocLinks(docs, emptyText) {
  if (!docs || !docs.length) {
    return `<p class="muted">${esc(emptyText || "暂无文档")}</p>`;
  }
  return `<ul class="link-list">${docs
    .map(
      (d) => `<li>
        <div>
          <a class="doc-title" href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a>
          <p class="muted">${esc(d.desc || "")}</p>
        </div>
        <div class="link-actions">
          <a href="${esc(d.url)}" target="_blank" rel="noopener">打开</a>
          <a href="${esc(d.download_url || d.url + "?download=1")}" download>下载</a>
        </div>
      </li>`
    )
    .join("")}</ul>`;
}

function renderArtifactLinks(artifacts) {
  if (!artifacts || !artifacts.length) {
    return `<p class="muted">本轮尚未写出可下载产物。</p>`;
  }
  return `<ul class="link-list">${artifacts
    .map(
      (a) => `<li>
        <div>
          <a class="doc-title" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a>
          <p class="muted">${esc(a.name)} · ${formatBytes(a.bytes)}</p>
        </div>
        <div class="link-actions">
          <a href="${esc(a.url)}" target="_blank" rel="noopener">打开</a>
          <a href="${esc(a.download_url || a.url + "?download=1")}" download>下载</a>
        </div>
      </li>`
    )
    .join("")}</ul>`;
}

async function loadComposeDocs() {
  const res = await fetch("/api/docs");
  const data = await res.json();
  if (!els.composeDocs) return;
  els.composeDocs.innerHTML = renderDocLinks(data.docs || [], "文档目录为空");
}

async function loadProfiles() {
  const res = await fetch("/api/profiles");
  const data = await res.json();
  profiles = data.profiles || [];
  els.profile.innerHTML = profiles
    .map((p) => `<option value="${esc(p.id)}">${esc(p.label)}</option>`)
    .join("");
  els.profile.value = profiles.some((p) => p.id === "sciverse") ? "sciverse" : "quick";
  updateHint();
}

async function loadTopicPresets() {
  if (!els.topicPreset) return;
  let data = null;
  try {
    const res = await fetch("/api/topic-presets");
    if (res.ok) {
      data = await res.json();
    }
  } catch (_) {
    /* fall through */
  }
  if (!data || !Array.isArray(data.topics)) {
    try {
      const res2 = await fetch("/configs/topic_presets.json");
      if (res2.ok) data = await res2.json();
    } catch (_) {
      /* fall through */
    }
  }
  if (!data || !Array.isArray(data.topics) || !data.topics.length) {
    if (els.topicPresetHint) {
      els.topicPresetHint.textContent =
        "备选主题加载失败：请重启 serve_viewer 后刷新页面。仍可在下方手动填写主题。";
    }
    return;
  }
  topicPresets = data.topics || [];
  const defaultId = data.default_id || "";
  els.topicPreset.innerHTML =
    `<option value="">自定义输入…</option>` +
    topicPresets
      .map(
        (t) =>
          `<option value="${esc(t.id)}">${esc(t.label_zh || t.topic)}</option>`
      )
      .join("");
  if (els.topicPresetHint && data.description) {
    els.topicPresetHint.textContent = data.description;
  }
  if (defaultId && topicPresets.some((t) => t.id === defaultId)) {
    els.topicPreset.value = defaultId;
    applyTopicPreset(defaultId);
  }
}

function applyTopicPreset(id) {
  const item = topicPresets.find((t) => t.id === id);
  if (!item) {
    topicFromPreset = false;
    if (els.topicPresetHint) {
      els.topicPresetHint.textContent = "已切换为自定义：可直接在下方编辑主题。";
    }
    return;
  }
  topicFromPreset = true;
  els.topic.value = item.topic || "";
  if (els.topicPresetHint) {
    const note = item.note ? ` · ${item.note}` : "";
    els.topicPresetHint.textContent = `已填入备选「${item.label_zh || item.id}」${note}。仍可在下方修改。`;
  }
}

function syncPresetWithTopicText() {
  if (!els.topicPreset || topicFromPreset) return;
  const text = els.topic.value.trim();
  const match = topicPresets.find((t) => (t.topic || "").trim() === text);
  els.topicPreset.value = match ? match.id : "";
}

async function loadExistingRuns() {
  const res = await fetch("/api/runs");
  const data = await res.json();
  const runs = (data.runs || []).filter((r) => r.has_papers || r.has_gaps);
  const preferred = "production_sciverse";
  els.existingRun.innerHTML =
    `<option value="">选择 outputs 目录…</option>` +
    runs
      .map((r) => {
        const mark = r.id === preferred ? " ★" : "";
        const verify = r.verify_status ? ` · ${r.verify_status}` : "";
        return `<option value="${esc(r.id)}">${esc(r.id)}${esc(mark)}${esc(verify)} · gaps ${esc(
          r.gaps ?? "?"
        )}</option>`;
      })
      .join("");
  if (runs.some((r) => r.id === preferred)) {
    els.existingRun.value = preferred;
  }
}

function updateHint() {
  const p = profiles.find((x) => x.id === els.profile.value);
  els.hint.textContent = p ? `${p.hint} · 预计 ${p.estimated}` : "";
}

function showError(msg) {
  els.formError.textContent = msg;
  els.formError.classList.toggle("hidden", !msg);
}

function setBusy(busy, title, msg) {
  els.submit.disabled = busy;
  els.progress.classList.toggle("hidden", !busy);
  if (title) els.progressTitle.textContent = title;
  if (msg) els.progressMsg.textContent = msg;
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(`panel-${tab.dataset.panel}`).classList.add("active");
    });
  });
}

function runIdFromOutputDir(output_dir) {
  const raw = String(output_dir || "").replace(/\\/g, "/");
  const lower = raw.toLowerCase();
  const marker = "/outputs/";
  const idx = lower.lastIndexOf(marker);
  if (idx >= 0) return raw.slice(idx + marker.length).replace(/^\/+|\/+$/g, "");
  if (lower.startsWith("outputs/")) return raw.slice("outputs/".length).replace(/^\/+|\/+$/g, "");
  return raw.replace(/^\.?\//, "").replace(/^\/+|\/+$/g, "");
}

function gateClass(status) {
  const s = String(status || "").toUpperCase();
  if (s === "PASS" || status === true) return "gate-pass";
  if (s === "FAIL" || status === false) return "gate-fail";
  return "gate-na";
}

function renderAlignBar(result, runId) {
  if (!els.alignBar) return;
  const g = result.gates || {};
  const m = result.metrics || {};
  const flags = m.pass_flags || {};
  const pct = (v) => (v == null ? "—" : `${Math.round(Number(v) * 100)}%`);
  const debugHref = result.debug_url || (runId ? `/debug/?run=${encodeURIComponent(runId)}` : "/debug/");
  const cells = [
    `<span class="gate ${gateClass(g.verify)}">verify ${esc(g.verify || "—")}</span>`,
    `<span class="gate ${gateClass(g.science_review)}">science ${esc(g.science_review || "—")}</span>`,
    `<span class="gate ${gateClass(g.consistency_ok)}">consistency ${
      g.consistency_ok == null ? "—" : g.consistency_ok ? "PASS" : "FAIL"
    }</span>`,
    `<span class="gate ${gateClass(flags.topic_hit_rate)}">贴题 ${esc(pct(m.topic_hit_rate))}</span>`,
    `<span class="gate ${gateClass(flags.gap_material_alignment)}">Gap对齐 ${esc(
      pct(m.gap_material_alignment)
    )}</span>`,
    `<span class="gate ${gateClass(flags.provenance_coverage)}">溯源 ${esc(pct(m.provenance_coverage))}</span>`,
    `<a class="chip" href="${esc(debugHref)}">调试端打开本 run</a>`,
  ];
  els.alignBar.innerHTML = `<div class="align-inner"><strong>对齐条</strong>（同源不同步 · run=<code>${esc(
    runId || "—"
  )}</code>）${cells.join("")}</div>`;
}

function renderResult(result) {
  const s = result.summary || {};
  const m = result.metrics || {};
  const flags = m.pass_flags || {};
  const pct = (v) => (v == null ? "—" : `${Math.round(Number(v) * 100)}%`);
  const flag = (k) => (flags[k] == null ? "" : flags[k] ? "✓" : "!");
  const runId =
    result.run_id ||
    runIdFromOutputDir(result.output_dir) ||
    window.__expertRunId ||
    "";
  window.__expertRunId = runId;
  renderAlignBar(result, runId);
  if (els.headerDebugLink) {
    els.headerDebugLink.href = result.debug_url || (runId ? `/debug/?run=${encodeURIComponent(runId)}` : "/debug/");
  }
  if (runId) {
    const url = new URL(location.href);
    url.searchParams.set("run", runId);
    history.replaceState(null, "", url);
  }

  els.summary.innerHTML = [
    ["文献", s.papers ?? 0],
    ["研究空白", s.gaps ?? 0],
    ["含全文", s.fulltext_papers ?? 0],
    ["一致性", s.consistency_ok == null ? "—" : s.consistency_ok ? "通过" : "异常"],
    [`贴题${flag("topic_hit_rate")}`, pct(m.topic_hit_rate)],
    [`Gap对齐${flag("gap_material_alignment")}`, pct(m.gap_material_alignment)],
    [`噪声↓${flag("evidence_boilerplate_rate")}`, pct(m.evidence_boilerplate_rate)],
    [`溯源${flag("provenance_coverage")}`, pct(m.provenance_coverage)],
  ]
    .map(
      ([label, value]) =>
        `<div class="metric"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`
    )
    .join("");

  const artifacts = result.artifacts || [];
  const docs = result.docs || [];
  const reportArtifact = artifacts.find((a) => a.name === "report.md");
  const gapsArtifact = artifacts.find((a) => a.name === "gaps.json");
  const papersArtifact = artifacts.find((a) => a.name === "papers.json");
  if (els.resultLinks) {
    const chips = [];
    const debugHref = result.debug_url || (runId ? `/debug/?run=${encodeURIComponent(runId)}` : "");
    if (debugHref) {
      chips.push(`<a class="chip" href="${esc(debugHref)}">调试端打开本 run</a>`);
    }
    if (reportArtifact) {
      chips.push(`<a class="chip" href="${esc(reportArtifact.url)}" target="_blank" rel="noopener">打开报告</a>`);
      chips.push(`<a class="chip" href="${esc(reportArtifact.download_url)}" download>下载报告</a>`);
    }
    if (gapsArtifact) {
      chips.push(`<a class="chip" href="${esc(gapsArtifact.download_url)}" download>下载 Gaps</a>`);
    }
    if (papersArtifact) {
      chips.push(`<a class="chip" href="${esc(papersArtifact.download_url)}" download>下载文献 JSON</a>`);
    }
    if (result.output_dir) {
      chips.push(`<span class="chip muted-chip">产物目录 ${esc(result.output_dir)}</span>`);
    }
    els.resultLinks.innerHTML = chips.join("") || `<span class="muted">暂无快捷链接</span>`;
  }

  const gaps = result.gaps || [];
  document.getElementById("panel-gaps").innerHTML = gaps.length
    ? gaps
        .map((g) => {
          const evidence = (g.evidence || [])
            .map(
              (e) => `<div class="card">
                <div class="pills">
                  <span class="pill">${esc(e.paper_id)}</span>
                  <span class="pill">${esc(e.location)}</span>
                </div>
                <p class="muted">${esc(e.claim || "")}</p>
                <blockquote class="quote">${esc(e.quote || "")}</blockquote>
              </div>`
            )
            .join("");
          return `<article class="card">
            <div class="pills">
              <span class="pill warm">${esc(g.type)}</span>
              <span class="pill">${esc(g.review_status || "")}</span>
            </div>
            <h3>${esc(g.title)}</h3>
            <p>${esc(g.description || "")}</p>
            <p><strong>下一步：</strong>${esc(g.suggested_next_step || "—")}</p>
            <p><strong>如何证伪：</strong>${esc(g.falsification_test || "—")}</p>
            <h4>证据摘录</h4>
            ${evidence || '<p class="muted">暂无证据摘录</p>'}
          </article>`;
        })
        .join("")
    : `<p class="muted">未找到 Research Gaps。</p>`;

  const papers = result.papers || [];
  document.getElementById("panel-papers").innerHTML = papers.length
    ? papers
        .map((p) => {
          const doiHref = p.doi ? `https://doi.org/${encodeURIComponent(String(p.doi).replace(/^https?:\/\/(dx\.)?doi\.org\//i, ""))}` : "";
          const doiHtml = doiHref
            ? ` · <a href="${esc(doiHref)}" target="_blank" rel="noopener">DOI</a>`
            : "";
          return `<article class="card">
            <div class="pills">
              <span class="pill">${esc(p.year || "n/a")}</span>
              ${p.has_fulltext ? '<span class="pill">全文可用</span>' : ""}
              <span class="pill warm">引用 ${esc(p.cited_by ?? "—")}</span>
            </div>
            <h3>${esc(p.title)}</h3>
            <p class="muted">${esc(p.venue || "")}${doiHtml}${p.doi ? ` · ${esc(p.doi)}` : ""}</p>
            <p>${esc(p.abstract_preview || "")}</p>
          </article>`;
        })
        .join("")
    : `<p class="muted">暂无文献。</p>`;

  const routeA = result.route_a || [];
  document.getElementById("panel-routea").innerHTML = routeA.length
    ? routeA
        .map(
          (c) => `<article class="card">
            <div class="pills">
              <span class="pill warm">${esc(c.novelty || "")}</span>
              <span class="pill">${esc(c.material || "")}</span>
              <span class="pill">score ${Number(c.score ?? 0).toFixed(3)}</span>
              <span class="pill">${esc(c.validation || "n/a")}</span>
            </div>
            <h3>${esc(c.hypothesis || "")}</h3>
            <p class="muted">目标性质：${esc(c.property || "—")}</p>
          </article>`
        )
        .join("")
    : `<p class="muted">本次未启用 Route A，或无候选假说。</p>`;

  const reportActions = document.getElementById("reportActions");
  if (reportActions) {
    reportActions.innerHTML = reportArtifact
      ? `<a class="chip" href="${esc(reportArtifact.url)}" target="_blank" rel="noopener">新标签打开 report.md</a>
         <a class="chip" href="${esc(reportArtifact.download_url)}" download>下载 report.md</a>`
      : `<span class="muted">报告仅在页面内预览；完整文件将写入 outputs 后可下载。</span>`;
  }
  els.reportText.textContent = result.report_markdown || "暂无报告。";

  document.getElementById("panel-files").innerHTML = `
    <article class="card">
      <h3>本轮生成文档</h3>
      <p class="muted">来自 ${esc(result.output_dir || "outputs/…")}，可在线打开或下载到本地。</p>
      ${renderArtifactLinks(artifacts)}
    </article>
    <article class="card">
      <h3>相关说明文档</h3>
      ${renderDocLinks(docs, "暂无说明文档")}
    </article>`;

  loadExpertReview(window.__expertRunId).catch((err) => {
    const panel = document.getElementById("panel-expert");
    if (panel) panel.innerHTML = `<p class="error">专家核对加载失败：${esc(err.message || err)}</p>`;
  });

  els.results.classList.remove("hidden");
  els.compose.classList.add("hidden");
}

function levelPill(level) {
  const map = { must: "warm", should: "", expert: "accent" };
  return map[level] || "";
}

function hintLine(hint) {
  if (!hint || typeof hint !== "object") return "";
  const bits = [];
  if (hint.pass === true) bits.push("机器提示：倾向通过");
  if (hint.pass === false) bits.push("机器提示：倾向不通过");
  if (hint.pass == null && hint.na) bits.push("机器提示：本类型可标 N/A");
  if (hint.warn) bits.push("机器提示：需警惕");
  if (hint.note) bits.push(String(hint.note));
  if (hint.quote_in_chunk === true) bits.push("quote⊂chunk：命中");
  if (hint.quote_in_chunk === false) bits.push("quote⊂chunk：未命中");
  if (hint.boilerplate === true) bits.push("疑似 boilerplate");
  return bits.length ? `<p class="muted hint-machine">${esc(bits.join(" · "))}</p>` : "";
}

function displayBlock(display) {
  if (!display || typeof display !== "object") return "";
  const rows = Object.entries(display)
    .map(([k, v]) => {
      const val = typeof v === "object" ? JSON.stringify(v) : String(v ?? "—");
      return `<div class="display-row"><span class="k">${esc(k)}</span><span class="v">${esc(val)}</span></div>`;
    })
    .join("");
  return rows ? `<div class="display-box"><strong>核对对象</strong>${rows}</div>` : "";
}

function renderCheckCard(check, storageKey) {
  const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
  const verdict = saved[check.check_id]?.verdict || "";
  const notes = saved[check.check_id]?.notes || "";
  return `<article class="card check-card" data-check-id="${esc(check.check_id)}">
    <div class="pills">
      <span class="pill ${levelPill(check.level)}">标准 ${esc(check.standard_id)} · ${esc(check.level)}</span>
      <span class="pill">${esc(check.category)}</span>
      <span class="pill">${esc(check.object_type)}</span>
    </div>
    <h4>${esc(check.title)}</h4>
    <p><strong>核对问题：</strong>${esc(check.question)}</p>
    <p><strong>通过标准：</strong>${esc(check.pass_criteria)}</p>
    <p><strong>失败信号：</strong>${esc(check.fail_signals)}</p>
    ${displayBlock(check.display)}
    ${hintLine(check.machine_hint)}
    <label class="verdict-row">专家判决
      <select class="expert-verdict">
        <option value="">未判定</option>
        <option value="pass" ${verdict === "pass" ? "selected" : ""}>pass</option>
        <option value="fail" ${verdict === "fail" ? "selected" : ""}>fail</option>
        <option value="unsure" ${verdict === "unsure" ? "selected" : ""}>unsure</option>
        <option value="na" ${verdict === "na" ? "selected" : ""}>n/a</option>
      </select>
    </label>
    <label>备注<textarea class="expert-notes" rows="2">${esc(notes)}</textarea></label>
  </article>`;
}

function bindExpertEditors(root, storageKey) {
  root.querySelectorAll(".check-card").forEach((card) => {
    const id = card.getAttribute("data-check-id");
    const sel = card.querySelector(".expert-verdict");
    const ta = card.querySelector(".expert-notes");
    const persist = () => {
      const all = JSON.parse(localStorage.getItem(storageKey) || "{}");
      all[id] = { verdict: sel.value, notes: ta.value, updated_at: new Date().toISOString() };
      localStorage.setItem(storageKey, JSON.stringify(all));
    };
    sel.addEventListener("change", persist);
    ta.addEventListener("change", persist);
  });
}

async function loadExpertReview(runId) {
  const panel = document.getElementById("panel-expert");
  if (!panel) return;
  if (!runId) {
    panel.innerHTML = `<p class="muted">请先打开已有运行，以生成核对对象。</p>`;
    return;
  }
  panel.innerHTML = `<p class="muted">正在生成专家核对包…</p>`;
  const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/expert-review`);
  const pack = await res.json();
  if (!res.ok) throw new Error(pack.error || "expert-review failed");
  const storageKey = `expert-review:${runId}`;
  const cats = (pack.standards_doc?.categories || [])
    .map((c) => `<li><strong>${esc(c.id)}</strong> ${esc(c.name)} — ${esc(c.desc)}</li>`)
    .join("");
  const stdList = (pack.standards_doc?.standards || [])
    .map(
      (s) => `<tr>
        <td><code>${esc(s.id)}</code></td>
        <td>${esc(s.level)}</td>
        <td>${esc(s.title)}</td>
        <td>${esc(s.applies_to)}</td>
        <td>${esc(s.pass_criteria)}</td>
      </tr>`
    )
    .join("");
  const runChecks = (pack.objects?.run?.checks || []).map((c) => renderCheckCard(c, storageKey)).join("");
  const gapBlocks = (pack.objects?.gaps || [])
    .map((g) => {
      const gChecks = (g.checks || []).map((c) => renderCheckCard(c, storageKey)).join("");
      const ev = (g.evidence || [])
        .map((e) => {
          const eChecks = (e.checks || []).map((c) => renderCheckCard(c, storageKey)).join("");
          return `<div class="evidence-block">
            <h5>证据 ${esc(e.id)} · ${esc(e.paper_id)}</h5>
            <blockquote class="quote">${esc(e.quote || "")}</blockquote>
            <p class="muted">chunk=${esc(e.provenance?.chunk_id || "—")} · parser=${esc(e.provenance?.parser || "—")}</p>
            ${eChecks}
          </div>`;
        })
        .join("");
      return `<article class="card gap-review-block">
        <div class="pills">
          <span class="pill warm">${esc(g.gap_type)}</span>
          <span class="pill">${esc(g.id)}</span>
        </div>
        <h3>${esc(g.title)}</h3>
        <p>${esc(g.description || "")}</p>
        <p><strong>下一步：</strong>${esc(g.suggested_next_step || "—")}</p>
        <p><strong>证伪：</strong>${esc(g.falsification_test || "—")}</p>
        <h4>Gap 级标准核对</h4>
        ${gChecks}
        <h4>证据级标准核对</h4>
        ${ev || '<p class="muted">无证据</p>'}
      </article>`;
    })
    .join("");
  const paperBlocks = (pack.objects?.papers || [])
    .map((p) => {
      const checks = (p.checks || []).map((c) => renderCheckCard(c, storageKey)).join("");
      return `<article class="card">
        <h3>${esc(p.title || p.id)}</h3>
        <p class="muted">${esc(p.id)} · ${esc(p.year || "—")} · DOI ${esc(p.doi || "—")} · ${esc(p.fulltext_source || "—")}</p>
        ${checks}
      </article>`;
    })
    .join("");

  panel.innerHTML = `
    <article class="card">
      <h3>专家核对总览</h3>
      <p>运行 <code>${esc(pack.run_id)}</code> · 主题：${esc(pack.topic)}</p>
      <p class="muted">核对对象合计 <strong>${esc(pack.summary?.total_checks)}</strong>
        （运行 ${esc(pack.summary?.run_checks)} / Gap ${esc(pack.summary?.gap_checks)} /
        证据 ${esc(pack.summary?.evidence_checks)} / 文献 ${esc(pack.summary?.paper_checks)}）</p>
      <p><a class="chip" href="/api/runs/${esc(pack.run_id)}/expert-review" target="_blank" rel="noopener">打开核对包 JSON</a>
         <a class="chip" href="/api/expert-standards" target="_blank" rel="noopener">打开标准全集 JSON</a>
         <a class="chip" href="/debug/?run=${esc(pack.run_id)}" target="_blank" rel="noopener">调试端同页</a></p>
      <ol>${(pack.instructions?.user || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ol>
      <button type="button" class="ghost-btn" id="exportExpertVerdicts">导出本机判决 JSON</button>
    </article>
    <article class="card">
      <h3>标准目录（核对时对照 ID）</h3>
      <ul>${cats}</ul>
      <div class="table-wrap"><table class="std-table">
        <thead><tr><th>ID</th><th>等级</th><th>标题</th><th>对象</th><th>通过标准</th></tr></thead>
        <tbody>${stdList}</tbody>
      </table></div>
    </article>
    <h3 class="section-title">一、运行层核对对象</h3>
    ${runChecks}
    <h3 class="section-title">二、Gap + 证据核对对象</h3>
    ${gapBlocks || '<p class="muted">无 Gap</p>'}
    <h3 class="section-title">三、文献核对对象</h3>
    ${paperBlocks || '<p class="muted">无文献</p>'}
  `;
  bindExpertEditors(panel, storageKey);
  const exportBtn = document.getElementById("exportExpertVerdicts");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      const blob = new Blob(
        [JSON.stringify({ run_id: runId, verdicts: JSON.parse(localStorage.getItem(storageKey) || "{}") }, null, 2)],
        { type: "application/json" }
      );
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `expert-verdicts-${runId}.json`;
      a.click();
    });
  }
}

async function pollJob(jobId) {
  const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
  const job = await res.json();
  if (!res.ok) throw new Error(job.error || "任务查询失败");

  setBusy(true, job.status === "done" ? "完成" : "任务进行中", job.message || job.status);
  if (job.status === "done") {
    clearInterval(pollTimer);
    pollTimer = null;
    setBusy(false);
    renderResult(job.result || {});
    return;
  }
  if (job.status === "failed") {
    clearInterval(pollTimer);
    pollTimer = null;
    setBusy(false);
    showError(job.error || "任务失败");
  }
}

els.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const topic = els.topic.value.trim();
  if (topic.length < 3) {
    showError("请输入至少 3 个字符的主题");
    return;
  }
  setBusy(true, "已提交", "正在创建任务…");
  try {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic,
        profile: els.profile.value,
        route_a: els.routeA.checked,
      }),
    });
    const job = await res.json();
    if (!res.ok) throw new Error(job.error || "提交失败");
    setBusy(true, "排队/运行中", job.message || "请稍候");
    if (pollTimer) clearInterval(pollTimer);
    await pollJob(job.id);
    pollTimer = setInterval(() => {
      pollJob(job.id).catch((err) => {
        clearInterval(pollTimer);
        pollTimer = null;
        setBusy(false);
        showError(String(err.message || err));
      });
    }, 2000);
  } catch (err) {
    setBusy(false);
    showError(String(err.message || err));
  }
});

els.profile.addEventListener("change", updateHint);
if (els.topicPreset) {
  els.topicPreset.addEventListener("change", () => {
    const id = els.topicPreset.value;
    if (!id) {
      topicFromPreset = false;
      if (els.topicPresetHint) {
        els.topicPresetHint.textContent = "已切换为自定义：可直接在下方编辑主题。";
      }
      return;
    }
    applyTopicPreset(id);
  });
}
if (els.topic) {
  els.topic.addEventListener("input", () => {
    topicFromPreset = false;
    syncPresetWithTopicText();
  });
}
els.openRunBtn.addEventListener("click", async () => {
  showError("");
  const runId = els.existingRun.value;
  if (!runId) {
    showError("请先选择一个已有运行目录");
    return;
  }
  await openRunById(runId);
});

async function openRunById(runId) {
  showError("");
  setBusy(true, "加载中", `正在打开 ${runId}…`);
  try {
    window.__expertRunId = runId;
    const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/public`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "打开失败");
    setBusy(false);
    renderResult(data);
  } catch (err) {
    setBusy(false);
    showError(String(err.message || err));
  }
}

els.again.addEventListener("click", () => {
  els.results.classList.add("hidden");
  els.compose.classList.remove("hidden");
  showError("");
  const url = new URL(location.href);
  url.searchParams.delete("run");
  history.replaceState(null, "", url);
  loadExistingRuns().catch(() => {});
});

bindTabs();
Promise.all([
  loadProfiles(),
  loadTopicPresets(),
  loadExistingRuns(),
  loadComposeDocs(),
])
  .then(async () => {
    const bootRun = new URLSearchParams(location.search).get("run");
    if (!bootRun) return;
    if (els.existingRun) {
      const has = [...els.existingRun.options].some((o) => o.value === bootRun);
      if (!has) {
        const opt = document.createElement("option");
        opt.value = bootRun;
        opt.textContent = bootRun;
        els.existingRun.appendChild(opt);
      }
      els.existingRun.value = bootRun;
    }
    await openRunById(bootRun);
  })
  .catch((err) => showError(String(err.message || err)));
