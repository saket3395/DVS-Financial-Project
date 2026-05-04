const REFRESH_MS = 5 * 60 * 1000;

const state = {
  stocks: [],
  filter: "ALL",
  selected: null,
  chart: null,
  series: null,
};

function classify(s) {
  const rsi = Number(s.RSI);
  const upside = Number(s["Upside%"]);
  if (Number.isFinite(rsi) && rsi <= 40 && Number.isFinite(upside) && upside >= 15) return "BUY";
  if (Number.isFinite(rsi) && rsi >= 65) return "SELL";
  if (Number.isFinite(upside) && upside >= 25) return "BUY";
  return "NEUTRAL";
}

function fmtNum(n, d = 2) {
  if (n === null || n === undefined || n === "" || !Number.isFinite(Number(n))) return "—";
  return Number(n).toFixed(d);
}

function fmtMcap(cr) {
  const n = Number(cr);
  if (!Number.isFinite(n)) return "—";
  if (n >= 1e5) return (n / 1e5).toFixed(2) + "L Cr";
  return n.toFixed(0) + " Cr";
}

function fmtUpdated(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
    const fmt = d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", hour12: false,
    });
    return `${fmt} IST`;
  } catch (e) {
    return iso;
  }
}

function heatColor(upside) {
  const n = Number(upside);
  if (!Number.isFinite(n)) return "#2c3245";
  if (n >= 30) return "#15803d";
  if (n >= 18) return "#22c55e";
  if (n >= 10) return "#4d7c5e";
  if (n >= 0) return "#3a3f4f";
  if (n >= -10) return "#7f1d1d";
  return "#dc2626";
}

function renderSignals() {
  const list = document.getElementById("signals-list");
  const items = state.stocks
    .map((s) => ({ ...s, _signal: classify(s) }))
    .filter((s) => state.filter === "ALL" || s._signal === state.filter)
    .sort((a, b) => Number(b["Upside%"] || 0) - Number(a["Upside%"] || 0));

  if (!items.length) {
    list.innerHTML = '<div class="p-3 text-secondary text-center">No signals</div>';
    return;
  }

  list.innerHTML = items
    .map(
      (s) => `
    <div class="signal-row ${s.Stock === state.selected ? "active" : ""}" data-ticker="${s.Stock}">
      <div><span class="tag tag-${s._signal}">${s._signal}</span><span class="ticker">${s.Stock}</span></div>
      <div class="price">₹${fmtNum(s.Price)}</div>
      <div class="meta">RSI ${fmtNum(s.RSI, 1)} · ${fmtMcap(s["MCap(Cr)"])}</div>
      <div class="meta-right">+${fmtNum(s["Upside%"], 1)}%</div>
    </div>`
    )
    .join("");

  list.querySelectorAll(".signal-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.selected = row.dataset.ticker;
      renderSignals();
      loadChart(state.selected);
    });
  });
}

function renderHeatmap() {
  const host = document.getElementById("heatmap");
  if (!state.stocks.length) {
    host.innerHTML = '<div class="text-secondary text-center py-3">No data</div>';
    return;
  }
  const sorted = [...state.stocks].sort(
    (a, b) => Number(b["Upside%"] || -999) - Number(a["Upside%"] || -999)
  );
  host.innerHTML = sorted
    .map(
      (s) => `
    <div class="heat-cell" data-ticker="${s.Stock}" style="background:${heatColor(s["Upside%"])}">
      <span class="sym">${s.Stock}</span>
      <span class="val">${fmtNum(s["Upside%"], 1)}%</span>
    </div>`
    )
    .join("");
  host.querySelectorAll(".heat-cell").forEach((cell) => {
    cell.addEventListener("click", () => {
      state.selected = cell.dataset.ticker;
      renderSignals();
      loadChart(state.selected);
    });
  });
}

function ensureChart() {
  if (state.chart) return;
  const host = document.getElementById("chart");
  state.chart = LightweightCharts.createChart(host, {
    layout: { background: { color: "#131722" }, textColor: "#cbd5e1" },
    grid: { vertLines: { color: "#1f2434" }, horzLines: { color: "#1f2434" } },
    rightPriceScale: { borderColor: "#2a2f3d" },
    timeScale: { borderColor: "#2a2f3d", timeVisible: false },
    crosshair: { mode: 1 },
    width: host.clientWidth,
    height: host.clientHeight,
  });
  state.series = state.chart.addCandlestickSeries({
    upColor: "#16a34a",
    downColor: "#dc2626",
    borderUpColor: "#16a34a",
    borderDownColor: "#dc2626",
    wickUpColor: "#16a34a",
    wickDownColor: "#dc2626",
  });
  window.addEventListener("resize", () => {
    if (state.chart) state.chart.applyOptions({ width: host.clientWidth, height: host.clientHeight });
  });
}

async function loadChart(ticker) {
  if (!ticker) return;
  ensureChart();
  document.getElementById("chart-ticker").textContent = ticker;
  document.getElementById("chart-meta").textContent = "loading…";
  try {
    const res = await fetch(`/api/ohlc?ticker=${encodeURIComponent(ticker)}`);
    const bars = await res.json();
    if (!bars.length) {
      document.getElementById("chart-meta").textContent = "no OHLC data";
      state.series.setData([]);
      return;
    }
    state.series.setData(bars);
    state.chart.timeScale().fitContent();
    const last = bars[bars.length - 1];
    const change = ((last.close - bars[0].open) / bars[0].open) * 100;
    document.getElementById("chart-meta").textContent =
      `${bars.length} bars · last ₹${last.close.toFixed(2)} · ${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
  } catch (e) {
    document.getElementById("chart-meta").textContent = "error loading OHLC";
  }
}

async function loadStocks() {
  try {
    const res = await fetch("/api/stocks");
    const payload = await res.json();
    state.stocks = payload.stocks || [];
    document.getElementById("updated-at").textContent = fmtUpdated(payload.generated_at);
    document.getElementById("stock-count").textContent = state.stocks.length;
    renderSignals();
    renderHeatmap();
    if (!state.selected && state.stocks.length) {
      state.selected = state.stocks[0].Stock;
      renderSignals();
      loadChart(state.selected);
    }
  } catch (e) {
    document.getElementById("refresh-badge").textContent = "offline";
  }
}

function bindFilters() {
  document.querySelectorAll("#signal-filters [data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll("#signal-filters [data-filter]")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.filter = btn.dataset.filter;
      renderSignals();
    });
  });
}

bindFilters();
loadStocks();
setInterval(loadStocks, REFRESH_MS);
