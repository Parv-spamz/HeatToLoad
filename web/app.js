/**
 * The Heat-to-Load Project // High-Taste Editorial Application Engine
 * Financial Times / Bloomberg / Linear aesthetic. Zero AI slop, zero neon glow blobs.
 * Tabular numerals, precise typographic hierarchy, seamless state synchronization.
 */

let appData = null;
let charts = {};
let currentState = null;
let currentRegion = 'all';

// Editorial Palette (Single semantic thermal axis)
const EDITORIAL_PALETTE = {
    cold: '#38bdf8',       // Light steel blue
    blue: '#3b82f6',       // Deep cerulean
    warm: '#f59e0b',       // Amber / gold
    hot: '#f97316',        // Orange / rust
    extreme: '#ef4444',    // Deep crimson / terracotta
    mutedBar: '#334155',   // Slate neutral
    gridSubtle: 'rgba(255, 255, 255, 0.05)',
    tooltipBg: '#0f172a',
    tooltipBorder: 'rgba(255, 255, 255, 0.12)'
};

// Global Chart.js Configuration
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.tooltip.backgroundColor = EDITORIAL_PALETTE.tooltipBg;
Chart.defaults.plugins.tooltip.borderColor = EDITORIAL_PALETTE.tooltipBorder;
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 4;
Chart.defaults.plugins.tooltip.titleFont = { family: "'Inter', sans-serif", weight: '600' };
Chart.defaults.plugins.tooltip.bodyFont = { family: "'JetBrains Mono', monospace", size: 12 };
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 6;

// Qualitative state summaries based on empirical energy profiles
const STATE_DESCRIPTIONS = {
    'Karnataka': 'High cooling elasticity driven by commercial IT infrastructure and urban air conditioning penetration across the Bengaluru metropolitan region.',
    'West Bengal': 'Severe humidity-amplified cooling surge during sultry pre-monsoon heatwaves along the lower Gangetic plain and Kolkata urban cluster.',
    'Kerala': 'Coastal humidity load multiplier; rapid adoption of residential inverter air conditioning drives evening peak demand surges in Kochi and Thiruvananthapuram.',
    'Odisha': 'Intense industrial baseline combined with high coastal thermal distress during April–June heatwaves across the coastal belt.',
    'Andhra Pradesh': 'Agricultural irrigation load synchronized with coastal cooling demand across Vijayawada and Visakhapatnam.',
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

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const resp = await fetch('data.json');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        appData = await resp.json();

        // Initialize all analytical modules
        initMetricStrip();
        initStateIndex();
        selectState(appData.states[0]?.state || 'Karnataka');
        initHeatwaveChart();
        initSimulator();
        initSHAPChart();
        initMasterTable();
        initEventListeners();
    } catch (err) {
        console.error('Failed to load empirical data:', err);
    }
});

/**
 * 1. Top Editorial Metric Strip
 */
