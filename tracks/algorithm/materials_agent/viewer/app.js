const state = {
  runId: "",
  runs: [],
  papers: [],
  gaps: [],
  fulltext: [],
  verify: null,
  consistency: null,
  queries: [],
  report: "",
  routeA: [],
  routeSummary: null,
  metrics: null,
  scienceReview: null,
  audit: [],
  selectedGapId: null,
  topic: "",
};

const $ = (sel) => document.querySelector(sel);

function qsRun() {
  return new URLSearchParams(location.search).get("run") || "";
}

function setStatus(text) {
  $("#loadStatus").textContent = text;
}

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.text();
}

async function loadRuns() {
  const data = await fetchJson("/api/runs");
  state.runs = data.runs || [];
  const select = $("#runSelect");
  select.innerHTML = "";
  for (const run of state.runs) {
    const opt = document.createElement("option");
    opt.value = run.id;
    const verify = run.verify_status ? ` · ${run.verify_status}` : "";
    opt.textContent = `${run.id}${verify}`;
    select.appendChild(opt);
  }
  const preferred = qsRun() || "production";
  const exists = state.runs.some((r) => r.id === preferred);
  state.runId = exists ? preferred : state.runs[0]?.id || "";
  select.value = state.runId;
  select.addEventListener("change", () => {
    const next = select.value;
    const url = new URL(location.href);
    url.searchParams.set("run", next);
    location.href = url.toString();
  });
}

async function maybe(path) {
  try {
    return await fetchJson(path);
  } catch {
    return null;
  }
}

async function maybeText(path) {
  try {
    return await fetchText(path);
  } catch {
    return "";
  }
}

async function loadRun(runId) {
  if (!runId) {
    setStatus("未找到 outputs 运行目录");
    return;
  }
  setStatus(`加载 ${runId}…`);
  const base = `/api/run/${encodeURIComponent(runId)}`;
  const [
    papers,
    gaps,
    fulltext,
    verify,
    consistency,
    queries,
    report,
    routeA,
    routeSummary,
    bundle,
    metrics,
    audit,
    scienceReview,
  ] = await Promise.all([
    maybe(`${base}/papers.json`),
    maybe(`${base}/gaps.json`),
    maybe(`${base}/fulltext_index.json`),
    maybe(`${base}/production_verification.json`),
    maybe(`${base}/consistency.json`),
    maybe(`${base}/queries.json`),
    maybeText(`${base}/report.md`),
    maybe(`${base}/route_a_spr_candidates.json`),
    maybe(`${base}/route_a_run_summary.json`),
    maybe(`${base}/bundle.json`),
    maybe(`${base}/optimization_metrics.json`),
    maybe(`${base}/audit.json`),
    maybe(`${base}/science_review.json`),
  ]);

  state.papers = papers || [];
  state.gaps = gaps || [];
  state.fulltext = fulltext || [];
  state.verify = verify;
  state.consistency = consistency;
  state.queries = queries || [];
  state.report = report || "";
  state.routeA = routeA || [];
  state.routeSummary = routeSummary;
  state.metrics = metrics || (audit || []).find((a) => a.step === "optimization_metrics")?.meta || null;
  state.scienceReview = scienceReview;
  state.audit = audit || [];
  state.topic = bundle?.topic || state.runs.find((r) => r.id === runId)?.topic || runId;
  state.selectedGapId = state.gaps[0]?.id || null;
  renderAll();
  setStatus(`已加载 ${runId} · papers ${state.papers.length} · gaps ${state.gaps.length}`);
}

function ftMap() {
  const map = new Map();
  for (const row of state.fulltext) map.set(row.paper_id, row);
  return map;
}

