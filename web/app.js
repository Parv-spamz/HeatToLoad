/**
 * Heat To Load // Institutional Analytics Application Engine
 * Styled after BloombergNEF, Our World in Data, and Palantir Foundry.
 * Drives interactive Chart.js visualizations, climate slider simulator,
 * state search with detailed dossier modal, and standardized data filtering.
 */

let appData = null;
let charts = {};

// Purpose-Driven Institutional Palette
const COLORS = {
    textMain: '#f1f5f9',
    textMuted: '#94a3b8',
    textDim: '#64748b',
    accent: '#38bdf8',           // Crisp cobalt/sky accent
    alertRed: '#f87171',         // Soft alert red strictly for thermal stress/risk
    alertGreen: '#34d399',       // Soft mint strictly for accuracy / low error
    amber: '#fbbf24',            // Subdued temperature amber
    barSlate: '#262f3d',         // Slate bar fill
    barSlateBorder: '#38bdf8',   // Crisp accent border edge
    barHighRisk: '#f87171',      // Risk highlight
    gridLines: 'rgba(255, 255, 255, 0.05)',
    tooltipBg: '#151921',
    tooltipBorder: 'rgba(255, 255, 255, 0.1)'
};

// Qualitative state summaries based on empirical energy profiles
const STATE_DESCRIPTIONS = {
    'Karnataka': 'High cooling elasticity driven by commercial IT infrastructure, tech campus data centers, and rapid urban air conditioning penetration across the Bengaluru metropolitan region.',
    'West Bengal': 'Severe humidity-amplified cooling surge during sultry pre-monsoon heatwaves along the lower Gangetic plain and Kolkata urban cluster.',
    'Kerala': 'Coastal humidity load multiplier; rapid adoption of residential inverter air conditioning drives evening peak demand surges in Kochi and Thiruvananthapuram.',
    'Odisha': 'Heavy industrial baseload combined with severe coastal heat index spikes during April–June heatwaves across the coastal belt.',
    'Andhra Pradesh': 'Agricultural irrigation pumping synchronized with coastal cooling demand across Vijayawada, Guntur, and Visakhapatnam.',
    'Bihar': 'Substantial latent residential demand and rural electrification expansion triggering rapid cooling surges when temperatures breach 40°C.',
    'Punjab': 'Heavy paddy irrigation pumping load synchronized with extreme continental heat dome conditions across Ludhiana and Amritsar.',
    'Tamil Nadu': 'Massive diversified manufacturing and textile base with intense summer cooling demand across Chennai and Coimbatore.',
    'Maharashtra': 'Largest aggregate power volume state in India; industrial hubs in Pune and coastal commercial cooling in Mumbai drive national coincident peaks.',
    'Uttar Pradesh': 'India’s largest population center; massive rural electrification and residential cooling load creates the country’s highest aggregate summer peak additions.',
    'Gujarat': 'Dominant round-the-clock chemical and petrochemical industrial load combined with severe Saurashtra desert heat spikes.',
    'Haryana': 'Intense commercial office and residential cooling surge concentrated in Gurgaon and Faridabad adjacent to the National Capital Region.',
    'Madhya Pradesh': 'Central transmission crossroads; extensive agricultural pumping combined with central continental heatwave exposure.',
    'Telangana': 'High-density tech commercial real estate and pharmaceutical manufacturing load across the greater Hyderabad urban agglomeration.',
    'Delhi': 'Pure commercial and high-density residential cooling demand with near-total air conditioning saturation; sensitive to sudden nighttime heat spikes.',
    'Rajasthan': 'Extreme desert temperature swings exceeding 48°C in Jodhpur and Bikaner with significant solar self-consumption during daylight hours.'
};

// Global Chart.js Defaults
Chart.defaults.color = COLORS.textMuted;
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.tooltip.backgroundColor = COLORS.tooltipBg;
Chart.defaults.plugins.tooltip.borderColor = COLORS.tooltipBorder;
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 6;
Chart.defaults.plugins.tooltip.titleFont = { weight: '600', size: 12 };
Chart.defaults.plugins.tooltip.bodyFont = { family: "'JetBrains Mono', monospace", size: 11 };
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 6;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const resp = await fetch('data.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        appData = await resp.json();

        initKPIs();
        initStateDropdown();
        initSensitivityChart('all');
        initResponseCurveChart(appData.states[0]?.state || 'Maharashtra');
        initHeatwaveTimelineChart();
        initSimulator();
        initSHAPChart();
        initTable();
        initSearch();
        initModal();
        initEventHandlers();
    } catch (err) {
        console.error('Failed to load dashboard data:', err);
    }
});