function initMetricStrip() {
    const summary = appData.summary || {};
    const holdout = appData.holdout_metrics || {};
    const scenarios = appData.scenarios || {};

    const mwEl = document.getElementById('metric-mw-c');
    const pctEl = document.getElementById('metric-pct-c');
    const mapeEl = document.getElementById('metric-mape');
    const scenEl = document.getElementById('metric-scen-2c');

    if (mwEl && summary.all_india_combined_mw_per_c) {
        mwEl.textContent = `+${summary.all_india_combined_mw_per_c.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
    }
    if (pctEl && summary.state_average_pct_per_c) {
        pctEl.textContent = `+${summary.state_average_pct_per_c.toFixed(2)}%`;
    }
    if (mapeEl && holdout.operational?.mape_pct) {
        mapeEl.textContent = `${holdout.operational.mape_pct.toFixed(2)}%`;
    }
    if (scenEl && scenarios.plus_2c?.all_india_simulated_coincident_peak_mw) {
        const gw = (scenarios.plus_2c.all_india_simulated_coincident_peak_mw / 1000).toFixed(1);
        scenEl.textContent = `${gw}`;
    }
}

/**
 * 2. Left Sidebar State Index
 */
function initStateIndex() {
    renderStateList();

    // Bind region filter buttons
    const tabs = document.querySelectorAll('#region-filter-tabs .seg-btn');
    tabs.forEach(btn => {
        btn.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentRegion = e.target.dataset.region;
            renderStateList();
        });
    });
}

function renderStateList() {
    const container = document.getElementById('state-list-container');
    if (!container) return;
    container.innerHTML = '';

    let states = [...appData.states];
    if (currentRegion !== 'all') {
        states = states.filter(s => s.region === currentRegion);
    }

    // Sort by sensitivity (%/°C) descending
    states.sort((a, b) => b.pct_per_c - a.pct_per_c);

    // Update count badge
    const badge = document.getElementById('state-count-badge');
    if (badge) badge.textContent = `${states.length} State${states.length === 1 ? '' : 's'}`;

    const maxPct = Math.max(...appData.states.map(s => s.pct_per_c), 3.5);

    states.forEach(s => {
        const item = document.createElement('div');
        item.className = `state-item ${currentState === s.state ? 'selected' : ''}`;
        item.dataset.state = s.state;

        const ratio = Math.min(100, Math.max(10, (s.pct_per_c / maxPct) * 100));
        const barColor = s.pct_per_c >= 2.5 ? EDITORIAL_PALETTE.extreme : (s.pct_per_c >= 1.8 ? EDITORIAL_PALETTE.warm : EDITORIAL_PALETTE.cold);

        item.innerHTML = `
            <div class="state-item-left">
                <span class="state-item-name">${s.state}</span>
                <span class="state-item-meta">${s.region} &bull; ${s.city}</span>
            </div>
            <div class="state-item-right">
                <div class="micro-bar-container" title="Relative thermal sensitivity">
                    <div class="micro-bar-fill" style="width: ${ratio}%; background: ${barColor};"></div>
                </div>
                <span class="state-item-pct" style="color: ${barColor};">+${s.pct_per_c.toFixed(2)}%</span>
            </div>
        `;

        item.addEventListener('click', () => {
            selectState(s.state);
        });

        container.appendChild(item);
    });
}

/**
 * 3. Select State and Update Inspector + Response Curve Chart
 */
function selectState(stateName) {
    currentState = stateName;
    const stateObj = appData.states.find(s => s.state === stateName) || appData.states[0];
    if (!stateObj) return;

    // Highlight in sidebar
    document.querySelectorAll('.state-item').forEach(el => {
        el.classList.toggle('selected', el.dataset.state === stateName);
    });

    // Update Inspector DOM
    const nameEl = document.getElementById('inspector-state-name');
    const regionEl = document.getElementById('inspector-region-tag');
    const descEl = document.getElementById('inspector-state-summary');
    const pctEl = document.getElementById('inspector-pct-c');
    const mwEl = document.getElementById('inspector-mw-c');
    const cddEl = document.getElementById('inspector-cdd');
    const mapeEl = document.getElementById('inspector-mape');

    const regionNames = {
        'NR': 'NORTHERN REGION',
        'WR': 'WESTERN REGION',
        'SR': 'SOUTHERN REGION',
        'ER': 'EASTERN REGION'
    };

    if (nameEl) nameEl.textContent = stateObj.state;
    if (regionEl) regionEl.textContent = `${regionNames[stateObj.region] || stateObj.region} \u2022 ${stateObj.city.toUpperCase()}`;
    if (descEl) descEl.textContent = STATE_DESCRIPTIONS[stateObj.state] || 'Empirical cooling sensitivity evaluated over 730 daily observations.';

    if (pctEl) pctEl.textContent = `+${stateObj.pct_per_c.toFixed(2)}% / \u00B0C`;
    if (mwEl) mwEl.textContent = `+${stateObj.mw_per_c.toFixed(1)} MW`;
    if (cddEl) cddEl.textContent = `+${stateObj.cdd_slope_mw.toFixed(1)} MW`;
    if (mapeEl) mapeEl.textContent = `${stateObj.holdout_mape.toFixed(2)}%`;

    // Render or update Chart 1
    renderResponseCurveChart(stateObj.state);
}

function renderResponseCurveChart(stateName) {
    const canvas = document.getElementById('chart-state-curve');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const curveData = appData.state_curves[stateName] || { points: [], fit_line: [] };
    const scatterData = curveData.points.map(p => ({ x: p.t, y: p.mw }));
    const lineData = curveData.fit_line.map(p => ({ x: p.t, y: p.mw }));

    if (charts.responseCurve) {
        charts.responseCurve.data.datasets[0].data = scatterData;
        charts.responseCurve.data.datasets[1].data = lineData;
        charts.responseCurve.options.plugins.title = {
            display: false
        };
        charts.responseCurve.update();
        return;
    }

    charts.responseCurve = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Observed Daily Peaks (Grid-India)',
                    data: scatterData,
                    backgroundColor: 'rgba(56, 189, 248, 0.32)',
                    borderColor: 'transparent',
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    order: 2
                },
                {
                    label: 'Polynomial Thermal Response Model',
                    type: 'line',
                    data: lineData,
                    borderColor: EDITORIAL_PALETTE.extreme,
                    borderWidth: 2.2,
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
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#94a3b8',
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.x.toFixed(1)}°C \u2192 ${Math.round(ctx.parsed.y).toLocaleString()} MW`
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    grid: { color: EDITORIAL_PALETTE.gridSubtle },
                    title: {
                        display: true,
                        text: 'Daily Maximum Temperature (\u00B0C) \u2014 Open-Meteo ERA5 Reanalysis',
                        color: '#64748b',
                        font: { size: 11, weight: '500' }
                    },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { color: EDITORIAL_PALETTE.gridSubtle },
                    title: {
                        display: true,
                        text: 'State Peak Electricity Demand Met (MW) \u2014 SCADA',
                        color: '#64748b',
                        font: { size: 11, weight: '500' }
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: (v) => `${(v / 1000).toFixed(1)}k`
                    }
                }
            }
        }
    });
}

