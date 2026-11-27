(() => {
  "use strict";

  const TOPIC_COLORS = {
    LLM: "var(--c-llm)",
    Multimodal: "var(--c-vlm)",
    VisionGen: "var(--c-gen)",
    RLPostTraining: "var(--c-rl)",
    EfficiencySystems: "var(--c-sys)",
    EmbodiedRobotics: "var(--c-bot)",
    DataEvalSurvey: "var(--c-eval)",
    ScienceOther: "var(--c-sci)",
  };

  const state = {
    manifest: null,
    topicMap: {},
    dayCache: {},
    surveyCache: {},
    searchIndex: null,
    view: "daily", // daily | archive | surveys | saved
    currentDate: null,
    currentSurvey: null,
    lang: localStorage.getItem("hfp_lang") || "zh",
    density: localStorage.getItem("hfp_density") || "compact", // compact | expanded
    dailyFilter: { q: "", topic: "ALL", signal: false, code: false, focus: false, sort: "topic" },
    archFilter: { q: "", topic: "ALL", signal: false, code: false },
    saved: JSON.parse(localStorage.getItem("hfp_saved_v1") || "{}"),
    drawerList: [],
    drawerIdx: -1,
  };

  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  function saveBookmarks() {
    localStorage.setItem("hfp_saved_v1", JSON.stringify(state.saved));
    $("nav-cnt-saved").textContent = Object.keys(state.saved).length;
  }

  function applyLang() {
    document.documentElement.setAttribute("data-lang", state.lang);
    $("btn-lang").textContent = state.lang === "zh" ? "EN" : "中文";
    localStorage.setItem("hfp_lang", state.lang);
  }

  function applyDensityLabel() {
    const exp = state.density === "expanded";
    $("density-zh").textContent = exp ? "紧凑账本" : "内联精读";
    $("density-en").textContent = exp ? "Compact" : "Expanded";
    localStorage.setItem("hfp_density", state.density);
  }

  function initTheme() {
    const stored = localStorage.getItem("hfp_theme");
    if (stored === "light" || stored === "dark") {
      document.documentElement.setAttribute("data-theme", stored);
    }
    $("btn-theme").addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme");
      const isDark =
        cur === "dark" || (!cur && window.matchMedia("(prefers-color-scheme: dark)").matches);
      const next = isDark ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("hfp_theme", next);
    });
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
    return res.json();
  }

  async function ensureDay(date) {
    if (!state.dayCache[date]) {
      state.dayCache[date] = await fetchJson(`data/daily/${date}.json`);
    }
    return state.dayCache[date];
  }

  async function ensureSearchIndex() {
    if (!state.searchIndex) {
      state.searchIndex = await fetchJson("data/search.json");
    }
    return state.searchIndex;
  }

  async function ensureSurvey(slug) {
    if (!state.surveyCache[slug]) {
      state.surveyCache[slug] = await fetchJson(`data/surveys/${slug}.json`);
    }
    return state.surveyCache[slug];
  }

  function topicLabel(key) {
    const meta = state.topicMap[key];
    if (!meta) return key;
    return state.lang === "en" ? meta.label_en : meta.label_zh;
  }

  function renderSignalPips(score) {
    const s = Math.max(1, Math.min(5, Number(score) || 3));
    let html = `<span class="pips" title="Signal ${s}/5">`;
    for (let i = 1; i <= 5; i++) {
      const cls = i <= s ? (s >= 4 ? "pip on hi" : "pip on") : "pip";
      html += `<i class="${cls}"></i>`;
    }
    html += `</span>`;
    return html;
  }

  /* ========================================================================
     Pulse Strip & Date Navigation
     ======================================================================== */
  function renderPulseStrip() {
    const days = [...state.manifest.days].reverse(); // chronological left -> right
    const maxCnt = Math.max(1, ...days.map((d) => d.count));
    const barsEl = $("pulse-bars");
    barsEl.innerHTML = days
      .map((d) => {
        const h = Math.max(12, Math.round((d.count / maxCnt) * 100));
        const active = d.date === state.currentDate ? "is-active" : "";
        return `<button type="button" class="pbar ${active}" style="height:${h}%" data-date="${d.date}" aria-label="${d.date} (${d.count} papers)"></button>`;
      })
      .join("");

    barsEl.querySelectorAll(".pbar").forEach((btn) => {
      btn.addEventListener("mouseenter", () => {
        const dt = btn.dataset.date;
        const info = state.manifest.days.find((x) => x.date === dt);
        if (info) {
          $("pulse-readout").textContent = `${info.date} · ${info.count} PAPERS · ▲ ${info.total_upvotes} UPVOTES · ${info.code_count} CODE`;
        }
      });
      btn.addEventListener("click", () => {
        location.hash = `#daily/${btn.dataset.date}`;
      });
    });

    const sel = $("date-select");
    sel.innerHTML = state.manifest.days
      .map((d) => `<option value="${d.date}" ${d.date === state.currentDate ? "selected" : ""}>${d.date} (${d.count})</option>`)
      .join("");

    const idx = state.manifest.days.findIndex((d) => d.date === state.currentDate);
    // manifest.days is newest-first: idx+1 is older (prev), idx-1 is newer (next)
    $("btn-prev-day").disabled = idx < 0 || idx >= state.manifest.days.length - 1;
    $("btn-next-day").disabled = idx <= 0;
  }

  /* ========================================================================
     Daily View Rendering
     ======================================================================== */
  async function renderDailyView() {
    $("pulse-section").hidden = false;
    renderPulseStrip();
    const issue = await ensureDay(state.currentDate);
    const papers = issue.papers || [];
    const dayIndex = state.manifest.days.length - state.manifest.days.findIndex((d) => d.date === issue.date);
    const weekday = new Date(issue.date + "T00:00:00Z").toLocaleDateString(
      state.lang === "en" ? "en-US" : "zh-CN",
      { weekday: "long", timeZone: "UTC" }
    );

    // Top 2 stubs: #1 by upvotes, #2 highest signal distinct paper
    const byVotes = [...papers].sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0));
    const topVote = byVotes[0];
    const topSignal =
      byVotes.find((p) => p !== topVote && (p.insight_score || 0) >= 4 && p.github_url) ||
      byVotes.find((p) => p !== topVote && (p.insight_score || 0) >= 4) ||
      byVotes[1];

    // Spectrum bar
    const countsByTopic = {};
    papers.forEach((p) => {
      countsByTopic[p.topic] = (countsByTopic[p.topic] || 0) + 1;
    });
    const specHtml = state.manifest.topics
      .filter((t) => countsByTopic[t.key])
      .map((t) => {
        const c = countsByTopic[t.key];
        const pct = ((c / papers.length) * 100).toFixed(1);
        return `<div class="spec-seg" data-topic="${t.key}" style="width:${pct}%;background:${TOPIC_COLORS[t.key]}" title="${topicLabel(t.key)}: ${c}"></div>`;
      })
      .join("");

    const stubCard = (p, kicker, metricHtml) => {
      if (!p) return "";
      const title = state.lang === "en" && p.title ? p.title : p.title_zh || p.title;
      return `
        <button type="button" class="stub" data-open-id="${esc(p.arxiv_id)}">
          <span class="stub-kicker">${kicker} · arXiv ${esc(p.arxiv_id)}</span>
          <span class="stub-num">${metricHtml}</span>
          <div class="stub-body">
            <div class="stub-title">${esc(title)}</div>
            <div class="stub-sub">${esc(p.tldr || "")}</div>
          </div>
        </button>`;
    };

    $("issue-hero").innerHTML = `
      <div>
        <p class="eyebrow">ISSUE #${String(dayIndex).padStart(3, "0")} · ${esc(weekday)} · ${esc(issue.date)}</p>
        <h1 class="issue-title">
          <span class="zh">${esc(issue.date)} 论文账本</span>
          <span class="en">Daily Ledger · ${esc(issue.date)}</span>
        </h1>
        <p class="issue-brief">${esc(issue.daily_brief || "")}</p>
        <div class="kpi-strip">
          <span><b>${papers.length}</b> <span class="zh">篇收录</span><span class="en">Papers</span></span>
          <span><b>▲ ${issue.total_upvotes || 0}</b> <span class="zh">社区总票数</span><span class="en">Total Votes</span></span>
          <span><b>${issue.code_count || 0}</b> <span class="zh">篇附代码</span><span class="en">With Code</span></span>
          <span><b>${issue.high_signal_count || 0}</b> <span class="zh">篇高信号</span><span class="en">Signal ≥4</span></span>
          <a href="${esc(issue.list_url)}" target="_blank" rel="noopener" style="text-decoration:underline">HF Source ↗</a>
        </div>
        <div class="spectrum-wrap">
          <div class="spectrum-bar">${specHtml}</div>
        </div>
      </div>
      <div class="stubs">
        ${stubCard(topVote, state.lang === "en" ? "TOP COMMUNITY VOTE" : "最高社区关注", `${topVote?.upvotes || 0}<small>▲</small>`)}
        ${stubCard(topSignal, state.lang === "en" ? "HIGH-SIGNAL SELECTION" : "重点方法信号", `${topSignal?.insight_score || 4}<small>/5</small>`)}
      </div>
    `;

    $("issue-hero").querySelectorAll(".spec-seg").forEach((seg) => {
      seg.addEventListener("click", () => {
        const tk = seg.dataset.topic;
        state.dailyFilter.topic = state.dailyFilter.topic === tk ? "ALL" : tk;
        renderDailyLedger(issue);
      });
    });

    $("issue-hero").querySelectorAll("[data-open-id]").forEach((btn) => {
      btn.addEventListener("click", () => openDrawerById(papers, btn.dataset.openId, issue.date));
    });

    renderDailyLedger(issue);
  }

  function renderTopicPills(containerId, countsByTopic, totalCount, activeTopic, onSelect) {
    const el = $(containerId);
    let html = `<button type="button" class="pill" data-t="ALL" aria-pressed="${activeTopic === "ALL"}">
      <span>${state.lang === "en" ? "All" : "全部"}</span><span class="cnt">${totalCount}</span>
    </button>`;
    state.manifest.topics.forEach((t) => {
      const cnt = countsByTopic[t.key] || 0;
      if (!cnt) return;
      html += `<button type="button" class="pill" data-t="${t.key}" aria-pressed="${activeTopic === t.key}">
        <span class="dot" style="background:${TOPIC_COLORS[t.key]}"></span>
        <span>${esc(topicLabel(t.key))}</span>
        <span class="cnt">${cnt}</span>
      </button>`;
    });
    el.innerHTML = html;
    el.querySelectorAll(".pill").forEach((btn) => {
      btn.addEventListener("click", () => onSelect(btn.dataset.t));
    });
  }

  function renderPaperRowHtml(p, dateStr) {
    const isSaved = Boolean(state.saved[p.arxiv_id]);
    const titlePrimary = state.lang === "en" && p.title ? p.title : p.title_zh || p.title;
    const showEnSub = state.lang === "zh" && p.title && p.title !== p.title_zh;
    const exp = state.density === "expanded" && (p.problem || p.method || p.result);

    return `
      <article class="ledger-row" data-aid="${esc(p.arxiv_id)}" data-date="${esc(dateStr)}" tabindex="0">
        <div class="row-votes">
          <span class="vote-num">▲ ${p.upvotes || 0}</span>
          <span class="arxiv-num">${esc(p.arxiv_id)}</span>
        </div>
        <div class="row-body">
          <div class="row-title-line">
            <span class="row-title">${esc(titlePrimary)}</span>
            ${p.github_url ? `<span class="badge badge-code">CODE</span>` : ""}
            ${(p.insight_score || 0) >= 5 ? `<span class="badge badge-pick">TOP SIGNAL</span>` : ""}
            ${p.focus_match ? `<span class="badge badge-focus">FOCUS</span>` : ""}
            ${p.org ? `<span class="badge badge-org">· ${esc(p.org)}</span>` : ""}
          </div>
          ${showEnSub ? `<div class="row-en mono">${esc(p.title)}</div>` : ""}
          <div class="row-tldr">${esc(p.tldr || "")}</div>
          ${
            exp
              ? `<div class="row-expanded-grid">
                  <div class="exp-cell"><strong>${state.lang === "en" ? "Problem" : "问题"}</strong>${esc(p.problem || "—")}</div>
                  <div class="exp-cell"><strong>${state.lang === "en" ? "Method" : "方法"}</strong>${esc(p.method || "—")}</div>
                  <div class="exp-cell"><strong>${state.lang === "en" ? "Result" : "实验结果"}</strong>${esc(p.result || "—")}</div>
                </div>`
              : ""
          }
        </div>
        <div class="row-right">
          ${renderSignalPips(p.insight_score)}
          <button type="button" class="star-btn ${isSaved ? "is-saved" : ""}" data-star="${esc(p.arxiv_id)}" title="收藏待读 / Bookmark">
            ${isSaved ? "★" : "☆"}
          </button>
        </div>
      </article>`;
  }

  function bindLedgerInteractions(container, listContext, fallbackDate) {
    container.querySelectorAll("[data-star]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const aid = btn.dataset.star;
        const row = btn.closest(".ledger-row");
        const dt = row?.dataset.date || fallbackDate;
        if (state.saved[aid]) {
          delete state.saved[aid];
        } else {
          const item = listContext.find((x) => x.arxiv_id === aid);
          if (item) {
            state.saved[aid] = { ...item, date: dt };
          }
        }
        saveBookmarks();
        btn.classList.toggle("is-saved", Boolean(state.saved[aid]));
        btn.textContent = state.saved[aid] ? "★" : "☆";
        if (state.view === "saved") renderSavedView();
      });
    });

    container.querySelectorAll(".ledger-row").forEach((row) => {
      const trigger = async () => {
        const aid = row.dataset.aid;
        const dt = row.dataset.date || fallbackDate;
        let fullList = listContext;
        // If clicked from compact search rows, load full day JSON so drawer has complete fields
        const sample = listContext.find((x) => x.arxiv_id === aid);
        if (sample && sample._fromSearch && dt) {
          const dayObj = await ensureDay(dt);
          fullList = dayObj.papers || listContext;
        }
        openDrawerById(fullList, aid, dt);
      };
      row.addEventListener("click", trigger);
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter") trigger();
      });
    });
  }

  function renderDailyLedger(issue) {
    const allPapers = issue.papers || [];
    const counts = {};
    allPapers.forEach((p) => (counts[p.topic] = (counts[p.topic] || 0) + 1));

    renderTopicPills("daily-topic-pills", counts, allPapers.length, state.dailyFilter.topic, (t) => {
      state.dailyFilter.topic = t;
      renderDailyLedger(issue);
    });

    const f = state.dailyFilter;
    const q = f.q.trim().toLowerCase();
    const filtered = allPapers.filter((p) => {
      if (f.topic !== "ALL" && p.topic !== f.topic) return false;
      if (f.signal && (p.insight_score || 0) < 4) return false;
      if (f.code && !p.github_url) return false;
      if (f.focus && !p.focus_match) return false;
      if (q) {
        const hay = `${p.arxiv_id} ${p.title_zh} ${p.title} ${p.org || ""} ${p.tldr || ""} ${p.method || ""} ${(p.tags || []).join(" ")}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    const container = $("daily-ledger");
    if (!filtered.length) {
      container.innerHTML = `<div class="empty-state">没有匹配的当日论文。如要跨月检索历史库，请点击顶部「全景归档与检索」。</div>`;
      return;
    }

    if (f.sort === "topic") {
      let html = "";
      const flatOrder = [];
      state.manifest.topics.forEach((t) => {
        const group = filtered
          .filter((p) => p.topic === t.key)
          .sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0));
        if (!group.length) return;
        group.forEach((g) => flatOrder.push(g));
        html += `
          <section class="topic-group">
            <div class="topic-head">
              <h2><span class="topic-swatch" style="background:${TOPIC_COLORS[t.key]}"></span>${esc(topicLabel(t.key))}</h2>
              <span class="topic-meta">${t.code} · ${group.length} ${state.lang === "en" ? "PAPERS" : "篇"}</span>
            </div>
            <div>${group.map((p) => renderPaperRowHtml(p, issue.date)).join("")}</div>
          </section>`;
      });
      container.innerHTML = html;
      bindLedgerInteractions(container, flatOrder, issue.date);
    } else {
      const sorted = [...filtered].sort((a, b) =>
        f.sort === "signal"
          ? (b.insight_score || 0) - (a.insight_score || 0) || (b.upvotes || 0) - (a.upvotes || 0)
          : (b.upvotes || 0) - (a.upvotes || 0)
      );
      container.innerHTML = `<section class="topic-group">${sorted.map((p) => renderPaperRowHtml(p, issue.date)).join("")}</section>`;
      bindLedgerInteractions(container, sorted, issue.date);
    }
  }

  /* ========================================================================
     Archive Calendar Matrix & Cross-Month Search
     ======================================================================== */
  async function renderArchiveView() {
    $("pulse-section").hidden = true;
    const stats = state.manifest.stats;
    $("archive-summary").textContent =
      state.lang === "en"
        ? `${stats.issue_count} active daily issues (${stats.earliest_date} to ${stats.latest_date}), indexing ${stats.paper_count} Hugging Face papers.`
        : `自 ${stats.earliest_date} 至 ${stats.latest_date} 共收录 ${stats.issue_count} 期有效日报、合计 ${stats.paper_count} 篇论文（已自动剔除无更新的空周末）。点击任意日历格直达当期账本，或在下方直接跨月检索。`;

    renderCalendarMatrices();
    const sIdx = await ensureSearchIndex();
    renderArchiveSearchResults(sIdx);
  }

  function renderCalendarMatrices() {
    const dayMap = {};
    state.manifest.days.forEach((d) => (dayMap[d.date] = d));
    const months = [...new Set(state.manifest.days.map((d) => d.date.slice(0, 7)))].sort();

    const html = months
      .map((ym) => {
        const [y, m] = ym.split("-").map(Number);
        const firstDay = new Date(Date.UTC(y, m - 1, 1));
        const startOffset = (firstDay.getUTCDay() + 6) % 7; // Monday = 0
        const daysInMonth = new Date(Date.UTC(y, m, 0)).getUTCDate();
        let monthPapers = 0;
        let cells = "";
        for (let i = 0; i < startOffset; i++) {
          cells += `<div class="cal-cell empty"></div>`;
        }
        for (let d = 1; d <= daysInMonth; d++) {
          const dateStr = `${ym}-${String(d).padStart(2, "0")}`;
          const info = dayMap[dateStr];
          if (info) {
            monthPapers += info.count;
            const lvl = info.count >= 35 ? "lvl-3" : info.count >= 20 ? "lvl-2" : "lvl-1";
            cells += `<button type="button" class="cal-cell has-data ${lvl}" data-cal-date="${dateStr}" title="${dateStr}: ${info.count} 篇">
              <span>${d}</span><small>${info.count}</small>
            </button>`;
          } else {
            cells += `<div class="cal-cell" title="${dateStr} (无更新)"><span>${d}</span></div>`;
          }
        }
        return `
          <div class="cal-card">
            <div class="cal-title"><span>${ym}</span><span>${monthPapers} ${state.lang === "en" ? "papers" : "篇"}</span></div>
            <div class="cal-weekdays"><span>MO</span><span>TU</span><span>WE</span><span>TH</span><span>FR</span><span>SA</span><span>SU</span></div>
            <div class="cal-grid">${cells}</div>
          </div>`;
      })
      .join("");

    const calEl = $("cal-months");
    calEl.innerHTML = html;
    calEl.querySelectorAll("[data-cal-date]").forEach((btn) => {
      btn.addEventListener("click", () => {
        location.hash = `#daily/${btn.dataset.calDate}`;
      });
    });
  }

  function renderArchiveSearchResults(sIdx) {
    const rows = sIdx.rows || [];
    const counts = {};
    rows.forEach((r) => (counts[r[2]] = (counts[r[2]] || 0) + 1));

    renderTopicPills("arch-topic-pills", counts, rows.length, state.archFilter.topic, (t) => {
      state.archFilter.topic = t;
      renderArchiveSearchResults(sIdx);
    });

    const f = state.archFilter;
    const q = f.q.trim().toLowerCase();
    const matched = [];
    for (const r of rows) {
      // [0:date, 1:arxiv_id, 2:topic, 3:upvotes, 4:score, 5:code, 6:title_zh, 7:title_en, 8:org, 9:tldr]
      if (f.topic !== "ALL" && r[2] !== f.topic) continue;
      if (f.signal && r[4] < 4) continue;
      if (f.code && !r[5]) continue;
      if (q) {
        const hay = `${r[0]} ${r[1]} ${r[6]} ${r[7]} ${r[8]} ${r[9]}`.toLowerCase();
        if (!hay.includes(q)) continue;
      }
      matched.push({
        _fromSearch: true,
        date: r[0],
        arxiv_id: r[1],
        topic: r[2],
        upvotes: r[3],
        insight_score: r[4],
        github_url: r[5] ? "1" : null,
        title_zh: r[6],
        title: r[7] || r[6],
        org: r[8] ? `${r[8]} · ${r[0]}` : r[0],
        tldr: r[9],
      });
    }

    matched.sort((a, b) => (q ? b.upvotes - a.upvotes : b.date.localeCompare(a.date) || b.upvotes - a.upvotes));
    const display = matched.slice(0, 120);
    const out = $("arch-results");

    if (!display.length) {
      out.innerHTML = `<div class="empty-state">未检索到匹配的归档论文。</div>`;
      return;
    }

    out.innerHTML = `
      <div class="topic-head" style="margin-top:16px;">
        <h2>${state.lang === "en" ? "Matching Papers" : "检索结果"}</h2>
        <span class="topic-meta">${matched.length} ${state.lang === "en" ? "MATCHES" : "条命中"}${matched.length > 120 ? " (展示前 120 条)" : ""}</span>
      </div>
      <div>${display.map((p) => renderPaperRowHtml(p, p.date)).join("")}</div>
    `;
    bindLedgerInteractions(out, display, null);
  }

  /* ========================================================================
     Surveys View & Two-Column Reader
     ======================================================================== */
  async function renderSurveysView() {
    $("pulse-section").hidden = true;
    const box = $("surveys-container");

    if (!state.currentSurvey) {
      const cards = state.manifest.surveys
        .map(
          (s) => `
          <article class="survey-card" data-survey="${esc(s.slug)}" tabindex="0">
            <div>
              <div class="eyebrow">${esc(s.period)}</div>
              <h3>${esc(state.lang === "en" ? s.title_en : s.title_zh)}</h3>
              <p>${esc(s.summary || s.full_title)}</p>
            </div>
            <div class="survey-foot">
              <span>${s.paper_count} ARXIV PAPERS</span>
              <span>${s.section_count} SECTIONS →</span>
            </div>
          </article>`
        )
        .join("");

      box.innerHTML = `
        <div class="archive-head">
          <p class="eyebrow">THEMATIC SURVEYS & TAXONOMIES</p>
          <h1 class="issue-title"><span class="zh">近三月前沿专题综述</span><span class="en">Curated Research Surveys</span></h1>
          <p class="issue-brief"><span class="zh">围绕递归自我改进（RSI）、Agent Harness 演化、长程控制、世界模型与前沿安全整理的系统性分类与证据核查。</span><span class="en">Systematic classifications and evidence audits across Recursive Self-Improvement, Agent Harnesses, World Models, and AI Safety.</span></p>
        </div>
        <div class="survey-grid">${cards}</div>
      `;
      box.querySelectorAll("[data-survey]").forEach((el) => {
        el.addEventListener("click", () => {
          location.hash = `#surveys/${el.dataset.survey}`;
        });
      });
      return;
    }

    const sData = await ensureSurvey(state.currentSurvey);
    const tocHtml = (sData.toc || [])
      .map((item) => `<a href="#surveys/${esc(sData.slug)}" data-jump="${esc(item.id)}" class="lvl-${item.level}">${esc(item.text)}</a>`)
      .join("");

    box.innerHTML = `
      <div class="archive-head" style="display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:14px;">
        <div>
          <p class="eyebrow">${esc(sData.period)} · ${sData.paper_count} REFERENCED PAPERS</p>
          <h1 class="issue-title">${esc(sData.full_title || sData.title_zh)}</h1>
        </div>
        <button type="button" class="util-btn" id="back-surveys">← <span class="zh">返回专题列表</span><span class="en">All Surveys</span></button>
      </div>
      <div class="reader-layout">
        <nav class="reader-toc" aria-label="Survey outline">
          <div class="reader-toc-title">CONTENTS</div>
          ${tocHtml}
        </nav>
        <article class="prose">${sData.html}</article>
      </div>
    `;
    $("back-surveys").addEventListener("click", () => {
      location.hash = "#surveys";
    });
    box.querySelectorAll("[data-jump]").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const target = document.getElementById(link.dataset.jump);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ========================================================================
     Saved Reading List View
     ======================================================================== */
  function renderSavedView() {
    $("pulse-section").hidden = true;
    const items = Object.values(state.saved).sort((a, b) => (b.date || "").localeCompare(a.date || ""));
    const container = $("saved-ledger");
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">暂无待读论文。在任意账本条目右侧点击「☆」即可加入本地阅读清单。</div>`;
      return;
    }
    container.innerHTML = `<div style="margin-top:14px;">${items.map((p) => renderPaperRowHtml(p, p.date || "")).join("")}</div>`;
    bindLedgerInteractions(container, items, null);
  }

  /* ========================================================================
     Slide-Over Perforated Dossier Drawer
     ======================================================================== */
  function openDrawerById(list, arxivId, dateStr) {
    const idx = list.findIndex((x) => x.arxiv_id === arxivId);
    if (idx < 0) return;
    state.drawerList = list;
    state.drawerIdx = idx;
    renderDrawer(dateStr);
  }

  function closeDrawer() {
    $("scrim").hidden = true;
    $("drawer").hidden = true;
    document.body.style.overflow = "";
  }

  function paperToBibtex(p, dateStr) {
    const year = (dateStr || "2026").slice(0, 4);
    const key = `arxiv${(p.arxiv_id || "paper").replace(/\W+/g, "_")}`;
    return `@article{${key},\n  title = {${p.title || p.title_zh}},\n  author = {${(p.authors_preview && p.authors_preview.join(" and ")) || p.submitter || "Authors"}},\n  journal = {arXiv preprint arXiv:${p.arxiv_id}},\n  year = {${year}},\n  url = {https://arxiv.org/abs/${p.arxiv_id}}\n}`;
  }

  function paperToMarkdown(p, dateStr) {
    return `### ${p.title_zh || p.title} (${p.arxiv_id})\n- 日期：${dateStr || ""}\n- 链接：https://arxiv.org/abs/${p.arxiv_id}${p.github_url && p.github_url !== "1" ? ` | Code: ${p.github_url}` : ""}\n- 核心结论：${p.tldr || ""}\n- 方法：${p.method || ""}\n- 结果：${p.result || ""}\n`;
  }

  function renderDrawer(dateStr) {
    const p = state.drawerList[state.drawerIdx];
    if (!p) return;
    const isSaved = Boolean(state.saved[p.arxiv_id]);
    const ideas = [...(p.ideas_and_insights || []), ...(p.new_paper_directions || [])];
    const ghUrl = p.github_url && p.github_url !== "1" ? p.github_url : null;

    const drawer = $("drawer");
    drawer.innerHTML = `
      <div class="drawer-bar">
        <div class="drawer-actions">
          <button type="button" class="step-btn" id="dr-prev" ${state.drawerIdx <= 0 ? "disabled" : ""}>↑ Prev</button>
          <button type="button" class="step-btn" id="dr-next" ${state.drawerIdx >= state.drawerList.length - 1 ? "disabled" : ""}>↓ Next</button>
          <button type="button" class="util-btn" id="dr-save">${isSaved ? "★ 已收藏" : "☆ 加入待读"}</button>
          <button type="button" class="util-btn" id="dr-copy-md">Markdown</button>
          <button type="button" class="util-btn" id="dr-copy-bib">BibTeX</button>
        </div>
        <button type="button" class="util-btn mono" id="dr-close">ESC ✕</button>
      </div>

      <div class="receipt">
        <div class="rec-eyebrow">${esc(topicLabel(p.topic))} · ARXIV ${esc(p.arxiv_id)} ${dateStr ? `· ${esc(dateStr)}` : ""}</div>
        <h2 class="rec-title">${esc(p.title_zh || p.title)}</h2>
        ${p.title && p.title !== p.title_zh ? `<p class="rec-en mono">${esc(p.title)}</p>` : `<div style="height:8px"></div>`}

        <div class="rec-links">
          <a class="rec-link primary" href="https://arxiv.org/pdf/${esc(p.arxiv_id)}" target="_blank" rel="noopener">Read PDF ↗</a>
          <a class="rec-link" href="https://arxiv.org/abs/${esc(p.arxiv_id)}" target="_blank" rel="noopener">arXiv Abs ↗</a>
          <a class="rec-link" href="https://huggingface.co/papers/${esc(p.arxiv_id)}" target="_blank" rel="noopener">HF Page ↗</a>
          ${ghUrl ? `<a class="rec-link" href="${esc(ghUrl)}" target="_blank" rel="noopener" style="border-color:var(--code);color:var(--code)">GitHub Code ↗</a>` : ""}
        </div>

        <div class="rec-kv">
          <div><span>Community Votes</span><b>▲ ${p.upvotes || 0}</b></div>
          <div><span>Signal Rating</span><b>${p.insight_score || 3} / 5</b></div>
          <div><span>Affiliation</span><b>${esc(p.org || "—")}</b></div>
          <div><span>Authors / Submitter</span><b>${p.n_authors ? `${p.n_authors} authors` : esc(p.submitter || "—")}</b></div>
        </div>

        ${p.tldr ? `<div class="rec-tldr">${esc(p.tldr)}</div>` : ""}

        ${p.problem ? `<div class="rec-sec"><h3>研究问题 / Problem</h3><p>${esc(p.problem)}</p></div>` : ""}
        ${p.method ? `<div class="rec-sec"><h3>核心方法 / Method</h3><p>${esc(p.method)}</p></div>` : ""}
        ${p.contribution ? `<div class="rec-sec"><h3>主要贡献 / Contribution</h3><p>${esc(p.contribution)}</p></div>` : ""}
        ${p.result ? `<div class="rec-sec"><h3>定量结果 / Quantitative Result</h3><p>${esc(p.result)}</p></div>` : ""}

        ${p.extra_commentary ? `<div class="rec-note"><strong>编者按：</strong>${esc(p.extra_commentary)}</div>` : ""}

        ${p.plain_explanation ? `<div class="rec-sec"><h3>跨领域直白解释 / Plain Intuition</h3><p>${esc(p.plain_explanation)}</p></div>` : ""}

        ${
          ideas.length
            ? `<div class="rec-sec">
                <h3>延伸研究设想 / Testable Follow-ups</h3>
                <ul>${ideas.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
              </div>`
            : ""
        }
      </div>
    `;

    $("scrim").hidden = false;
    drawer.hidden = false;
    document.body.style.overflow = "hidden";

    $("dr-close").onclick = closeDrawer;
    $("dr-prev").onclick = () => {
      if (state.drawerIdx > 0) {
        state.drawerIdx--;
        renderDrawer(dateStr);
      }
    };
    $("dr-next").onclick = () => {
      if (state.drawerIdx < state.drawerList.length - 1) {
        state.drawerIdx++;
        renderDrawer(dateStr);
      }
    };
    $("dr-save").onclick = () => {
      if (state.saved[p.arxiv_id]) {
        delete state.saved[p.arxiv_id];
      } else {
        state.saved[p.arxiv_id] = { ...p, date: dateStr };
      }
      saveBookmarks();
      renderDrawer(dateStr);
      if (state.view === "daily" && state.dayCache[state.currentDate]) renderDailyLedger(state.dayCache[state.currentDate]);
      if (state.view === "saved") renderSavedView();
    };
    $("dr-copy-md").onclick = async (e) => {
      await navigator.clipboard.writeText(paperToMarkdown(p, dateStr));
      e.target.textContent = "Copied ✓";
      setTimeout(() => (e.target.textContent = "Markdown"), 1200);
    };
    $("dr-copy-bib").onclick = async (e) => {
      await navigator.clipboard.writeText(paperToBibtex(p, dateStr));
      e.target.textContent = "Copied ✓";
      setTimeout(() => (e.target.textContent = "BibTeX"), 1200);
    };
  }

  /* ========================================================================
     Router & Global Event Bindings
     ======================================================================== */
  async function route() {
    const hash = (location.hash || "#daily").slice(1);
    const [seg1, seg2] = hash.split("/");

    if (seg1 === "archive") {
      state.view = "archive";
    } else if (seg1 === "surveys") {
      state.view = "surveys";
      state.currentSurvey = seg2 || null;
    } else if (seg1 === "saved") {
      state.view = "saved";
    } else {
      state.view = "daily";
      const validDates = new Set(state.manifest.days.map((d) => d.date));
      state.currentDate = validDates.has(seg2) ? seg2 : state.manifest.stats.latest_date;
    }

    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.setAttribute("aria-selected", String(tab.dataset.nav === state.view));
    });
    ["daily", "archive", "surveys", "saved"].forEach((v) => {
      $("view-" + v).hidden = v !== state.view;
    });

    if (state.view === "daily") await renderDailyView();
    else if (state.view === "archive") await renderArchiveView();
    else if (state.view === "surveys") await renderSurveysView();
    else if (state.view === "saved") renderSavedView();
  }

  async function bootstrap() {
    initTheme();
    applyLang();
    applyDensityLabel();

    state.manifest = await fetchJson("data/manifest.json");
    state.manifest.topics.forEach((t) => (state.topicMap[t.key] = t));

    const st = state.manifest.stats;
    $("edition-span").textContent = `${(st.earliest_date || "").slice(0, 7).replace("-", ".")} — ${(st.latest_date || "").slice(0, 7).replace("-", ".")}`;
    $("nav-cnt-daily").textContent = st.issue_count;
    $("nav-cnt-papers").textContent = st.paper_count;
    $("nav-cnt-surveys").textContent = st.survey_count;
    saveBookmarks();

    if (state.manifest.site?.repository_url) {
      $("gh-link").href = state.manifest.site.repository_url;
      $("footer-gh").href = state.manifest.site.repository_url;
    }

    // Navigation clicks
    document.querySelectorAll(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        location.hash = `#${btn.dataset.nav}`;
      });
    });

    $("btn-lang").addEventListener("click", () => {
      state.lang = state.lang === "zh" ? "en" : "zh";
      applyLang();
      route();
    });

    $("btn-density").addEventListener("click", () => {
      state.density = state.density === "compact" ? "expanded" : "compact";
      applyDensityLabel();
      route();
    });

    $("date-select").addEventListener("change", (e) => {
      location.hash = `#daily/${e.target.value}`;
    });
    $("btn-prev-day").addEventListener("click", () => {
      const idx = state.manifest.days.findIndex((d) => d.date === state.currentDate);
      if (idx >= 0 && idx < state.manifest.days.length - 1) {
        location.hash = `#daily/${state.manifest.days[idx + 1].date}`;
      }
    });
    $("btn-next-day").addEventListener("click", () => {
      const idx = state.manifest.days.findIndex((d) => d.date === state.currentDate);
      if (idx > 0) {
        location.hash = `#daily/${state.manifest.days[idx - 1].date}`;
      }
    });

    // Daily filter bindings
    $("daily-q").addEventListener("input", (e) => {
      state.dailyFilter.q = e.target.value;
      if (state.dayCache[state.currentDate]) renderDailyLedger(state.dayCache[state.currentDate]);
    });
    const bindToggle = (id, filterObj, key, onUpdate) => {
      $(id).addEventListener("click", (e) => {
        filterObj[key] = !filterObj[key];
        e.currentTarget.setAttribute("aria-pressed", String(filterObj[key]));
        onUpdate();
      });
    };
    bindToggle("tog-signal", state.dailyFilter, "signal", () => renderDailyLedger(state.dayCache[state.currentDate]));
    bindToggle("tog-code", state.dailyFilter, "code", () => renderDailyLedger(state.dayCache[state.currentDate]));
    bindToggle("tog-focus", state.dailyFilter, "focus", () => renderDailyLedger(state.dayCache[state.currentDate]));

    document.querySelectorAll("[data-sort]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.dailyFilter.sort = btn.dataset.sort;
        document.querySelectorAll("[data-sort]").forEach((b) =>
          b.setAttribute("aria-pressed", String(b === btn))
        );
        if (state.dayCache[state.currentDate]) renderDailyLedger(state.dayCache[state.currentDate]);
      });
    });

    // Archive filter bindings
    $("arch-q").addEventListener("input", async (e) => {
      state.archFilter.q = e.target.value;
      renderArchiveSearchResults(await ensureSearchIndex());
    });
    bindToggle("arch-tog-signal", state.archFilter, "signal", async () =>
      renderArchiveSearchResults(await ensureSearchIndex())
    );
    bindToggle("arch-tog-code", state.archFilter, "code", async () =>
      renderArchiveSearchResults(await ensureSearchIndex())
    );

    // Saved export buttons
    $("btn-export-md").addEventListener("click", async (e) => {
      const items = Object.values(state.saved);
      const md = items.map((p) => paperToMarkdown(p, p.date)).join("\n");
      await navigator.clipboard.writeText(md || "Empty");
      const orig = e.currentTarget.textContent;
      e.currentTarget.textContent = "Copied ✓";
      setTimeout(() => (e.currentTarget.textContent = orig), 1400);
    });
    $("btn-export-bib").addEventListener("click", async (e) => {
      const items = Object.values(state.saved);
      const bib = items.map((p) => paperToBibtex(p, p.date)).join("\n\n");
      await navigator.clipboard.writeText(bib || "");
      const orig = e.currentTarget.textContent;
      e.currentTarget.textContent = "Copied ✓";
      setTimeout(() => (e.currentTarget.textContent = orig), 1400);
    });

    $("scrim").addEventListener("click", closeDrawer);

    // Global keyboard shortcuts: `/` search, `Esc` close drawer, `J`/`K` step papers in drawer
    document.addEventListener("keydown", (e) => {
      const tag = (e.target?.tagName || "").toLowerCase();
      const inInput = tag === "input" || tag === "textarea" || tag === "select";
      if (e.key === "/" && !inInput) {
        e.preventDefault();
        const box = state.view === "archive" ? $("arch-q") : $("daily-q");
        if (box) box.focus();
      } else if (e.key === "Escape" && !$("drawer").hidden) {
        closeDrawer();
      } else if (!$("drawer").hidden && !inInput) {
        if (e.key === "j" || e.key === "ArrowDown") {
          if (state.drawerIdx < state.drawerList.length - 1) {
            e.preventDefault();
            state.drawerIdx++;
            renderDrawer(state.currentDate);
          }
        } else if (e.key === "k" || e.key === "ArrowUp") {
          if (state.drawerIdx > 0) {
            e.preventDefault();
            state.drawerIdx--;
            renderDrawer(state.currentDate);
          }
        }
      }
    });

    window.addEventListener("hashchange", route);
    await route();
  }

  bootstrap().catch((err) => {
    console.error(err);
    $("main-root").innerHTML = `<div class="wrap empty-state">Failed to initialize ledger: ${esc(err.message)}</div>`;
  });
})();