function renderHero() {
  const status = state.verify?.status;
  const badge = $("#verifyBadge");
  badge.textContent = status
    ? `verify ${status}`
    : state.gaps.length
      ? "survey ready"
      : "no verification";
  badge.className = `eyebrow ${status === "PASS" ? "pass" : status === "FAIL" ? "fail" : "warn"}`;
  $("#topicTitle").textContent = state.topic || "Materials Literature Survey";
  const parsed = state.fulltext.filter((x) =>
    ["mineru", "grobid", "grobid_fusion"].includes(x.fulltext_source)
  ).length;
  const science = state.scienceReview?.status;
  $("#heroLede").textContent =
    `运行目录 outputs/${state.runId} · 全文可解析 ${parsed}/${state.papers.length || state.fulltext.length} · ` +
    `Gaps ${state.gaps.length}` +
    (state.consistency ? ` · consistency ${state.consistency.ok ? "PASS" : "FAIL"}` : "") +
    (science ? ` · science ${science}` : "");

  const userHref = `/?run=${encodeURIComponent(state.runId || "")}`;
  const userLink = $("#headerUserLink");
  if (userLink) userLink.href = userHref;
  const openUser = $("#openUserSameRun");
  if (openUser) openUser.href = userHref;

  const m = state.metrics || {};
  const flags = m.pass_flags || {};
  const pct = (v) => (v == null ? "—" : `${Math.round(Number(v) * 100)}%`);
  const metrics = [
    ["文献", state.papers.length],
    ["Gaps", state.gaps.length],
    ["全文解析", `${parsed}/${Math.max(state.papers.length, 1)}`],
    ["贴题率", pct(m.topic_hit_rate)],
    ["Gap对齐", pct(m.gap_material_alignment)],
    ["Route A", state.routeA.length],
  ];
  $("#metricStrip").innerHTML = metrics
    .map(
      ([label, value]) =>
        `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`
    )
    .join("");

  const align = $("#alignBar");
  if (align) {
    const gateClass = (v) => {
      const s = String(v || "").toUpperCase();
      if (s === "PASS" || v === true) return "gate-pass";
      if (s === "FAIL" || v === false) return "gate-fail";
      return "gate-na";
    };
    align.innerHTML = `<div class="align-inner"><strong>对齐条</strong>（同源不同步 · run=<code>${escapeHtml(
      state.runId || "—"
    )}</code>）
      <span class="gate ${gateClass(status)}">verify ${escapeHtml(status || "—")}</span>
      <span class="gate ${gateClass(science)}">science ${escapeHtml(science || "—")}</span>
      <span class="gate ${gateClass(state.consistency?.ok)}">consistency ${
        state.consistency == null ? "—" : state.consistency.ok ? "PASS" : "FAIL"
      }</span>
      <span class="gate ${gateClass(flags.topic_hit_rate)}">贴题 ${escapeHtml(pct(m.topic_hit_rate))}</span>
      <span class="gate ${gateClass(flags.gap_material_alignment)}">Gap对齐 ${escapeHtml(
      pct(m.gap_material_alignment)
    )}</span>
      <span class="gate ${gateClass(flags.provenance_coverage)}">溯源 ${escapeHtml(pct(m.provenance_coverage))}</span>
      <a class="btn ghost" href="${escapeHtml(userHref)}" style="text-decoration:none">用户端打开本 run</a>
    </div>`;
  }
}

