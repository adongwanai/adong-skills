const buttons = document.querySelectorAll("[data-filter]");
const items = document.querySelectorAll(".timeline-card[data-category]");
const detailItems = document.querySelectorAll(".timeline-card[data-detail-id]");
const detailData = JSON.parse(document.getElementById("portfolio-details")?.textContent || "{}");
const modal = document.querySelector("[data-detail-modal]");
const pageRegions = document.querySelectorAll("main, footer");
let lastFocused = null;

for (const button of buttons) {
  button.addEventListener("click", () => {
    const filter = button.dataset.filter;
    const categories = new Set((button.dataset.categories || "").split(" ").filter(Boolean));
    for (const candidate of buttons) {
      const active = candidate === button;
      candidate.classList.toggle("active", active);
      candidate.setAttribute("aria-pressed", String(active));
    }
    for (const item of items) {
      item.hidden = filter !== "all" && !categories.has(item.dataset.category);
      if (!item.hidden) item.classList.add("is-visible");
    }
  });
}

const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    }
  }
}, { threshold: 0.12 });

for (const item of items) observer.observe(item);
for (const metric of document.querySelectorAll(".metric-card")) metric.classList.add("float-in");

function clear(node) {
  node.replaceChildren();
}

function text(selector, value) {
  const node = modal.querySelector(selector);
  node.textContent = value || "";
  return node;
}

function renderListSection(section) {
  const wrap = document.createElement("section");
  wrap.className = "detail-section";
  const title = document.createElement("h3");
  title.textContent = section.title;
  wrap.append(title);
  const list = document.createElement("ul");
  for (const item of section.items || []) {
    const li = document.createElement("li");
    li.textContent = item;
    list.append(li);
  }
  wrap.append(list);
  return wrap;
}

function openDetail(id) {
  const detail = detailData[id];
  if (!detail) return;
  lastFocused = document.activeElement;
  text("[data-detail-category]", detail.category);
  text("[data-detail-title]", detail.title);
  text("[data-detail-meta]", [detail.kicker, detail.organization, detail.date].filter(Boolean).join(" · "));
  text("[data-detail-summary]", detail.summary);
  text("[data-detail-abstract]", detail.abstract);

  const visualWrap = modal.querySelector("[data-detail-visual-wrap]");
  const visual = modal.querySelector("[data-detail-visual]");
  const caption = modal.querySelector("[data-detail-visual-caption]");
  if (detail.visual) {
    visual.src = detail.visual.path;
    visual.alt = detail.visual.alt || "";
    caption.textContent = detail.visual_caption || detail.visual.alt || "";
    visualWrap.hidden = false;
  } else {
    visual.removeAttribute("src");
    visualWrap.hidden = true;
  }

  const metricWrap = modal.querySelector("[data-detail-metrics-wrap]");
  const metricList = modal.querySelector("[data-detail-metrics]");
  clear(metricList);
  for (const metric of detail.metrics || []) {
    const card = document.createElement("div");
    const value = document.createElement("strong");
    const label = document.createElement("span");
    value.textContent = metric.value;
    label.textContent = metric.label;
    card.append(value, label);
    metricList.append(card);
  }
  metricWrap.hidden = !metricList.children.length;

  const sections = modal.querySelector("[data-detail-sections]");
  clear(sections);
  for (const section of detail.sections || []) sections.append(renderListSection(section));

  const starWrap = modal.querySelector("[data-detail-star-wrap]");
  const starGrid = modal.querySelector("[data-detail-star]");
  clear(starGrid);
  for (const [label, value] of Object.entries(detail.star || {})) {
    const card = document.createElement("div");
    const key = document.createElement("strong");
    const body = document.createElement("p");
    key.textContent = label;
    body.textContent = value;
    card.append(key, body);
    starGrid.append(card);
  }
  starWrap.hidden = !starGrid.children.length;

  const tradeoffWrap = modal.querySelector("[data-detail-tradeoff-wrap]");
  text("[data-detail-tradeoff]", detail.tradeoff);
  tradeoffWrap.hidden = !detail.tradeoff;

  const tags = modal.querySelector("[data-detail-tags]");
  clear(tags);
  for (const tag of detail.tags || []) {
    const node = document.createElement("span");
    node.textContent = tag;
    tags.append(node);
  }

  const links = modal.querySelector("[data-detail-links]");
  clear(links);
  for (const link of detail.links || []) {
    const anchor = document.createElement("a");
    anchor.href = link.url;
    anchor.textContent = link.label;
    links.append(anchor);
  }

  modal.hidden = false;
  modal.setAttribute("aria-hidden", "false");
  for (const region of pageRegions) region.inert = true;
  document.body.classList.add("modal-open");
  modal.querySelector(".detail-close").focus();
}

function closeDetail() {
  if (modal.hidden) return;
  modal.hidden = true;
  modal.setAttribute("aria-hidden", "true");
  for (const region of pageRegions) region.inert = false;
  document.body.classList.remove("modal-open");
  if (lastFocused) lastFocused.focus();
}

for (const item of detailItems) {
  item.addEventListener("click", (event) => {
    if (event.target.closest("a")) return;
    openDetail(item.dataset.detailId);
  });
  item.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDetail(item.dataset.detailId);
    }
  });
}

for (const closer of document.querySelectorAll("[data-detail-close]")) {
  closer.addEventListener("click", closeDetail);
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Tab" && !modal.hidden) {
    const focusable = [...modal.querySelectorAll('button:not([disabled]), a[href]')];
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  if (event.key === "Escape") closeDetail();
});