// 1. Initialize Top KPIs
function initKPIs() {
    const summary = appData.summary || {};
    const holdout = appData.holdout_metrics || {};

    if (summary.all_india_combined_mw_per_c) {
        document.getElementById('kpi-mw-c').innerHTML = `+${summary.all_india_combined_mw_per_c.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} <span class="kpi-unit">MW / °C</span>`;
    }
    if (summary.state_average_pct_per_c) {
        document.getElementById('kpi-pct-c').innerHTML = `+${summary.state_average_pct_per_c.toFixed(2)}% <span class="kpi-unit">/ °C</span>`;
    }
    if (holdout.operational?.mape_pct) {
        document.getElementById('kpi-mape').innerHTML = `${holdout.operational.mape_pct.toFixed(2)}% <span class="kpi-unit">MAPE</span>`;
    }
}

// 2. State Dropdown
function initStateDropdown() {
    const select = document.getElementById('state-select');
    if (!select) return;
    select.innerHTML = '';
    appData.states.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.state;
        opt.textContent = `${s.state} (${s.region}) — +${s.pct_per_c.toFixed(2)}%/°C`;
        select.appendChild(opt);
    });

    select.addEventListener('change', (e) => {
        updateResponseCurve(e.target.value);
    });
}

// 3. Chart 1: State Sensitivity Ranking
function initSensitivityChart(regionFilter = 'all') {
    const ctx = document.getElementById('chart-sensitivity').getContext('2d');
    
    let filteredStates = [...appData.states];
    if (regionFilter !== 'all') {
        filteredStates = filteredStates.filter(s => s.region === regionFilter);
    }

    filteredStates.sort((a, b) => b.pct_per_c - a.pct_per_c);

    const labels = filteredStates.map(s => s.state);
    const dataPct = filteredStates.map(s => s.pct_per_c);

    // Solid color fill using the accent and alert colors with no outline
    const barColors = dataPct.map(v => v >= 2.5 ? COLORS.alertRed : COLORS.accent);

    if (charts.sensitivity) {
        charts.sensitivity.data.labels = labels;
        charts.sensitivity.data.datasets[0].data = dataPct;
        charts.sensitivity.data.datasets[0].backgroundColor = barColors;
        charts.sensitivity.update();
        return;
    }

    charts.sensitivity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sensitivity (%/°C)',
                data: dataPct,
                backgroundColor: barColors,
                borderWidth: 0,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const idx = elements[0].index;
                    const stateName = charts.sensitivity.data.labels[idx];
                    openStateModal(stateName);
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `+${ctx.raw.toFixed(2)}% per °C (Click to inspect)`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: '% Increase per °C above baseline', color: COLORS.textDim }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: COLORS.textMain, font: { weight: '500' } }
                }
            }
        }
    });
}

