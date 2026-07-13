const COPY = {
  tc: {
    direction: "往",
    due: "即將到站",
    minutes: "分鐘",
    noService: "暫未有預計到站時間",
    updated: "更新",
    stale: "較早資料",
    stop: "站",
  },
  en: {
    direction: "To",
    due: "Due",
    minutes: "min",
    noService: "No arrival estimate available",
    updated: "Updated",
    stale: "Earlier data",
    stop: "Stop",
  },
  sc: {
    direction: "往",
    due: "即将到站",
    minutes: "分钟",
    noService: "暂无预计到站时间",
    updated: "更新",
    stale: "较早资料",
    stop: "站",
  },
};

const LOCALES = { tc: "zh-HK", en: "en-HK", sc: "zh-CN" };

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]));
}

function languageValue(record, base, language) {
  return record?.[`${base}_${language}`]
    || record?.[`${base}_tc`]
    || record?.[`${base}_en`]
    || "";
}

function minutesUntil(iso) {
  if (!iso) return null;
  const timestamp = new Date(iso).getTime();
  if (!Number.isFinite(timestamp)) return null;
  return Math.max(0, Math.ceil((timestamp - Date.now()) / 60000));
}

function formatTime(iso, language) {
  if (!iso) return "-";
  const timestamp = new Date(iso);
  if (!Number.isFinite(timestamp.getTime())) return "-";
  return new Intl.DateTimeFormat(LOCALES[language], {
    timeZone: "Asia/Hong_Kong",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(timestamp);
}

function formatUpdated(iso, language) {
  if (!iso) return "";
  const timestamp = new Date(iso);
  if (!Number.isFinite(timestamp.getTime())) return "";
  return new Intl.DateTimeFormat(LOCALES[language], {
    timeZone: "Asia/Hong_Kong",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(timestamp);
}

function styles() {
  return `<style>
    :host { display: block; width: 100%; height: 100%; container-type: size; }
    * { box-sizing: border-box; }
    .w { letter-spacing: 0; }
    .bus-route {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 2.7em;
      min-height: 1.8em;
      padding: 0 var(--space-2);
      border-radius: min(var(--radius-1, 6px), 6px);
      background: var(--accent-4);
      color: var(--on-accent);
      font-weight: var(--fw-black);
      font-variant-numeric: tabular-nums;
      line-height: 1;
      letter-spacing: 0;
      flex: 0 0 auto;
    }
    .bus-title-icon { color: var(--accent-4); flex: 0 0 auto; }
    .bus-destination { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .bus-direction {
      display: inline-flex;
      align-items: center;
      gap: var(--space-1);
      color: var(--text-muted);
      font-size: var(--fs-caption);
      font-weight: var(--fw-bold);
      white-space: nowrap;
    }
    .bus-body {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      gap: var(--space-3);
      min-height: 0;
    }
    .bus-stop {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
      border-radius: min(var(--radius-1, 6px), 6px);
      background: var(--surface-sunken);
      min-width: 0;
    }
    .bus-stop i { color: var(--accent-5); font-size: var(--icon-md); }
    .bus-stop-copy { min-width: 0; }
    .bus-stop-name {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text-primary);
      font-weight: var(--fw-bold);
      line-height: 1.15;
    }
    .bus-stop-meta {
      display: block;
      margin-top: 2px;
      color: var(--text-muted);
      font-size: var(--fs-caption);
      font-variant-numeric: tabular-nums;
    }
    .eta-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: var(--space-3);
      min-width: 0;
      min-height: 0;
    }
    .eta-item {
      display: grid;
      grid-template-rows: auto auto auto;
      align-content: center;
      gap: var(--space-1);
      min-width: 0;
      min-height: 0;
      padding: var(--space-3);
      border-radius: min(var(--radius-2, 8px), 8px);
      background: var(--surface-sunken);
    }
    .eta-item.is-next {
      background: var(--accent-4-soft);
      box-shadow: inset max(var(--edge-weight, 3px), 3px) 0 0 var(--accent-4);
    }
    .eta-primary {
      display: flex;
      align-items: baseline;
      gap: var(--space-1);
      min-width: 0;
      color: var(--text-primary);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .eta-item.is-next .eta-primary { color: var(--accent-4); }
    .eta-minutes {
      font-size: var(--eta-size, 3rem);
      font-weight: var(--fw-black);
      line-height: 0.95;
      letter-spacing: 0;
    }
    .eta-unit {
      color: var(--text-secondary);
      font-size: var(--fs-caption);
      font-weight: var(--fw-bold);
      text-transform: var(--label-transform, uppercase);
    }
    .eta-clock {
      color: var(--text-secondary);
      font-size: var(--fs-body);
      font-weight: var(--fw-bold);
      font-variant-numeric: tabular-nums;
    }
    .eta-remark {
      align-self: start;
      margin-top: var(--space-1);
      overflow: hidden;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      color: var(--text-muted);
      font-size: var(--fs-caption);
      line-height: 1.2;
    }
    .bus-updated {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--space-1);
      color: var(--text-muted);
      font-size: var(--fs-caption);
      font-variant-numeric: tabular-nums;
    }
    .bus-updated.is-stale { color: var(--accent-2); font-weight: var(--fw-bold); }
    .bus-empty {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 0;
      padding: var(--space-4);
      border-radius: min(var(--radius-2, 8px), 8px);
      background: var(--surface-sunken);
      color: var(--text-muted);
      font-weight: var(--fw-semi);
      text-align: center;
    }
    .size-xs { --eta-size: 2rem; }
    .size-sm { --eta-size: 2.25rem; }
    .size-md { --eta-size: 3.15rem; }
    .size-lg { --eta-size: 4.5rem; }
    .size-xs .bus-title-icon,
    .size-xs .bus-direction,
    .size-xs .bus-stop-meta,
    .size-xs .bus-updated,
    .size-xs .eta-clock,
    .size-xs .eta-remark,
    .size-xs .eta-item:nth-child(n + 2) { display: none; }
    .size-xs .bus-body { grid-template-rows: auto minmax(0, 1fr); gap: var(--space-2); }
    .size-xs .eta-grid { grid-template-columns: 1fr; }
    .size-xs .eta-item { padding: var(--space-2) var(--space-3); }
    .size-xs .bus-stop { padding: var(--space-1) var(--space-2); }
    .size-sm .eta-item:nth-child(n + 3) { display: none; }
    .size-sm .eta-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2); }
    .size-sm .eta-item { padding: var(--space-2); }
    .size-sm .eta-remark { -webkit-line-clamp: 1; }
    @container (max-width: 250px) {
      .bus-title-icon, .bus-direction, .bus-stop-meta, .bus-updated,
      .eta-clock, .eta-remark, .eta-item:nth-child(n + 2) { display: none; }
      .bus-body { grid-template-rows: auto minmax(0, 1fr); gap: var(--space-2); }
      .eta-grid { grid-template-columns: 1fr; }
    }
  </style>`;
}

function errorMarkup(message, size) {
  return `
    <link rel="stylesheet" href="/static/style/spectra-widgets.css">
    ${styles()}
    <div class="w size-${escapeHtml(size)}" data-widget="hk_bus_arrival">
      <div class="w-title">
        <i class="ph-bold ph-warning-circle" style="color:var(--accent-1)"></i>
        <h3>Hong Kong Bus</h3>
      </div>
      <div class="w-body list-body bus-empty">${escapeHtml(message)}</div>
    </div>`;
}

export default function render(shadow, ctx) {
  const data = ctx?.data ?? {};
  const options = ctx?.cell?.options ?? {};
  const size = ["xs", "sm", "md", "lg"].includes(ctx?.cell?.size)
    ? ctx.cell.size
    : "md";
  const language = ["tc", "en", "sc"].includes(options.language)
    ? options.language
    : "tc";
  const copy = COPY[language];

  if (data.error) {
    shadow.innerHTML = errorMarkup(data.error, size);
    return;
  }

  const journey = data.journey ?? {};
  const arrivals = Array.isArray(data.arrivals) ? data.arrivals : [];
  const stopName = languageValue(journey, "stop_name", language) || "-";
  const destination = languageValue(arrivals[0], "dest", language)
    || languageValue(journey, "dest", language)
    || "-";
  const origin = languageValue(journey, "orig", language);
  const showRemarks = options.show_remarks !== false;

  const arrivalMarkup = arrivals.length
    ? arrivals.map((arrival, index) => {
      const minutes = minutesUntil(arrival.eta);
      const minutesText = minutes == null ? "-" : minutes === 0 ? copy.due : String(minutes);
      const unit = minutes == null || minutes === 0 ? "" : copy.minutes;
      const remark = showRemarks ? languageValue(arrival, "remark", language) : "";
      return `
        <div class="eta-item${index === 0 ? " is-next" : ""}">
          <div class="eta-primary">
            <span class="eta-minutes">${escapeHtml(minutesText)}</span>
            ${unit ? `<span class="eta-unit">${escapeHtml(unit)}</span>` : ""}
          </div>
          <span class="eta-clock">${escapeHtml(formatTime(arrival.eta, language))}</span>
          ${remark ? `<span class="eta-remark">${escapeHtml(remark)}</span>` : ""}
        </div>`;
    }).join("")
    : `<div class="bus-empty">${escapeHtml(copy.noService)}</div>`;

  const updatedTime = formatUpdated(data.data_timestamp || data.generated_timestamp, language);
  const staleClass = data.stale ? " is-stale" : "";
  const updatedLabel = data.stale ? copy.stale : copy.updated;

  shadow.innerHTML = `
    <link rel="stylesheet" href="/static/style/spectra-widgets.css">
    ${styles()}
    <div class="w size-${escapeHtml(size)}" data-widget="hk_bus_arrival">
      <div class="w-title">
        <i class="ph-bold ph-bus bus-title-icon"></i>
        <span class="bus-route">${escapeHtml(journey.route || "-")}</span>
        <h3 class="bus-destination">${escapeHtml(destination)}</h3>
        <span class="w-title-meta bus-direction">
          ${escapeHtml(copy.direction)} <i class="ph-bold ph-arrow-right" aria-hidden="true"></i>
        </span>
      </div>
      <div class="w-body list-body bus-body">
        <div class="bus-stop">
          <i class="ph-bold ph-map-pin" aria-hidden="true"></i>
          <div class="bus-stop-copy">
            <span class="bus-stop-name">${escapeHtml(stopName)}</span>
            <span class="bus-stop-meta">${escapeHtml(copy.stop)} ${escapeHtml(journey.seq || "-")}${origin ? ` · ${escapeHtml(origin)}` : ""}</span>
          </div>
        </div>
        <div class="eta-grid">${arrivalMarkup}</div>
        ${updatedTime ? `<div class="bus-updated${staleClass}"><i class="ph-bold ${data.stale ? "ph-warning" : "ph-clock"}" aria-hidden="true"></i>${escapeHtml(updatedLabel)} ${escapeHtml(updatedTime)}</div>` : ""}
      </div>
    </div>`;
}
