/**
 * Heat To Load // Frontend Application Engine
 * Drives interactive Chart.js visualizations, climate slider simulator, and dynamic data filtering.
 */

let appData = null;
let charts = {};

// Color Palette
const COLORS = {
    cyan: '#00f2fe',
    blue: '#4facfe',
    amber: '#f59e0b',
    rose: '#f43f5e',
    orange: '#fb923c',
    emerald: '#10b981',
    purple: '#8b5cf6',
    slate: '#94a3b8',
    gridLines: 'rgba(255, 255, 255, 0.05)',
    tooltipBg: 'rgba(16, 23, 38, 0.95)'
};

// Global Chart.js Defaults
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.plugins.tooltip.backgroundColor = COLORS.tooltipBg;
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.15)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.legend.labels.usePointStyle = true;

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
        document.getElementById('kpi-mw-c').innerHTML = `+${summary.all_india_combined_mw_per_c.toLocaleString()} <span class="kpi-unit">MW / °C</span>`;
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
    select.innerHTML = '';
    appData.states.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.state;
        opt.textContent = `${s.state} (${s.region}) - +${s.pct_per_c.toFixed(2)}%/°C`;
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

    const bgColors = dataPct.map(v => v > 2.5 ? COLORS.rose : v > 1.5 ? COLORS.amber : COLORS.blue);

    if (charts.sensitivity) charts.sensitivity.destroy();

    charts.sensitivity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sensitivity (%/°C)',
                data: dataPct,
                backgroundColor: bgColors,
                borderRadius: 4,
                borderSkipped: false
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
                        label: (ctx) => `+${ctx.raw.toFixed(2)}% per °C`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: '% Increase per °C above baseline' }
                },
                y: {
                    grid: { display: false }
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
                    label: 'Daily Observations',
                    data: scatterData,
                    backgroundColor: 'rgba(79, 172, 254, 0.45)',
                    borderColor: 'transparent',
                    pointRadius: 3.5,
                    order: 2
                },
                {
                    label: 'Polynomial Thermal Response',
                    type: 'line',
                    data: lineData,
                    borderColor: COLORS.rose,
                    borderWidth: 2.5,
                    pointRadius: 0,
                    tension: 0.2,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.x}°C → ${ctx.parsed.y.toLocaleString()} MW`
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Daily Maximum Temperature (°C)' }
                },
                y: {
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Peak Electricity Demand (MW)' }
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
    charts.responseCurve.update();
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
                    label: 'Actual Coincident Peak Met (MW)',
                    data: actual,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    borderWidth: 2.2,
                    pointRadius: 2.5,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Model Q50 Forecast (MW)',
                    data: pred,
                    borderColor: COLORS.rose,
                    borderWidth: 1.8,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'Daily Max Temp (°C)',
                    data: temp,
                    borderColor: COLORS.amber,
                    borderWidth: 2,
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
                    ticks: { maxTicksLimit: 20 }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Coincident Peak Demand (MW)' }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    grid: { display: false },
                    title: { display: true, text: 'Max Temperature (°C)' },
                    min: 28,
                    max: 48
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

    function recalculate(deltaT) {
        badge.textContent = `+${deltaT.toFixed(1)}°C`;
        
        // Non-linear scaling model derived from +1C and +2C simulations
        // Linear elasticity ~ +2,761.9 MW/C with slight second-order curvature
        const surgeMw = (deltaT * 2761.9) + (deltaT ** 1.35 * 420.0);
        const scenarioPeak = basePeak + surgeMw;
        const surgePct = (surgeMw / basePeak) * 100.0;

        peakGwEl.textContent = `${(scenarioPeak / 1000.0).toFixed(1)} GW`;
        surgeMwEl.textContent = `+${Math.round(surgeMw).toLocaleString()} MW`;
        surgePctEl.textContent = `+${surgePct.toFixed(2)}%`;

        if (deltaT >= 2.2) {
            riskLevelEl.textContent = 'CRITICAL DEFICIT';
            riskLevelEl.className = 'sim-val text-rose';
        } else if (deltaT >= 1.4) {
            riskLevelEl.textContent = 'HIGH CORRIDOR RISK';
            riskLevelEl.className = 'sim-val text-amber';
        } else {
            riskLevelEl.textContent = 'MODERATE STRESS';
            riskLevelEl.className = 'sim-val text-cyan';
        }

        updateSimChart(basePeak, scenarioPeak, deltaT);
    }

    function updateSimChart(base, scen, deltaT) {
        const labels = ['Baseline (Observed)', `Simulated (+${deltaT.toFixed(1)}°C)`];
        const data = [base / 1000.0, scen / 1000.0];
        const colors = ['#34495e', deltaT >= 2.0 ? COLORS.rose : COLORS.amber];

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
                        label: 'Coincident Peak (GW)',
                        data: data,
                        backgroundColor: colors,
                        borderRadius: 6,
                        barThickness: 50
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
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
                            title: { display: true, text: 'Gigawatts (GW)' }
                        },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    }

    slider.addEventListener('input', (e) => {
        recalculate(parseFloat(e.target.value));
    });

    recalculate(1.5);
}

// 7. Chart 5: SHAP Attribution
function initSHAPChart() {
    const ctx = document.getElementById('chart-shap').getContext('2d');
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
                backgroundColor: 'rgba(139, 92, 246, 0.75)',
                borderColor: COLORS.purple,
                borderWidth: 1,
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
                    callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()} MW Impact` }
                }
            },
            scales: {
                x: {
                    grid: { color: COLORS.gridLines },
                    title: { display: true, text: 'Mean Absolute Impact on Peak (MW)' }
                },
                y: { grid: { display: false } }
            }
        }
    });
}

// 8. Data League Table
function initTable() {
    const tbody = document.getElementById('states-table-body');
    const search = document.getElementById('state-search');

    function renderRows(items) {
        tbody.innerHTML = '';
        items.forEach(s => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="state-badge">${s.state}</td>
                <td><span class="region-pill region-${s.region}">${s.region}</span></td>
                <td>${s.city}</td>
                <td>${Math.round(s.mean_demand_mw).toLocaleString()}</td>
                <td style="color: ${s.mw_per_c > 0 ? '#34d399' : '#94a3b8'}; font-weight: 600;">+${s.mw_per_c.toFixed(1)}</td>
                <td style="color: ${s.pct_per_c > 2.0 ? '#f43f5e' : '#38bdf8'}; font-weight: 700;">+${s.pct_per_c.toFixed(2)}%</td>
                <td>+${s.cdd_slope_mw.toFixed(1)}</td>
                <td>${s.holdout_mape.toFixed(2)}%</td>
                <td>${s.holdout_r2.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    renderRows(appData.states);

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

// 9. Event Handlers
function initEventHandlers() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            initSensitivityChart(e.target.dataset.filter);
        });
    });

    document.getElementById('btn-export-json').addEventListener('click', (e) => {
        e.preventDefault();
        const blob = new Blob([JSON.stringify(appData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'heat_to_load_web_data.json';
        a.click();
    });
}