function renderOverview() {
  const checks = state.verify?.checks || [];
  $("#verifyList").innerHTML = checks.length
    ? checks
        .map(
          (c) => `<div class="check-item">
            <i class="dot ${c.pass ? "pass" : "fail"}"></i>
            <div>
              <strong>${c.name}</strong>
              <span>${c.detail || (c.pass ? "ok" : "failed")}</span>
            </div>
          </div>`
        )
        .join("")
    : `<p class="muted">该运行没有 production_verification.json（例如 demo 或 route_a 独立产物）。</p>`;

  $("#consistencyNote").textContent = state.consistency
    ? `Consistency: ${state.consistency.ok ? "PASS" : "FAIL"} · issues=${(state.consistency.issues || []).length}`
    : "无 consistency.json";

  const m = state.metrics || {};
  const flags = m.pass_flags || {};
  const metricRows = [
    ["topic_hit_rate", "贴题命中率", m.topic_hit_rate, 0.7, true],
    ["gap_material_alignment", "Gap 材料对齐", m.gap_material_alignment, 0.8, true],
    ["evidence_boilerplate_rate", "证据噪声率", m.evidence_boilerplate_rate, 0.05, false],
    ["provenance_coverage", "证据溯源覆盖", m.provenance_coverage, 0.95, true],
  ];
  const metricsEl = $("#metricsList");
  if (metricsEl) {
    metricsEl.innerHTML = metricRows
      .map(([key, label, value, target, higherBetter]) => {
        const ok = flags[key];
        const pct = value == null ? "—" : `${Math.round(Number(value) * 100)}%`;
        const tip = higherBetter ? `目标 ≥${Math.round(target * 100)}%` : `目标 ≤${Math.round(target * 100)}%`;
        return `<div class="check-item">
            <i class="dot ${ok ? "pass" : ok === false ? "fail" : "warn"}"></i>
            <div>
              <strong>${label}: ${pct}</strong>
              <span>${tip}${m.topic_materials ? ` · topic=[${(m.topic_materials || []).join(", ")}]` : ""}</span>
            </div>
          </div>`;
      })
      .join("");
  }
  const retrieve = (state.audit || []).find((a) => a.step === "retrieve");
  const retrieveEl = $("#retrieveAudit");
  if (retrieveEl) {
    retrieveEl.textContent = retrieve
      ? JSON.stringify(
          {
            tool: retrieve.tool,
            output: retrieve.output_summary,
            topic_hit_rate: retrieve.meta?.topic_hit_rate,
            top_scores: retrieve.meta?.top_scores || [],
          },
          null,
          2
        )
      : "无 retrieve audit";
  }

  const counts = {};
  for (const row of state.fulltext) {
    const key = row.fulltext_source || "unknown";
    counts[key] = (counts[key] || 0) + 1;
  }
  const total = Math.max(1, state.fulltext.length);
  $("#fulltextChart").innerHTML = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([name, n]) => {
      const pct = Math.round((n / total) * 100);
      const cls = name === "mineru" ? "mineru" : name === "none" ? "none" : "";
      return `<div class="bar-row">
        <span>${name}</span>
        <div class="bar-track"><div class="bar-fill ${cls}" style="width:${pct}%"></div></div>
        <strong>${n}</strong>
      </div>`;
    })
    .join("") || `<p class="muted">无 fulltext_index.json</p>`;

  $("#fulltextLegend").innerHTML = Object.entries(counts)
    .map(([k, v]) => `<li>${k}: ${v}</li>`)
    .join("");

  $("#queryList").innerHTML = (state.queries || [])
    .map((q) => `<li>${escapeHtml(q)}</li>`)
    .join("") || "<li class='muted'>无 queries</li>";
}

function renderPapers() {
  const q = ($("#paperFilter").value || "").trim().toLowerCase();
  const source = $("#sourceFilter").value;
  const fmap = ftMap();
  const rows = state.papers.filter((p) => {
    const ft = fmap.get(p.id);
    const src = ft?.fulltext_source || "none";
    if (source !== "all" && src !== source) return false;
    if (!q) return true;
    const blob = `${p.id} ${p.title || ""} ${p.doi || ""}`.toLowerCase();
    return blob.includes(q);
  });

  $("#paperList").innerHTML = rows
    .map((p) => {
      const ft = fmap.get(p.id) || {};
      const src = ft.fulltext_source || "none";
      return `<article class="card">
        <div class="pill-row">
          <span class="pill">${escapeHtml(p.id)}</span>
          <span class="pill ${src === "none" ? "warn" : "accent"}">${escapeHtml(src)}</span>
          <span class="pill">${p.year || "n/a"}</span>
          <span class="pill">cited ${p.cited_by ?? "—"}</span>
        </div>
        <h3>${escapeHtml(p.title || "(untitled)")}</h3>
        <p class="meta">${escapeHtml(p.venue || "")}${p.doi ? ` · ${escapeHtml(p.doi)}` : ""}</p>
        <p class="muted">${escapeHtml((p.abstract || "").slice(0, 220))}${(p.abstract || "").length > 220 ? "…" : ""}</p>
      </article>`;
    })
    .join("") || `<p class="muted">没有匹配的文献。</p>`;
}