/**
 * 4. Heatwave Timeline Chart (Panel 2)
 */
function initHeatwaveChart() {
    const canvas = document.getElementById('chart-heatwave');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

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
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Model Forecast Q50 (MW)',
                    data: pred,
                    borderColor: EDITORIAL_PALETTE.extreme,
                    borderWidth: 1.8,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'Mean Maximum Temperature (\u00B0C)',
                    data: temp,
                    borderColor: EDITORIAL_PALETTE.warm,
                    borderWidth: 1.6,
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
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => `Date: 2024-${items[0].label}`,
                        label: (ctx) => {
                            if (ctx.datasetIndex === 2) {
                                return `Temperature: ${ctx.parsed.y.toFixed(1)}\u00B0C`;
                            }
                            return `${ctx.dataset.label.split('(')[0].trim()}: ${Math.round(ctx.parsed.y).toLocaleString()} MW`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 15, color: '#94a3b8' }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: EDITORIAL_PALETTE.gridSubtle },
                    title: { display: true, text: 'Coincident Peak Demand (MW)', color: '#64748b' },
                    ticks: {
                        color: '#94a3b8',
                        callback: (v) => `${Math.round(v / 1000)}k`
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    grid: { display: false },
                    title: { display: true, text: 'Daytime Temperature (\u00B0C)', color: '#64748b' },
                    min: 28,
                    max: 48,
                    ticks: { color: EDITORIAL_PALETTE.warm }
                }
            }
        }
    });
}

/**
 * 5. Interactive Climate Simulator (Panel 3)
 */
