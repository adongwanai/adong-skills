const filters = [...document.querySelectorAll("[data-status-filter]")];
const jobs = [...document.querySelectorAll("[data-job-status]")];
const empty = document.querySelector("[data-empty-filter]");

for (const button of filters) {
  button.addEventListener("click", () => {
    for (const item of filters) item.setAttribute("aria-pressed", String(item === button));
    const selected = button.dataset.statusFilter;
    let visible = 0;
    for (const job of jobs) {
      const show = selected === "all" || job.dataset.jobStatus === selected;
      job.hidden = !show;
      if (show) visible += 1;
    }
    empty.hidden = visible !== 0;
  });
}