function renderGapNav() {
  $("#gapNav").innerHTML = state.gaps
    .map((g) => {
      const active = g.id === state.selectedGapId ? "active" : "";
      return `<button class="${active}" data-gap="${escapeHtml(g.id)}">
        <div class="pill-row"><span class="pill accent">${escapeHtml(g.gap_type || "")}</span>
        <span class="pill">${escapeHtml(g.review_status || "")}</span></div>
        <strong>${escapeHtml(g.title || g.id)}</strong>
      </button>`;
    })
    .join("") || `<p class="muted">无 gaps.json</p>`;

  $("#gapNav").querySelectorAll("button[data-gap]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.selectedGapId = btn.dataset.gap;
      renderGapNav();
      renderGapDetail();
    });
  });
}

function renderGapDetail() {
  const gap = state.gaps.find((g) => g.id === state.selectedGapId);
  if (!gap) {
    $("#gapDetail").innerHTML = `<p class="muted">选择左侧 Gap。</p>`;
    return;
  }
  const evidence = gap.evidence_chain || [];
  $("#gapDetail").innerHTML = `
    <div class="pill-row">
      <span class="pill accent">${escapeHtml(gap.gap_type || "")}</span>
      <span class="pill">novelty ${Number(gap.novelty ?? 0).toFixed(2)}</span>
      <span class="pill">action ${Number(gap.actionability ?? 0).toFixed(2)}</span>
      <span class="pill">${escapeHtml(gap.review_status || "")}</span>
    </div>
    <h2>${escapeHtml(gap.title || gap.id)}</h2>
    <p>${escapeHtml(gap.description || "")}</p>
    <p class="meta">support: ${(gap.supporting_paper_ids || []).map(escapeHtml).join(", ") || "—"}</p>
    <p class="meta">contradict: ${(gap.contradicting_paper_ids || []).map(escapeHtml).join(", ") || "—"}</p>
    <h3>下一步</h3>
    <p>${escapeHtml(gap.suggested_next_step || "—")}</p>
    <h3>证伪条件</h3>
    <p>${escapeHtml(gap.falsification_test || "—")}</p>
    <h3>证据链 (${evidence.length})</h3>
    <div class="evidence">
      ${
        evidence
          .map(
            (e) => `<div class="card">
              <div class="pill-row">
                <span class="pill">${escapeHtml(e.paper_id || "")}</span>
                <span class="pill">${escapeHtml(e.location || "")}</span>
                <span class="pill">conf ${Number(e.confidence ?? 0).toFixed(2)}</span>
              </div>
              <p class="meta">${escapeHtml(e.claim || "")}</p>
              <blockquote class="quote">${escapeHtml(e.quote_or_basis || "")}</blockquote>
              <p class="meta">${
                e.provenance
                  ? `chunk=${escapeHtml(e.provenance.chunk_id || "")} · hash=${escapeHtml(
                      (e.provenance.pdf_hash || "").slice(0, 12)
                    )}`
                  : "no provenance"
              }</p>
            </div>`
          )
          .join("") || `<p class="muted">无 evidence_chain</p>`
      }
    </div>
  `;
}