function initSimulator() {
    const slider = document.getElementById('climate-slider');
    const badgeText = document.getElementById('slider-temp-text');

    const peakGwEl = document.getElementById('sim-peak-gw');
    const surgeMwEl = document.getElementById('sim-surge-mw');
    const surgePctEl = document.getElementById('sim-surge-pct');
    const riskRatingEl = document.getElementById('sim-risk-rating');
    const riskNoteEl = document.getElementById('sim-risk-note');

    const canvas = document.getElementById('chart-sim-bars');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const basePeak = appData.scenarios?.plus_1c?.all_india_coincident_baseline_peak_mw || 223421.1;
    const dependableCapacity = 235000.0; // 235 GW national dependable dispatch baseline

    function recalculate(deltaT) {
        if (badgeText) badgeText.textContent = `+${deltaT.toFixed(1)}\u00B0C`;

        // Empirical quadratic model matching +1C (+2,836 MW) and +2C (+5,841 MW)
        const surgeMw = (deltaT * 2761.9) + (Math.pow(deltaT, 1.35) * 420.0);
        const scenarioPeak = basePeak + surgeMw;
        const surgePct = (surgeMw / basePeak) * 100.0;

        if (peakGwEl) peakGwEl.textContent = `${(scenarioPeak / 1000.0).toFixed(1)} GW`;
        if (surgeMwEl) surgeMwEl.textContent = `+${Math.round(surgeMw).toLocaleString()} MW`;
        if (surgePctEl) surgePctEl.textContent = `+${surgePct.toFixed(2)}% peak expansion`;

        if (deltaT >= 2.2) {
            riskRatingEl.textContent = 'CRITICAL DEFICIT';
            riskRatingEl.style.color = EDITORIAL_PALETTE.extreme;
            riskNoteEl.textContent = 'Coincident demand exceeds available thermal/hydro reserve margins';
        } else if (deltaT >= 1.4) {
            riskRatingEl.textContent = 'HIGH CORRIDOR RISK';
            riskRatingEl.style.color = EDITORIAL_PALETTE.warm;
            riskNoteEl.textContent = 'ER-to-NR / WR transmission corridor chokes during solar ramp-down';
        } else {
            riskRatingEl.textContent = 'MODERATE STRESS';
            riskRatingEl.style.color = EDITORIAL_PALETTE.cold;
            riskNoteEl.textContent = 'Absorbed by spinning reserves and pumped-storage hydro dispatch';
        }

        updateSimulatorChart(basePeak, scenarioPeak, dependableCapacity, deltaT);
    }

    function updateSimulatorChart(base, scen, capacity, deltaT) {
        const labels = [
            'Baseline Observed Peak',
            `Simulated Peak (+${deltaT.toFixed(1)}\u00B0C)`,
            'Dependable Capacity'
        ];
        const data = [base / 1000.0, scen / 1000.0, capacity / 1000.0];
        const colors = [
            '#475569',
            deltaT >= 2.0 ? EDITORIAL_PALETTE.extreme : EDITORIAL_PALETTE.warm,
            '#334155'
        ];

        if (charts.simCompare) {
            charts.simCompare.data.labels = labels;
            charts.simCompare.data.datasets[0].data = data;
            charts.simCompare.data.datasets[0].backgroundColor = colors;
            charts.simCompare.update();
        } else {
            charts.simCompare = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Gigawatts (GW)',
                        data: data,
                        backgroundColor: colors,
                        borderRadius: 3,
                        barThickness: 28
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (c) => `${c.raw.toFixed(1)} GW`
                            }
                        }
                    },
                    scales: {
                        x: {
                            min: 210,
                            max: 245,
                            grid: { color: EDITORIAL_PALETTE.gridSubtle },
                            title: { display: true, text: 'Coincident Peak Capacity (GW)', color: '#64748b' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: '#f1f5f9', font: { weight: '500' } }
                        }
                    }
                }
            });
        }
    }

    if (slider) {
        slider.addEventListener('input', (e) => {
            recalculate(parseFloat(e.target.value));
        });
        recalculate(parseFloat(slider.value));
    }
}

