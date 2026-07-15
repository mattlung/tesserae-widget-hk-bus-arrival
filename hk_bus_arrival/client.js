const COPY = {
  tc: {
    noService: "暫未有預計到站時間",
    source: "九巴到站時間",
    stale: "較早資料",
    to: "往",
    moreRoutes: (count) => `另外 ${count} 條路線`,
  },
  en: {
    noService: "No arrival estimate available",
    source: "KMB arrival times",
    stale: "Earlier data",
    to: "To",
    moreRoutes: (count) => `${count} more route${count === 1 ? "" : "s"}`,
  },
  sc: {
    noService: "暂无预计到站时间",
    source: "九巴到站时间",
    stale: "较早资料",
    to: "往",
    moreRoutes: (count) => `另外 ${count} 条路线`,
  },
};

const LOCALES = { tc: "zh-HK", en: "en-HK", sc: "zh-CN" };
const ROUTE_LIMITS = { xs: 3, sm: 3, md: 5, lg: 8 };
const ETA_LIMITS = { xs: 1, sm: 2, md: 3, lg: 3 };
const FONT_SCALES = { small: 0.9, normal: 1, large: 1.2, extra_large: 1.4 };

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

function styles(fontScale = 1) {
  return `<style>
    :host { display: block; width: 100%; height: 100%; container-type: size; }
    * { box-sizing: border-box; }
    .w { letter-spacing: 0; }
    .bus-board {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      gap: 0;
      width: 100%;
      height: 100%;
      padding: 0;
      overflow: hidden;
      background: var(--surface);
      color: var(--text-primary);
      font-size: ${fontScale * 100}%;
    }
    .board-head {
      min-width: 0;
      padding: 14px 18px 12px;
      border-bottom: 1px solid var(--text-muted);
    }
    .brand-row {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      min-width: 0;
    }
    .brand-title {
      flex: 1 1 auto;
      min-width: 0;
      margin: 0;
      overflow: hidden;
      color: var(--text-primary);
      font-size: 1.45em;
      font-weight: var(--fw-black);
      line-height: 1.05;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .brand-icon {
      flex: 0 0 auto;
      color: var(--text-primary);
      font-size: 1.75em;
    }
    .route-list {
      display: grid;
      grid-template-rows: repeat(var(--row-count), minmax(0, 1fr));
      min-height: 0;
      overflow: hidden;
    }
    .route-row {
      display: grid;
      grid-template-columns: minmax(4.5rem, 0.7fr) minmax(8rem, 1.8fr) repeat(var(--eta-count), minmax(4.6rem, 0.75fr));
      align-items: center;
      min-width: 0;
      min-height: 0;
      padding: 5px 18px;
      border-bottom: 1px solid var(--text-muted);
    }
    .route-code {
      min-width: 0;
      overflow: hidden;
      padding-right: var(--space-3);
      color: var(--text-primary);
      font-size: 2em;
      font-weight: var(--fw-black);
      font-variant-numeric: tabular-nums;
      line-height: 1;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .route-destination {
      min-width: 0;
      padding-right: var(--space-3);
    }
    .stop-name,
    .destination-name,
    .destination-note {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .journey-label {
      display: block;
      min-width: 0;
    }
    .stop-name {
      color: var(--text-primary);
      font-size: 1.15em;
      font-weight: var(--fw-black);
      line-height: 1.05;
    }
    .destination-name {
      display: flex;
      gap: 0.35em;
      margin-top: 5px;
      min-width: 0;
      color: var(--text-secondary);
      font-size: 0.8em;
      font-weight: var(--fw-semi);
      line-height: 1.1;
    }
    .destination-prefix { flex: 0 0 auto; }
    .destination-text {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .destination-note {
      margin-top: 3px;
      color: var(--text-muted);
      font-size: 0.78em;
      line-height: 1.15;
    }
    .eta-slot {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      justify-content: center;
      min-width: 0;
      padding-left: var(--space-2);
      color: var(--text-primary);
      font-variant-numeric: tabular-nums;
      text-align: right;
    }
    .eta-time {
      max-width: 100%;
      overflow: hidden;
      font-size: 1.05em;
      line-height: 1;
      text-overflow: clip;
      white-space: nowrap;
    }
    .eta-slot.is-next .eta-time {
      font-size: 1.55em;
      font-weight: var(--fw-black);
    }
    .eta-remark {
      display: block;
      max-width: 100%;
      margin-top: 5px;
      overflow: hidden;
      color: var(--text-muted);
      font-size: 0.66em;
      line-height: 1.1;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .route-notice {
      display: flex;
      align-items: center;
      grid-column: 3 / -1;
      gap: var(--space-2);
      min-width: 0;
      color: var(--text-secondary);
      font-size: 0.78em;
      line-height: 1.2;
    }
    .route-notice i { flex: 0 0 auto; font-size: 1.282em; }
    .route-notice span {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .more-row {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 0;
      padding: var(--space-2) var(--space-3);
      border-bottom: 1px solid var(--text-muted);
      color: var(--text-muted);
      font-size: 0.78em;
      font-weight: var(--fw-bold);
    }
    .board-footer {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      min-width: 0;
      padding: 9px 18px;
    }
    .kmb-mark {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--text-primary);
      color: var(--surface);
      font-size: 0.58em;
      font-weight: var(--fw-black);
      line-height: 1;
    }
    .footer-label {
      min-width: 0;
      overflow: hidden;
      color: var(--text-secondary);
      font-size: 0.78em;
      font-weight: var(--fw-semi);
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .footer-time {
      margin-left: auto;
      color: var(--text-primary);
      font-size: 1em;
      font-weight: var(--fw-bold);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .bus-board.is-stale .footer-label { color: var(--accent-2); }
    .board-error {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 0;
      padding: var(--space-4);
      color: var(--text-secondary);
      font-size: 1em;
      font-weight: var(--fw-semi);
      text-align: center;
    }

    .size-xs .board-head { padding: 8px 9px 7px; }
    .size-xs .brand-row { gap: 5px; }
    .size-xs .brand-title { font-size: 0.82em; }
    .size-xs .brand-icon { font-size: 1em; }
    .size-xs .route-row {
      grid-template-columns: minmax(2.7rem, 0.55fr) minmax(0, 1.25fr) repeat(var(--eta-count), minmax(3.4rem, 0.85fr));
      padding: 3px 9px;
    }
    .size-xs .route-code { padding-right: 5px; font-size: 1.15em; }
    .size-xs .route-destination { padding-right: 5px; }
    .size-xs .stop-name { font-size: 0.62em; }
    .size-xs .destination-name { margin-top: 2px; font-size: 0.48em; }
    .size-xs .destination-note { display: none; }
    .size-xs .eta-slot { padding-left: 3px; }
    .size-xs .eta-slot.is-next .eta-time { font-size: 0.86em; }
    .size-xs .route-notice { grid-column: 3; gap: 3px; font-size: 0.55em; }
    .size-xs .route-notice i { display: none; }
    .size-xs .route-row.has-notice .route-destination { display: none; }
    .size-xs .route-row.has-notice .route-notice { grid-column: 2 / -1; }
    .size-xs .board-footer { padding: 5px 9px; }
    .size-xs .more-row { font-size: 0.62em; }
    .size-xs .board-error { font-size: 0.76em; }
    .size-xs .kmb-mark { width: 20px; height: 20px; font-size: 0.43em; }
    .size-xs .footer-label { display: none; }
    .size-xs .footer-time { font-size: 0.68em; }

    .size-sm .board-head { padding: 10px 12px 8px; }
    .size-sm .brand-title { font-size: 1em; }
    .size-sm .brand-icon { font-size: 1.25em; }
    .size-sm .route-row {
      grid-template-columns: minmax(3.4rem, 0.65fr) minmax(6rem, 1.55fr) repeat(var(--eta-count), minmax(4.3rem, 0.75fr));
      padding: 4px 12px;
    }
    .size-sm .route-code { padding-right: 7px; font-size: 1.4em; }
    .size-sm .route-destination { padding-right: 7px; }
    .size-sm .stop-name { font-size: 0.76em; }
    .size-sm .destination-name { margin-top: 2px; font-size: 0.58em; }
    .size-sm .destination-note { margin-top: 2px; font-size: 0.56em; }
    .size-sm .eta-slot { padding-left: 5px; }
    .size-sm .eta-time { font-size: 0.75em; }
    .size-sm .eta-slot.is-next .eta-time { font-size: 1em; }
    .size-sm .eta-remark { margin-top: 3px; font-size: 0.54em; }
    .size-sm .route-notice { grid-column: 3 / -1; font-size: 0.65em; }
    .size-sm .route-notice i { font-size: 1.538em; }
    .size-sm .more-row { font-size: 0.66em; }
    .size-sm .board-error { font-size: 0.82em; }
    .size-sm .board-footer { padding: 6px 12px; }
    .size-sm .kmb-mark { width: 23px; height: 23px; font-size: 0.48em; }
    .size-sm .footer-label { font-size: 0.65em; }
    .size-sm .footer-time { font-size: 0.78em; }
    .size-sm[data-eta-count="1"] .route-row {
      grid-template-columns: minmax(4.25rem, 0.75fr) minmax(0, 1.5fr) minmax(4.7rem, 0.8fr);
    }

    .size-lg .board-head { padding: 28px 32px 23px; }
    .size-lg .brand-row { gap: 18px; }
    .size-lg .brand-title { font-size: 2.65em; }
    .size-lg .brand-icon { font-size: 3em; }
    .size-lg .route-row {
      grid-template-columns: minmax(10.5rem, 0.75fr) minmax(16rem, 1.65fr) repeat(var(--eta-count), minmax(7.5rem, 0.7fr));
      padding: 8px 32px;
    }
    .size-lg .route-code { padding-right: 22px; font-size: 3.2em; }
    .size-lg .route-destination { padding-right: 22px; }
    .size-lg .stop-name { font-size: 1.65em; }
    .size-lg .destination-name { margin-top: 8px; font-size: 1.1em; }
    .size-lg .destination-note { margin-top: 7px; font-size: 0.85em; }
    .size-lg .eta-slot { padding-left: 15px; }
    .size-lg .eta-time { font-size: 1.5em; }
    .size-lg .eta-slot.is-next .eta-time { font-size: 2.2em; }
    .size-lg .eta-remark { margin-top: 8px; font-size: 0.82em; }
    .size-lg .route-notice { gap: 10px; font-size: 1em; }
    .size-lg .route-notice i { font-size: 1.35em; }
    .size-lg .more-row { font-size: 1.05em; }
    .size-lg .board-error { font-size: 1.35em; }
    .size-lg .board-footer { gap: 14px; padding: 16px 32px; }
    .size-lg .kmb-mark { width: 45px; height: 45px; font-size: 0.88em; }
    .size-lg .footer-label { font-size: 1.1em; }
    .size-lg .footer-time { font-size: 1.5em; }

    .size-md[data-font-size="large"] .route-row {
      grid-template-columns: minmax(6rem, 0.75fr) minmax(8rem, 1.2fr) repeat(var(--eta-count), minmax(5.6rem, 0.8fr));
    }
    .size-md[data-font-size="extra_large"] .route-row {
      grid-template-columns: minmax(7rem, 0.8fr) minmax(8rem, 1fr) repeat(var(--eta-count), minmax(6.5rem, 0.85fr));
    }
    .size-xs[data-font-size="extra_large"] .route-row {
      grid-template-columns: minmax(2.7rem, 0.55fr) minmax(0, 1fr) repeat(var(--eta-count), minmax(3.9rem, 0.95fr));
    }
    .size-lg[data-font-size="extra_large"] .route-row {
      grid-template-columns: minmax(14rem, 0.9fr) minmax(14rem, 1.5fr) repeat(var(--eta-count), minmax(9.5rem, 0.7fr));
    }
  </style>`;
}

