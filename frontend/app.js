const fmtNumber = new Intl.NumberFormat('en-US');
const fmtMoney = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

let anthropicChart;
let googleChart;
let refreshInFlight = false;

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

  target.className = `inline-state${payload.status === 'error' ? ' error' : ''}`;
  target.classList.remove('hidden');
  const action = payload.status === 'error' ? '<button class="retry-button" type="button">Retry</button>' : '';
  target.innerHTML = `<span>${payload.message || 'No data available'}</span>${action}`;
  if (payload.status === 'error') {
    const button = target.querySelector('button');
    if (button) {
      button.addEventListener('click', retryHandler, { once: true });
    }
  }
}

function createLineChart(canvas, labels, datasets) {
  return new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      resizeDelay: 200,
      plugins: { legend: { labels: { color: '#93a1b2' } } },
      scales: {
        x: { ticks: { color: '#93a1b2' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#93a1b2' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
    },
  });
}

function createBarChart(canvas, labels, dataset) {
  return new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: { labels, datasets: [dataset] },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      resizeDelay: 200,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#93a1b2' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#93a1b2' }, grid: { display: false } },
      },
    },
  });
}

function updateAnthropicChart(payload) {
  const labels = payload.daily.map((d) => d.date.slice(5));
  const inputData = payload.daily.map((d) => d.input_tokens);
  const outputData = payload.daily.map((d) => d.output_tokens);
  const canvas = document.getElementById('anthropicDailyChart');

  if (!anthropicChart) {
    anthropicChart = createLineChart(canvas, labels, [
      { label: 'Input', data: inputData, borderColor: '#2B9AA0', tension: 0.3, fill: false },
      { label: 'Output', data: outputData, borderColor: '#4D6FE8', tension: 0.3, fill: false },
    ]);
    return;
  }

  anthropicChart.data.labels = labels;
  anthropicChart.data.datasets[0].data = inputData;
  anthropicChart.data.datasets[1].data = outputData;
  anthropicChart.update('none');
}

function updateGoogleChart(payload) {
  const labels = payload.top_services.map((s) => s.service);
  const data = payload.top_services.map((s) => s.requests);
  const canvas = document.getElementById('googleServicesChart');

  if (!googleChart) {
    googleChart = createBarChart(canvas, labels, {
      label: 'Requests',
      data,
      backgroundColor: ['#2B9AA0', '#3A8DBF', '#4D6FE8', '#2B9AA0AA', '#4D6FE8AA'],
      borderRadius: 10,
    });
    return;
  }

  googleChart.data.labels = labels;
  googleChart.data.datasets[0].data = data;
  googleChart.update('none');
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

  updateAnthropicChart(payload);
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

  updateGoogleChart(payload);
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
  if (refreshInFlight) {
    return;
  }

  refreshInFlight = true;
  const refreshButton = document.getElementById('refreshButton');
  refreshButton.disabled = true;

  try {
    const query = force ? '?refresh=true' : '';
    const [anthropicRes, googleRes, statusRes] = await Promise.all([
      fetch(`/api/usage/anthropic${query}`),
      fetch(`/api/usage/google${query}`),
      fetch('/api/status'),
    ]);

    const [anthropic, google, status] = await Promise.all([
      anthropicRes.json(),
      googleRes.json(),
      statusRes.json(),
    ]);

    renderAnthropic(anthropic);
    renderGoogle(google);
    setFooter(status);
    setLastUpdated();
  } finally {
    refreshInFlight = false;
    refreshButton.disabled = false;
  }
}

window.addEventListener('beforeunload', () => {
  if (anthropicChart) anthropicChart.destroy();
  if (googleChart) googleChart.destroy();
});

document.getElementById('refreshButton').addEventListener('click', () => refreshData(true));
refreshData().catch((error) => {
  console.error(error);
  document.getElementById('lastUpdated').textContent = 'Last updated — failed to load';
});