function renderRouteA() {
  const summary = state.routeSummary;
  $("#routeASummary").innerHTML = summary
    ? `<h2>Route A 摘要</h2>
       <div class="pill-row">
         <span class="pill accent">${escapeHtml(summary.status || "")}</span>
         <span class="pill">candidates ${summary.candidates ?? state.routeA.length}</span>
         ${(summary.external_providers || [])
           .map((p) => `<span class="pill">${escapeHtml(p)}</span>`)
           .join("")}
       </div>
       <p class="meta">roles: ${(summary.roles_seen || []).map(escapeHtml).join(" › ") || "—"}</p>`
    : state.routeA.length
      ? `<h2>Route A 候选</h2><p class="muted">已加载 candidates，无 run_summary。</p>`
      : `<h2>Route A</h2><p class="muted">当前运行没有 Route A 产物。可对 production 跑 scripts/run_route_a.py，或选择 production_route_a。</p>`;

  $("#routeAList").innerHTML = state.routeA
    .map(
      (c, i) => `<article class="card">
        <div class="pill-row">
          <span class="pill">#${i + 1}</span>
          <span class="pill accent">${escapeHtml(c.novelty_label || "")}</span>
          <span class="pill">score ${Number(c.score ?? 0).toFixed(3)}</span>
          <span class="pill">${escapeHtml((c.external_validation || {}).verdict || "n/a")}</span>
          <span class="pill">${escapeHtml(c.material_motif || "")}</span>
        </div>
        <h3>${escapeHtml(c.hypothesis || "")}</h3>
        <p class="meta">trace: ${(c.role_trace || []).map(escapeHtml).join(" › ")}</p>
        <p class="meta">MP: ${escapeHtml((c.external_validation || {}).detail || "")}
          ${
            (c.external_validation || {}).energy_above_hull != null
              ? ` · e_hull=${(c.external_validation || {}).energy_above_hull}`
              : ""
          }</p>
      </article>`
    )
    .join("");
}

function renderReport() {
  $("#reportBody").textContent = state.report || "暂无 report.md";
}

function levelPillClass(level) {
  if (level === "must") return "warn";
  if (level === "expert") return "accent";
  return "";
}

function machineHintHtml(hint) {
  if (!hint || typeof hint !== "object") return "";
  const bits = [];
  if (hint.pass === true) bits.push("机器：倾向通过");
  if (hint.pass === false) bits.push("机器：倾向不通过");
  if (hint.pass == null && hint.na) bits.push("机器：可标 N/A");
  if (hint.warn) bits.push("机器：需警惕");
  if (hint.note) bits.push(String(hint.note));
  if (hint.quote_in_chunk === true) bits.push("quote⊂chunk 命中");
  if (hint.quote_in_chunk === false) bits.push("quote⊂chunk 未命中");
  if (hint.boilerplate === true) bits.push("疑似 boilerplate");
  if (hint.chunk_preview) bits.push(`chunk预览：${String(hint.chunk_preview).slice(0, 120)}…`);
  return bits.length ? `<p class="muted">${escapeHtml(bits.join(" · "))}</p>` : "";
}

function displayHtml(display) {
  if (!display || typeof display !== "object") return "";
  const rows = Object.entries(display)
    .map(([k, v]) => {
      const val = typeof v === "object" ? JSON.stringify(v) : String(v ?? "—");
      return `<div class="display-row"><code>${escapeHtml(k)}</code> ${escapeHtml(val)}</div>`;
    })
    .join("");
  return rows ? `<div class="display-box"><strong>核对对象</strong>${rows}</div>` : "";
}