function errorMarkup(message, size, fontSize, fontScale) {
  return `
    <link rel="stylesheet" href="/static/style/spectra-widgets.css">
    ${styles(fontScale)}
    <div class="w size-${escapeHtml(size)} bus-board" data-widget="hk_bus_arrival" data-font-size="${escapeHtml(fontSize)}">
      <header class="board-head">
        <div class="brand-row">
          <h3 class="brand-title">KMB Bus Arrivals</h3>
          <i class="ph-bold ph-bus brand-icon" aria-hidden="true"></i>
        </div>
      </header>
      <div class="board-error">${escapeHtml(message)}</div>
    </div>`;
}

function routeMarkup(routeData, language, copy, showRemarks, etaCount) {
  const journey = routeData?.journey ?? {};
  const arrivals = Array.isArray(routeData?.arrivals) ? routeData.arrivals : [];
  const timedArrivals = arrivals.filter((arrival) => arrival?.eta).slice(0, etaCount);
  const noTimeArrival = arrivals.find((arrival) => !arrival?.eta);
  const destination = languageValue(arrivals[0], "dest", language)
    || languageValue(journey, "dest", language)
    || "-";
  const stopName = languageValue(journey, "stop_name", language) || "-";
  const serviceNote = showRemarks
    ? languageValue(noTimeArrival, "remark", language)
    : "";
  const destinationNote = timedArrivals.length ? serviceNote : "";
  const journeyLabel = `
    <span class="journey-label">
      <strong class="stop-name">${escapeHtml(stopName)}</strong>
      <span class="destination-name">
        <span class="destination-prefix">${escapeHtml(copy.to)}</span>
        <span class="destination-text">${escapeHtml(destination)}</span>
      </span>
    </span>`;

  if (!timedArrivals.length) {
    const notice = routeData?.error || serviceNote || copy.noService;
    return `
      <div class="route-row has-notice" role="listitem">
        <span class="route-code">${escapeHtml(journey.route || "-")}</span>
        <span class="route-destination">
          ${journeyLabel}
          ${destinationNote ? `<small class="destination-note">${escapeHtml(destinationNote)}</small>` : ""}
        </span>
        <span class="route-notice">
          <i class="ph-bold ph-info" aria-hidden="true"></i>
          <span>${escapeHtml(notice)}</span>
        </span>
      </div>`;
  }

  const etaSlots = Array.from({ length: etaCount }, (_, index) => {
    const arrival = timedArrivals[index];
    if (!arrival) return '<span class="eta-slot is-empty" aria-hidden="true"></span>';
    const remark = showRemarks ? languageValue(arrival, "remark", language) : "";
    return `
      <span class="eta-slot${index === 0 ? " is-next" : ""}">
        <time class="eta-time" datetime="${escapeHtml(arrival.eta)}">${escapeHtml(formatTime(arrival.eta, language))}</time>
        ${remark ? `<small class="eta-remark">${escapeHtml(remark)}</small>` : ""}
      </span>`;
  }).join("");

  return `
    <div class="route-row" role="listitem">
      <span class="route-code">${escapeHtml(journey.route || "-")}</span>
      <span class="route-destination">
        ${journeyLabel}
        ${destinationNote ? `<small class="destination-note">${escapeHtml(destinationNote)}</small>` : ""}
      </span>
      ${etaSlots}
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
  const fontSize = Object.hasOwn(FONT_SCALES, options.font_size)
    ? options.font_size
    : "normal";
  const fontScale = FONT_SCALES[fontSize];
  const configuredEtaCount = [1, 2, 3].includes(Number(options.max_etas))
    ? Number(options.max_etas)
    : 3;
  const etaCount = Math.min(configuredEtaCount, ETA_LIMITS[size]);
  const copy = COPY[language];

  if (data.error) {
    shadow.innerHTML = errorMarkup(data.error, size, fontSize, fontScale);
    return;
  }

  const routes = Array.isArray(data.routes)
    ? data.routes
    : data.journey
      ? [{ journey: data.journey, arrivals: data.arrivals, error: data.error }]
      : [];
  if (!routes.length) {
    shadow.innerHTML = errorMarkup(copy.noService, size, fontSize, fontScale);
    return;
  }

  const showRemarks = options.show_remarks !== false;
  const routeLimit = ROUTE_LIMITS[size];
  const hasOverflow = routes.length > routeLimit;
  const visibleRoutes = hasOverflow ? routes.slice(0, routeLimit - 1) : routes;
  const hiddenCount = routes.length - visibleRoutes.length;
  const rows = visibleRoutes.map((route) => routeMarkup(
    route,
    language,
    copy,
    showRemarks,
    etaCount,
  ));
  if (hiddenCount) {
    rows.push(`<div class="more-row">${escapeHtml(copy.moreRoutes(hiddenCount))}</div>`);
  }

  const updateIso = data.data_timestamp || data.generated_timestamp || new Date().toISOString();
  const updateTime = formatTime(updateIso, language);
  const staleClass = data.stale ? " is-stale" : "";
  const footerLabel = data.stale ? `${copy.source} · ${copy.stale}` : copy.source;

  shadow.innerHTML = `
    <link rel="stylesheet" href="/static/style/spectra-widgets.css">
    ${styles(fontScale)}
    <div class="w size-${escapeHtml(size)} bus-board${staleClass}" data-widget="hk_bus_arrival" data-font-size="${escapeHtml(fontSize)}" data-eta-count="${etaCount}" style="--eta-count:${etaCount}">
      <header class="board-head">
        <div class="brand-row">
          <h3 class="brand-title">KMB Bus Arrivals</h3>
          <i class="ph-bold ph-bus brand-icon" aria-hidden="true"></i>
        </div>
      </header>
      <div class="route-list" role="list" style="--row-count:${rows.length}">${rows.join("")}</div>
      <footer class="board-footer">
        <span class="kmb-mark" aria-hidden="true">KMB</span>
        <span class="footer-label">${escapeHtml(footerLabel)}</span>
        <time class="footer-time" datetime="${escapeHtml(updateIso)}">${escapeHtml(updateTime)}</time>
      </footer>
    </div>`;
}
