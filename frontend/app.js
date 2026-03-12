const fmtNumber = new Intl.NumberFormat('en-US');
const fmtMoney = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

let anthropicChart;
let googleChart;

function setBadge(element, status) {
  element.className = 'status-badge';
  if (status === 'connected') {
    element.textContent = 'Connected';
  } else if (status === 'error') {
    element.textContent = 'Error';
    element.classList.add('error');
  } else if (status === 'not_configured') {
    element.textContent = 'Not configured';
    element.classList.add('empty');
  } else {
    element.textContent = 'Loading';
    element.classList.add('empty');
  }
}

function renderInlineState(target, payload, retryHandler) {
  if (payload.status === 'connected') {
    target.classList.add('hidden');
    target.innerHTML = '';
    return;
  }
  target.className = `inline-state ${payload.status === 'error' ? 'error' : ''}`;
  target.classList.remove('hidden');
  const action = payload.status === 'error' ? '<button class="retry-button">Retry</button>' : '';
  target.innerHTML = `<span>${payload.message || 'No data available'}</span>${action}`;
  if (payload.status === 'error') {
    target.querySelector('button').addEventListener('click', retryHandler);
  }
}

function renderAnthropic(payload) {
  setBadge(document.getElementById('anthropicBadge'), payload.status);
  document.getElementById('anthropicInput').textContent = fmtNumber.format(payload.totals.input_tokens || 0);
  document.getElementById('anthropicOutput').textContent = fmtNumber.format(payload.totals.output_tokens || 0);
  document.getElementById('anthropicCost').textContent = fmtMoney.format(payload.totals.cost_usd || 0);

  const modelsEl = document.getElementById('anthropicModels');
  modelsEl.innerHTML = '';
  const maxTokens = Math.max(1, ...payload.models.map((m) => m.input_tokens + m.output_tokens), 1);
  payload.models.forEach((model) => {
    const total = model.input_tokens + model.output_tokens;
    const row = document.createElement('div');
    row.className = 'model-row';
    row.innerHTML = `
      <div class="model-label">${model.model}</div>
      <div class="model-pill">
        <div class="input" style="width:${(model.input_tokens / maxTokens) * 100}%"></div>
        <div class="output" style="width:${(model.output_tokens / maxTokens) * 100}%"></div>
      </div>
      <div class="model-meta">${fmtNumber.format(model.input_tokens)} in · ${fmtNumber.format(model.output_tokens)} out · ${fmtMoney.format(model.cost_usd)}</div>
    `;
    modelsEl.appendChild(row);
  });

  const ctx = document.getElementById('anthropicDailyChart');
  if (anthropicChart) anthropicChart.destroy();
  anthropicChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: payload.daily.map((d) => d.date.slice(5)),
      datasets: [
        { label: 'Input', data: payload.daily.map((d) => d.input_tokens), borderColor: '#2B9AA0', tension: 0.3, fill: false },
        { label: 'Output', data: payload.daily.map((d) => d.output_tokens), borderColor: '#4D6FE8', tension: 0.3, fill: false },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#93a1b2' } } },
      scales: {
        x: { ticks: { color: '#93a1b2' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#93a1b2' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
    },
  });

  renderInlineState(document.getElementById('anthropicState'), payload, () => refreshData(true));
}

function renderGoogle(payload) {
  setBadge(document.getElementById('googleBadge'), payload.status);
  document.getElementById('googleRequests').textContent = fmtNumber.format(payload.totals.requests || 0);
  document.getElementById('googleErrors').textContent = fmtNumber.format(payload.totals.errors || 0);
  document.getElementById('googleRate').textContent = `${payload.totals.error_rate || 0}%`;

  const servicesEl = document.getElementById('googleServices');
  servicesEl.innerHTML = '';
  payload.services.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.service}</td><td>${fmtNumber.format(row.requests)}</td><td>${fmtNumber.format(row.errors)}</td><td>${row.error_rate}%</td>`;
    servicesEl.appendChild(tr);
  });

  const ctx = document.getElementById('googleServicesChart');
  if (googleChart) googleChart.destroy();
  googleChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: payload.top_services.map((s) => s.service),
      datasets: [{
        label: 'Requests',
        data: payload.top_services.map((s) => s.requests),
        backgroundColor: ['#2B9AA0', '#3A8DBF', '#4D6FE8', '#2B9AA0AA', '#4D6FE8AA'],
        borderRadius: 10,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#93a1b2' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#93a1b2' }, grid: { display: false } },
      },
    },
  });

  renderInlineState(document.getElementById('googleState'), payload, () => refreshData(true));
}

function setLastUpdated() {
  document.getElementById('lastUpdated').textContent = `Last updated — ${new Date().toLocaleString()}`;
}

function setFooter(status) {
  const anthAge = status.services.anthropic.cache_age_seconds;
  const googleAge = status.services.google.cache_age_seconds;
  document.getElementById('footerCache').textContent = `Cache age — Anthropic: ${anthAge == null ? '—' : Math.floor(anthAge / 60) + 'm'}, Google Cloud: ${googleAge == null ? '—' : Math.floor(googleAge / 60) + 'm'}`;
}

async function refreshData(force = false) {
  const query = force ? '?refresh=true' : '';
  const [anthropic, google, status] = await Promise.all([
    fetch(`/api/usage/anthropic${query}`).then((r) => r.json()),
    fetch(`/api/usage/google${query}`).then((r) => r.json()),
    fetch('/api/status').then((r) => r.json()),
  ]);
  renderAnthropic(anthropic);
  renderGoogle(google);
  setFooter(status);
  setLastUpdated();
}

document.getElementById('refreshButton').addEventListener('click', () => refreshData(true));
refreshData().catch((error) => {
  console.error(error);
  document.getElementById('lastUpdated').textContent = 'Last updated — failed to load';
});
