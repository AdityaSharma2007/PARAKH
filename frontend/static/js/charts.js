/**
 * Zero-dependency SVG Chart Generator for PARAKH
 */

export function renderTrendChart(containerId, dataPoints = []) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!dataPoints || dataPoints.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 40px;">No interview session data available yet. Complete an interview to track progression.</div>`;
    return;
  }

  const width = 800;
  const height = 260;
  const padding = 50;

  const minScore = 0;
  const maxScore = 100;

  // X coordinate calculation
  const getX = (index) => {
    if (dataPoints.length === 1) return width / 2;
    return padding + (index * (width - 2 * padding)) / (dataPoints.length - 1);
  };

  // Y coordinate calculation
  const getY = (val) => {
    return height - padding - ((val - minScore) / (maxScore - minScore)) * (height - 2 * padding);
  };

  // Build line path
  let pathD = "";
  dataPoints.forEach((pt, i) => {
    const x = getX(i);
    const y = getY(pt.overall_score);
    pathD += (i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`);
  });

  // Area path for gradient fill
  let areaD = pathD;
  if (dataPoints.length > 1) {
    const lastX = getX(dataPoints.length - 1);
    const firstX = getX(0);
    const baseY = height - padding;
    areaD += ` L ${lastX} ${baseY} L ${firstX} ${baseY} Z`;
  }

  // Grid lines (every 25 points)
  let gridLines = "";
  [25, 50, 75, 100].forEach((level) => {
    const y = getY(level);
    gridLines += `
      <line x1="${padding}" y1="${y}" x2="${width - padding}" y2="${y}" class="chart-grid-line" />
      <text x="${padding - 10}" y="${y + 4}" class="chart-axis-text" text-anchor="end">${level}</text>
    `;
  });

  // Data point dots & tooltips
  let dots = "";
  dataPoints.forEach((pt, i) => {
    const x = getX(i);
    const y = getY(pt.overall_score);
    dots += `
      <circle cx="${x}" cy="${y}" r="5" class="chart-point">
        <title>Interview #${pt.interview_id} (${pt.date}): ${pt.overall_score}/100</title>
      </circle>
      <text x="${x}" y="${height - padding + 20}" class="chart-axis-text" text-anchor="middle">${pt.date}</text>
      <text x="${x}" y="${y - 12}" class="chart-axis-text" text-anchor="middle" font-weight="bold" fill="#fff">${pt.overall_score}</text>
    `;
  });

  container.innerHTML = `
    <svg class="svg-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">
      <defs>
        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#6366f1" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#6366f1" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      ${gridLines}
      ${dataPoints.length > 1 ? `<path d="${areaD}" class="chart-area" />` : ""}
      <path d="${pathD}" class="chart-line" />
      ${dots}
    </svg>
  `;
}