function checkCardHtml(check, storageKey) {
  const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
  const verdict = saved[check.check_id]?.verdict || "";
  const notes = saved[check.check_id]?.notes || "";
  return `<article class="surface check-card" data-check-id="${escapeHtml(check.check_id)}">
    <div class="pill-row">
      <span class="pill ${levelPillClass(check.level)}">标准 ${escapeHtml(check.standard_id)} · ${escapeHtml(check.level)}</span>
      <span class="pill">${escapeHtml(check.category)}</span>
      <span class="pill">${escapeHtml(check.object_type)}:${escapeHtml(check.object_id)}</span>
    </div>
    <h3>${escapeHtml(check.title)}</h3>
    <p><strong>核对问题：</strong>${escapeHtml(check.question)}</p>
    <p><strong>通过标准：</strong>${escapeHtml(check.pass_criteria)}</p>
    <p><strong>失败信号：</strong>${escapeHtml(check.fail_signals)}</p>
    ${displayHtml(check.display)}
    ${machineHintHtml(check.machine_hint)}
    <label class="verdict-row">专家判决
      <select class="expert-verdict">
        <option value="">未判定</option>
        <option value="pass" ${verdict === "pass" ? "selected" : ""}>pass</option>
        <option value="fail" ${verdict === "fail" ? "selected" : ""}>fail</option>
        <option value="unsure" ${verdict === "unsure" ? "selected" : ""}>unsure</option>
        <option value="na" ${verdict === "na" ? "selected" : ""}>n/a</option>
      </select>
    </label>
    <label>备注<textarea class="expert-notes" rows="2">${escapeHtml(notes)}</textarea></label>
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

async function renderExpertReview() {
  const root = $("#expertRoot");
  const meta = $("#expertMeta");
  if (!root) return;
  const runId = state.runId;
  if (!runId) {
    root.innerHTML = `<p class="muted">未选择运行。</p>`;
    return;
  }
  root.innerHTML = `<p class="muted">正在生成专家核对包…</p>`;
  try {
    const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/expert-review`);
    const pack = await res.json();
    if (!res.ok) throw new Error(pack.error || "expert-review failed");
    state.expertPack = pack;
    const storageKey = `expert-review-debug:${runId}`;
    if (meta) {
      meta.textContent = `run=${pack.run_id} · 核对项 ${pack.summary?.total_checks ?? "—"} · 标准 ${
        (pack.standards_doc?.standards || []).length
      } 条`;
    }
    const cats = (pack.standards_doc?.categories || [])
      .map((c) => `<li><strong>${escapeHtml(c.id)}</strong> ${escapeHtml(c.name)} — ${escapeHtml(c.desc)}</li>`)
      .join("");
    const stdRows = (pack.standards_doc?.standards || [])
      .map(
        (s) => `<tr>
          <td><code>${escapeHtml(s.id)}</code></td>
          <td>${escapeHtml(s.level)}</td>
          <td>${escapeHtml(s.title)}</td>
          <td>${escapeHtml(s.applies_to)}</td>
          <td>${escapeHtml(s.pass_criteria)}</td>
          <td>${escapeHtml(s.fail_signals)}</td>
        </tr>`
      )
      .join("");
    const runChecks = (pack.objects?.run?.checks || []).map((c) => checkCardHtml(c, storageKey)).join("");
    const gapBlocks = (pack.objects?.gaps || [])
      .map((g) => {
        const gChecks = (g.checks || []).map((c) => checkCardHtml(c, storageKey)).join("");
        const ev = (g.evidence || [])
          .map((e) => {
            const eChecks = (e.checks || []).map((c) => checkCardHtml(c, storageKey)).join("");
            const chunkPrev = e.chunk_preview || e.provenance?.chunk_preview || "";
            return `<div class="evidence-block">
              <h4>证据 ${escapeHtml(e.id)} · paper ${escapeHtml(e.paper_id)}</h4>
              <blockquote class="quote">${escapeHtml(e.quote || "")}</blockquote>
              <p class="muted">claim=${escapeHtml(e.claim || "—")} · chunk=${escapeHtml(
              e.provenance?.chunk_id || "—"
            )} · parser=${escapeHtml(e.provenance?.parser || "—")} · pdf=${escapeHtml(
              String(e.provenance?.pdf_hash || "").slice(0, 16) || "—"
            )}</p>
              ${chunkPrev ? `<pre class="chunk-preview">${escapeHtml(chunkPrev)}</pre>` : ""}
              ${eChecks}
            </div>`;
          })
          .join("");
        return `<div class="gap-review-block">
          <div class="pill-row">
            <span class="pill warn">${escapeHtml(g.gap_type)}</span>
            <span class="pill">${escapeHtml(g.id)}</span>
          </div>
          <h3>${escapeHtml(g.title)}</h3>
          <p>${escapeHtml(g.description || "")}</p>
          <p><strong>下一步：</strong>${escapeHtml(g.suggested_next_step || "—")}</p>
          <p><strong>证伪：</strong>${escapeHtml(g.falsification_test || "—")}</p>
          <h4>Gap 级标准</h4>
          ${gChecks}
          <h4>证据级标准</h4>
          ${ev || '<p class="muted">无证据</p>'}
        </div>`;
      })
      .join("");
    const paperBlocks = (pack.objects?.papers || [])
      .map((p) => {
        const checks = (p.checks || []).map((c) => checkCardHtml(c, storageKey)).join("");
        return `<article class="surface">
          <h3>${escapeHtml(p.title || p.id)}</h3>
          <p class="muted">${escapeHtml(p.id)} · ${escapeHtml(p.year || "—")} · DOI ${escapeHtml(
          p.doi || "—"
        )} · src ${escapeHtml(p.fulltext_source || "—")}</p>
          ${p.abstract_preview ? `<p class="muted">${escapeHtml(p.abstract_preview)}</p>` : ""}
          ${checks}
        </article>`;
      })
      .join("");

    root.innerHTML = `
      <article class="surface">
        <h3>核对总览</h3>
        <p>主题：${escapeHtml(pack.topic)}</p>
        <p class="muted">运行 ${escapeHtml(pack.summary?.run_checks)} / Gap ${escapeHtml(
      pack.summary?.gap_checks
    )} / 证据 ${escapeHtml(pack.summary?.evidence_checks)} / 文献 ${escapeHtml(pack.summary?.paper_checks)}</p>
        <p class="pill-row">
          <a class="btn ghost" href="/api/runs/${escapeHtml(pack.run_id)}/expert-review" target="_blank" rel="noopener">核对包 JSON</a>
          <a class="btn ghost" href="/api/expert-standards" target="_blank" rel="noopener">标准全集 JSON</a>
          <a class="btn ghost" href="/" target="_blank" rel="noopener">用户端</a>
          <button type="button" class="btn ghost" id="exportExpertVerdictsDebug">导出判决</button>
        </p>
        <ol>${(pack.instructions?.debug || pack.instructions?.user || [])
          .map((x) => `<li>${escapeHtml(x)}</li>`)
          .join("")}</ol>
      </article>
      <article class="surface">
        <h3>标准目录（全部 ID）</h3>
        <ul>${cats}</ul>
        <div class="table-wrap"><table class="std-table">
          <thead><tr><th>ID</th><th>等级</th><th>标题</th><th>对象</th><th>通过</th><th>失败信号</th></tr></thead>
          <tbody>${stdRows}</tbody>
        </table></div>
      </article>
      <h3 class="section-title">一、运行层</h3>
      ${runChecks}
      <h3 class="section-title">二、Gap + 证据</h3>
      ${gapBlocks || '<p class="muted">无 Gap</p>'}
      <h3 class="section-title">三、文献</h3>
      ${paperBlocks || '<p class="muted">无文献</p>'}
    `;
    bindExpertEditors(root, storageKey);
    const exportBtn = $("#exportExpertVerdictsDebug");
    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        const blob = new Blob(
          [
            JSON.stringify(
              { run_id: runId, audience: "debug", verdicts: JSON.parse(localStorage.getItem(storageKey) || "{}") },
              null,
              2
            ),
          ],
          { type: "application/json" }
        );
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `expert-verdicts-debug-${runId}.json`;
        a.click();
      });
    }
  } catch (err) {
    root.innerHTML = `<p class="error">专家核对加载失败：${escapeHtml(err.message || err)}</p>`;
    if (meta) meta.textContent = "加载失败";
  }
}

function renderAll() {
  renderHero();
  renderOverview();
  renderPapers();
  renderGapNav();
  renderGapDetail();
  renderRouteA();
  renderReport();
  renderExpertReview();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      $(`#panel-${tab.dataset.tab}`).classList.add("active");
    });
  });
  $("#paperFilter").addEventListener("input", renderPapers);
  $("#sourceFilter").addEventListener("change", renderPapers);
}

async function main() {
  bindTabs();
  try {
    await loadRuns();
    await loadRun(state.runId);
  } catch (err) {
    setStatus(String(err));
    $("#topicTitle").textContent = "无法加载产物";
    $("#heroLede").textContent =
      "请先运行 python scripts/serve_viewer.py，并确保 outputs/ 下已有 survey 结果。";
  }
}

main();