// 4. Chart 2: Non-linear Temperature Response Curve
function initResponseCurveChart(stateName) {
    const ctx = document.getElementById('chart-response-curve').getContext('2d');
    const stateData = appData.state_curves[stateName] || { points: [], fit_line: [] };

    const scatterData = stateData.points.map(p => ({ x: p.t, y: p.mw }));
    const lineData = stateData.fit_line.map(p => ({ x: p.t, y: p.mw }));

    charts.responseCurve = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Daily Observations (SCADA)',
                    data: scatterData,
                    normalized: true,
                    backgroundColor: 'rgba(56, 189, 248, 0.32)',
                    borderColor: 'transparent',
                    pointRadius: 3,
                    order: 2
                },
                {
                    label: 'Polynomial Thermal Response',
                    type: 'line',
                    data: lineData,
                    normalized: true,
                    borderColor: COLORS.alertRed,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.15,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: { color: COLORS.textMuted }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.x.toFixed(1)}°C → ${Math.round(ctx.parsed.y).toLocaleString()} MW`
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Daily Maximum Temperature (°C) — ERA5 Reanalysis', color: COLORS.textDim }
                },
                y: {
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Peak Electricity Demand (MW) — SCADA', color: COLORS.textDim },
                    ticks: { callback: (v) => `${(v / 1000).toFixed(1)}k` }
                }
            }
        }
    });
}

function updateResponseCurve(stateName) {
    const stateData = appData.state_curves[stateName];
    if (!stateData || !charts.responseCurve) return;

    charts.responseCurve.data.datasets[0].data = stateData.points.map(p => ({ x: p.t, y: p.mw }));
    charts.responseCurve.data.datasets[1].data = stateData.fit_line.map(p => ({ x: p.t, y: p.mw }));
    charts.responseCurve.update('none');
}

// 5. Chart 3: Heatwave Timeline Tracking
function initHeatwaveTimelineChart() {
    const ctx = document.getElementById('chart-heatwave-timeline').getContext('2d');
    const timeline = appData.heatwave_timeline || [];

    const dates = timeline.map(t => t.date.slice(5)); // MM-DD
    const actual = timeline.map(t => t.actual_mw);
    const pred = timeline.map(t => t.q50_pred_mw);
    const temp = timeline.map(t => t.mean_tmax_c);

    charts.heatwave = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Actual Coincident Demand (MW)',
                    data: actual,
                    borderColor: COLORS.accent,
                    backgroundColor: 'rgba(56, 189, 248, 0.05)',
                    borderWidth: 1.8,
                    pointRadius: 2,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Model Forecast (Q50)',
                    data: pred,
                    borderColor: COLORS.alertRed,
                    borderWidth: 1.6,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'Daytime Temperature (°C)',
                    data: temp,
                    borderColor: COLORS.amber,
                    borderWidth: 1.4,
                    pointRadius: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 15, color: COLORS.textMuted }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Coincident Peak Demand (MW)', color: COLORS.textDim },
                    ticks: { callback: (v) => `${Math.round(v / 1000)}k` }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    grid: { display: false },
                    title: { display: true, text: 'Max Temperature (°C)', color: COLORS.textDim },
                    min: 28,
                    max: 48,
                    ticks: { color: COLORS.amber }
                }
            }
        }
    });
}

// 6. Interactive Simulator (+0.5°C to +3.0°C)
function initSimulator() {
    const slider = document.getElementById('temp-slider');
    const badge = document.getElementById('slider-badge');
    
    const peakGwEl = document.getElementById('sim-peak-gw');
    const surgeMwEl = document.getElementById('sim-surge-mw');
    const surgePctEl = document.getElementById('sim-surge-pct');
    const riskLevelEl = document.getElementById('sim-risk-level');

    const ctx = document.getElementById('chart-simulator-compare').getContext('2d');

    const basePeak = appData.scenarios?.plus_1c?.all_india_coincident_baseline_peak_mw || 223421.1;

    function getTempStage(deltaT) {
        if (deltaT <= 1.2) {
            return {
                color: COLORS.accent,
                borderColor: 'rgba(56, 189, 248, 0.4)',
                bg: 'rgba(56, 189, 248, 0.08)',
                thumbColor: COLORS.accent,
                riskText: 'MODERATE STRESS',
                riskClass: 'sim-val text-sky'
            };
        } else if (deltaT <= 2.1) {
            return {
                color: COLORS.amber,
                borderColor: 'rgba(251, 191, 36, 0.4)',
                bg: 'rgba(251, 191, 36, 0.08)',
                thumbColor: COLORS.amber,
                riskText: 'HIGH CORRIDOR RISK',
                riskClass: 'sim-val text-amber'
            };
        } else {
            return {
                color: COLORS.alertRed,
                borderColor: 'rgba(248, 113, 113, 0.45)',
                bg: 'rgba(248, 113, 113, 0.08)',
                thumbColor: COLORS.alertRed,
                riskText: 'CRITICAL DEFICIT',
                riskClass: 'sim-val text-alert'
            };
        }
    }

    function recalculate(deltaT) {
        const stage = getTempStage(deltaT);

        if (badge) {
            badge.textContent = `+${deltaT.toFixed(1)}°C`;
            badge.style.color = stage.color;
            badge.style.borderColor = stage.borderColor;
            badge.style.backgroundColor = stage.bg;
        }
        
        if (slider) {
            slider.style.setProperty('--slider-thumb-color', stage.thumbColor);
        }
        
        const surgeMw = (deltaT * 2761.9) + (deltaT ** 1.35 * 420.0);
        const scenarioPeak = basePeak + surgeMw;
        const surgePct = (surgeMw / basePeak) * 100.0;

        if (peakGwEl) peakGwEl.textContent = `${(scenarioPeak / 1000.0).toFixed(1)} GW`;
        if (surgeMwEl) surgeMwEl.textContent = `+${Math.round(surgeMw).toLocaleString()} MW`;
        if (surgePctEl) surgePctEl.textContent = `+${surgePct.toFixed(2)}%`;

        if (riskLevelEl) {
            riskLevelEl.textContent = stage.riskText;
            riskLevelEl.className = stage.riskClass;
        }

        updateSimChart(basePeak, scenarioPeak, deltaT);
    }

    function updateSimChart(base, scen, deltaT) {
        const labels = ['Baseline (Observed)', `Simulated (+${deltaT.toFixed(1)}°C)`];
        const data = [base / 1000.0, scen / 1000.0];
        const colors = [
            'rgba(56, 189, 248, 0.35)', 
            deltaT >= 2.0 ? 'rgba(248, 113, 113, 0.85)' : 'rgba(251, 191, 36, 0.85)'
        ];
        const borderColors = [
            COLORS.accent,
            deltaT >= 2.0 ? COLORS.alertRed : COLORS.amber
        ];

        if (charts.simCompare) {
            charts.simCompare.data.labels = labels;
            charts.simCompare.data.datasets[0].data = data;
            charts.simCompare.data.datasets[0].backgroundColor = colors;
            charts.simCompare.data.datasets[0].borderColor = borderColors;
            charts.simCompare.update('none'); // Real-time 60fps instant redraw with no animation queueing
        } else {
            charts.simCompare = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Coincident Peak (GW)',
                        data: data,
                        backgroundColor: colors,
                        borderColor: borderColors,
                        borderWidth: 1,
                        borderRadius: 6,
                        barThickness: 50
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 0 },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: { label: (ctx) => `${ctx.raw.toFixed(1)} GW` }
                        }
                    },
                    scales: {
                        y: {
                            min: 200,
                            max: 245,
                            grid: { color: COLORS.gridLines },
                            title: { display: true, text: 'Gigawatts (GW)', color: COLORS.textDim }
                        },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    }

    let simRaf = null;
    if (slider) {
        slider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            if (simRaf) cancelAnimationFrame(simRaf);
            simRaf = requestAnimationFrame(() => {
                recalculate(val);
            });
        });
        recalculate(parseFloat(slider.value));
    }
}

// 7. Chart 5: SHAP Attribution (High-fidelity purple attribution bars)
function initSHAPChart() {
    const canvas = document.getElementById('chart-shap');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const drivers = appData.shap_drivers || [];

    const labels = drivers.map(d => d.feature.replace(/_/g, ' '));
    const impacts = drivers.map(d => d.impact_mw);

    charts.shap = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mean |SHAP| (MW)',
                data: impacts,
                backgroundColor: '#8b5cf6',
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: { label: (ctx) => `+${ctx.raw.toLocaleString()} MW Mean Attribution` }
                }
            },
            scales: {
                x: {
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Mean Absolute Impact on Peak (MW)', color: COLORS.textDim }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: COLORS.textMain, font: { weight: '500' } }
                }
            }
        }
    });
}

// 8. Data League Table (Standardized neutral region badges)
function initTable() {
    const tbody = document.getElementById('states-table-body');
    const search = document.getElementById('state-search');
    if (!tbody) return;

    const rowCache = [];
    tbody.innerHTML = '';
    
    appData.states.forEach(s => {
        const tr = document.createElement('tr');
        tr.title = `Click to view comprehensive details for ${s.state}`;
        const isHighStress = s.pct_per_c >= 2.5;

        tr.innerHTML = `
            <td class="state-badge">${s.state}</td>
            <td><span class="region-pill">${s.region}</span></td>
            <td>${s.city}</td>
            <td class="num-td">${Math.round(s.mean_demand_mw).toLocaleString()} MW</td>
            <td class="num-td" style="color: var(--accent); font-weight: 600;">+${s.mw_per_c.toFixed(1)}</td>
            <td class="num-td" style="color: ${isHighStress ? 'var(--alert-red)' : 'var(--text-main)'}; font-weight: 700;">+${s.pct_per_c.toFixed(2)}%</td>
            <td class="num-td">+${s.cdd_slope_mw.toFixed(1)}</td>
            <td class="num-td" style="color: ${s.holdout_mape <= 7 ? 'var(--alert-green)' : 'inherit'};">${s.holdout_mape.toFixed(2)}%</td>
            <td class="num-td">${s.holdout_r2.toFixed(2)}</td>
        `;
        tr.addEventListener('click', () => {
            openStateModal(s.state);
        });
        tbody.appendChild(tr);
        rowCache.push({
            el: tr,
            searchKey: `${s.state} ${s.region} ${s.city} ${s.code}`.toLowerCase()
        });
    });

    if (search) {
        search.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            for (let i = 0; i < rowCache.length; i++) {
                const item = rowCache[i];
                item.el.style.display = (!query || item.searchKey.includes(query)) ? '' : 'none';
            }
        });
    }
}

// 9. State Search & Autocomplete
function initSearch() {
    const searchInput = document.getElementById('state-search-global');
    const dropdown = document.getElementById('search-autocomplete-list');
    if (!searchInput || !dropdown) return;

    function renderResults(query) {
        if (!query) {
            dropdown.innerHTML = '';
            dropdown.classList.add('hidden');
            return;
        }

        const matches = appData.states.filter(s =>
            s.state.toLowerCase().includes(query) ||
            s.region.toLowerCase().includes(query) ||
            s.city.toLowerCase().includes(query) ||
            s.code.toLowerCase().includes(query)
        );

        if (matches.length === 0) {
            dropdown.innerHTML = `<div style="padding: 8px 12px; font-size: 11px; color: var(--text-dim);">No matching states</div>`;
            dropdown.classList.remove('hidden');
            return;
        }

        dropdown.innerHTML = '';
        matches.forEach(s => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            const isHighStress = s.pct_per_c >= 2.5;
            item.innerHTML = `
                <div class="ac-left">
                    <span class="ac-name">${s.state}</span>
                    <span class="ac-meta">${s.region} &bull; ${s.city}</span>
                </div>
                <div class="ac-right">
                    <span class="ac-badge" style="color: ${isHighStress ? 'var(--alert-red)' : 'var(--text-muted)'}">+${s.pct_per_c.toFixed(2)}%/°C</span>
                </div>
            `;
            item.addEventListener('click', () => {
                openStateModal(s.state);
                searchInput.value = '';
                dropdown.classList.add('hidden');
            });
            dropdown.appendChild(item);
        });

        dropdown.classList.remove('hidden');
    }

    searchInput.addEventListener('input', (e) => {
        renderResults(e.target.value.toLowerCase().trim());
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            dropdown.classList.add('hidden');
            searchInput.blur();
        } else if (e.key === 'Enter') {
            const firstItem = dropdown.querySelector('.autocomplete-item');
            if (firstItem) {
                firstItem.click();
            }
        }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    // Global '/' shortcut to focus search
    window.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement !== searchInput && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }
    });
}

// 10. State Comprehensive Details Modal (Institutional Style)
function initModal() {
    const modal = document.getElementById('state-modal');
    const closeBtn = document.getElementById('modal-close-btn');
    const backdrop = document.getElementById('modal-backdrop');
    const btnInspect = document.getElementById('btn-open-state-modal');

    if (closeBtn) closeBtn.addEventListener('click', closeStateModal);
    if (backdrop) backdrop.addEventListener('click', closeStateModal);

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeStateModal();
        }
    });

    if (btnInspect) {
        btnInspect.addEventListener('click', () => {
            const currentSelected = document.getElementById('state-select').value;
            openStateModal(currentSelected);
        });
    }
}

function openStateModal(stateName) {
    const s = appData.states.find(item => item.state === stateName) || appData.states[0];
    if (!s) return;

    const modal = document.getElementById('state-modal');
    if (!modal) return;

    const regionNames = {
        'NR': 'NORTHERN REGION (NR)',
        'WR': 'WESTERN REGION (WR)',
        'SR': 'SOUTHERN REGION (SR)',
        'ER': 'EASTERN REGION (ER)'
    };

    // Header & Titles
    document.getElementById('modal-region-badge').textContent = regionNames[s.region] || s.region;
    document.getElementById('modal-state-name').textContent = s.state;
    document.getElementById('modal-load-center').textContent = `Centroid Weather & Grid Load Center: ${s.city} (${s.lat.toFixed(2)}°N, ${s.lon.toFixed(2)}°E)`;

    // Top Metric Strip (Clean tabular off-white, alert red strictly for surge)
    document.getElementById('modal-mean-demand').textContent = `${Math.round(s.mean_demand_mw).toLocaleString()} MW`;
    document.getElementById('modal-mw-c').textContent = `+${s.mw_per_c.toFixed(1)} MW/°C`;
    document.getElementById('modal-pct-c').textContent = `+${s.pct_per_c.toFixed(2)}% / °C surge`;
    document.getElementById('modal-cdd').textContent = `+${s.cdd_slope_mw.toFixed(1)} MW`;
    document.getElementById('modal-mape').textContent = `${s.holdout_mape.toFixed(2)}% MAPE`;
    document.getElementById('modal-r2').textContent = `Holdout R² = ${s.holdout_r2.toFixed(2)}`;

    // Narrative & Attributes List
    document.getElementById('modal-state-desc').textContent = STATE_DESCRIPTIONS[s.state] || 'Empirical cooling sensitivity evaluated over 730 consecutive daily SCADA load observations.';

    const attrList = document.getElementById('modal-attributes-list');
    attrList.innerHTML = `
        <div class="modal-attr-row">
            <span class="modal-attr-name">State Grid Code</span>
            <span class="modal-attr-val">${s.code}</span>
        </div>
        <div class="modal-attr-row">
            <span class="modal-attr-name">Centroid Coordinates</span>
            <span class="modal-attr-val">${s.lat.toFixed(4)}°N, ${s.lon.toFixed(4)}°E</span>
        </div>
        <div class="modal-attr-row">
            <span class="modal-attr-name">Marginal Thermal Elasticity</span>
            <span class="modal-attr-val" style="color: var(--accent);">+${s.mw_per_c.toFixed(2)} MW / °C</span>
        </div>
        <div class="modal-attr-row">
            <span class="modal-attr-name">Surge Rate (% of Baseline)</span>
            <span class="modal-attr-val" style="color: ${s.pct_per_c >= 2.5 ? 'var(--alert-red)' : 'var(--text-main)'};">+${s.pct_per_c.toFixed(2)}% / °C</span>
        </div>
        <div class="modal-attr-row">
            <span class="modal-attr-name">Cooling Degree Slope (CDD_24)</span>
            <span class="modal-attr-val">+${s.cdd_slope_mw.toFixed(1)} MW / CDD</span>
        </div>
        <div class="modal-attr-row">
            <span class="modal-attr-name">Balance Point Inflection Threshold</span>
            <span class="modal-attr-val">28.0°C (Cooling Saturation Point)</span>
        </div>
    `;

    // Meteorological Mechanics
    const mechanicsBox = document.getElementById('modal-mechanics-card');
    mechanicsBox.innerHTML = `
        <div class="modal-mechanic-item">
            <strong>Atmospheric Humidity Multiplier:</strong> Coastal and riverine humidity levels amplify thermal stress via NOAA Heat Index, driving sustained air conditioning baseload through nighttime hours.
        </div>
        <div class="modal-mechanic-item">
            <strong>Summer 2024 Holdout Validation:</strong> Tested out-of-sample against the historic May–June 2024 heat dome with a predictive MAPE of <strong>${s.holdout_mape.toFixed(2)}%</strong>.
        </div>
        <div class="modal-mechanic-item">
            <strong>Transmission Grid Impact:</strong> Under a +2.0°C warming scenario, ${s.state} adds an estimated <strong>+${Math.round(s.mw_per_c * 2).toLocaleString()} MW</strong> to peak regional demand.
        </div>
    `;

    // Action Button: Focus in Response Curve
    const btnCurve = document.getElementById('modal-btn-view-curve');
    if (btnCurve) {
        btnCurve.onclick = () => {
            const select = document.getElementById('state-select');
            if (select) {
                select.value = s.state;
                updateResponseCurve(s.state);
            }
            closeStateModal();
            const curveCard = document.getElementById('chart-response-curve');
            if (curveCard) {
                curveCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        };
    }

    modal.classList.remove('hidden');
}

function closeStateModal() {
    const modal = document.getElementById('state-modal');
    if (modal) modal.classList.add('hidden');
}

// 11. Event Handlers
function initEventHandlers() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            initSensitivityChart(e.target.dataset.filter);
        });
    });

    const exportBtn = document.getElementById('btn-export-json');
    if (exportBtn) {
        exportBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const blob = new Blob([JSON.stringify(appData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'heat_to_load_web_data.json';
            a.click();
        });
    }
}