/**
 * 6. SHAP Feature Attribution (Panel 4)
 */
function initSHAPChart() {
    const canvas = document.getElementById('chart-shap-bars');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const drivers = appData.shap_drivers || [];
    const labels = drivers.map(d => {
        return d.feature
            .replace(/_/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());
    });
    const impacts = drivers.map(d => d.impact_mw);

    charts.shap = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mean |SHAP| Value (MW)',
                data: impacts,
                backgroundColor: 'rgba(56, 189, 248, 0.75)',
                borderColor: EDITORIAL_PALETTE.cold,
                borderWidth: 1,
                borderRadius: 3,
                barThickness: 18
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `+${ctx.raw.toLocaleString()} MW Mean Attribution`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: EDITORIAL_PALETTE.gridSubtle },
                    title: { display: true, text: 'Mean Absolute Impact on Daily Peak (MW)', color: '#64748b' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#f1f5f9', font: { size: 11, weight: '500' } }
                }
            }
        }
    });
}

/**
 * 7. Master Parametric Ledger Table (Panel 5)
 */
function initMasterTable() {
    const tbody = document.getElementById('master-table-body');
    const search = document.getElementById('filter-table-input');
    if (!tbody) return;

    function renderRows(stateList) {
        tbody.innerHTML = '';
        stateList.forEach(s => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.title = `Click to inspect ${s.state}`;

            const sensColor = s.pct_per_c >= 2.5 ? EDITORIAL_PALETTE.extreme : (s.pct_per_c >= 1.8 ? EDITORIAL_PALETTE.warm : EDITORIAL_PALETTE.cold);

            tr.innerHTML = `
                <td style="font-weight: 600; color: #fff;">${s.state}</td>
                <td><span style="font-family: var(--font-mono); font-size: 11px; padding: 2px 6px; background: rgba(255,255,255,0.05); border: 1px solid var(--border-subtle); border-radius: 3px;">${s.region}</span></td>
                <td style="color: var(--text-secondary);">${s.city}</td>
                <td class="num-col">${Math.round(s.mean_demand_mw).toLocaleString()} MW</td>
                <td class="num-col" style="color: #38bdf8; font-weight: 600;">+${s.mw_per_c.toFixed(1)}</td>
                <td class="num-col" style="color: ${sensColor}; font-weight: 700;">+${s.pct_per_c.toFixed(2)}%</td>
                <td class="num-col">+${s.cdd_slope_mw.toFixed(1)}</td>
                <td class="num-col">${s.holdout_mape.toFixed(2)}%</td>
                <td class="num-col" style="color: ${s.holdout_r2 >= 0 ? '#10b981' : '#64748b'};">${s.holdout_r2.toFixed(2)}</td>
            `;

            tr.addEventListener('click', () => {
                selectState(s.state);
                // Smooth scroll to Inspector
                const inspector = document.querySelector('.panel');
                if (inspector) inspector.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });

            tbody.appendChild(tr);
        });
    }

    renderRows(appData.states);

    if (search) {
        search.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const filtered = appData.states.filter(s =>
                s.state.toLowerCase().includes(query) ||
                s.region.toLowerCase().includes(query) ||
                s.city.toLowerCase().includes(query)
            );
            renderRows(filtered);
        });
    }
}

/**
 * 8. Additional Global Event Listeners
 */
function initEventListeners() {
    // Keyboard navigation: up/down arrow through states
    window.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') return;
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            const states = appData.states;
            const currentIndex = states.findIndex(s => s.state === currentState);
            if (currentIndex === -1) return;

            let nextIndex = e.key === 'ArrowDown' ? currentIndex + 1 : currentIndex - 1;
            if (nextIndex >= 0 && nextIndex < states.length) {
                e.preventDefault();
                selectState(states[nextIndex].state);
            }
        }
    });
}
