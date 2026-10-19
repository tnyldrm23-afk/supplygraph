'use strict';
const $ = id => document.getElementById(id);
const state = { organizations: [], products: [], graph: null, overview: null, scenario: null, allProducts: false, view: 'overview' };
const fmt = (value, digits = 1) => new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const orgName = id => state.organizations.find(o => o.id === id)?.name || id;
const plural = (n, word, many = word + 's') => `${fmt(n, 0)} ${n === 1 ? word : many}`;
function error(message) { $('global-error').textContent = message; $('global-error').hidden = !message; }
async function api(path, options = {}) {
  const response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail));
  return payload.data ?? payload;
}
function option(select, value, label) { const item = document.createElement('option'); item.value = value; item.textContent = label; select.append(item); }
function evidenceTag(value) { return `<span class="evidence-tag ${value === 'observed' ? 'observed' : 'assumed'}">${esc(value)}</span>`; }
function showMethod() { $('method-dialog').showModal(); }
['method-button', 'notice-method'].forEach(id => $(id).addEventListener('click', showMethod));
$('close-method').addEventListener('click', () => $('method-dialog').close());
$('method-dialog').addEventListener('click', event => { if (event.target === $('method-dialog')) { const box = event.target.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) event.target.close(); } });

/* Network map */
function svgElement(tag, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs || {}).forEach(([key, value]) => el.setAttribute(key, value));
  if (text !== undefined) el.textContent = text;
  return el;
}
// [stage colour, plural heading]
const kindStyle = {
  supplier: ['#3d5f8f', 'Suppliers'],
  manufacturer: ['#8a5f2e', 'Manufacturers'],
  distributor: ['#5d7046', 'Distributors'],
  retailer: ['#7a4e7a', 'Retailers']
};
const CARD = { width: 196, height: 64, column: 262, top: 56, gap: 82 };
function selectFacility(id) {
  $('supplier-select').value = id;
  facilityInfo();
  renderGraph();
}
function graphView() {
  return $('graph-wrap').dataset.mode === 'auto'
    ? (window.matchMedia('(max-width: 760px)').matches ? 'list' : 'map')
    : $('graph-wrap').dataset.mode;
}
function syncGraphView() {
  document.querySelectorAll('[data-network-view]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.networkView === graphView()));
  });
}
document.querySelectorAll('[data-network-view]').forEach(button => {
  button.addEventListener('click', () => {
    $('graph-wrap').dataset.mode = button.dataset.networkView;
    syncGraphView();
  });
});
window.matchMedia('(max-width: 760px)').addEventListener('change', syncGraphView);
function scenarioSets() {
  const active = (state.scenario?.scenario.reduction || 0) > 0;
  return {
    failures: new Set(active ? state.scenario.scenario.supplier_ids : []),
    exposed: new Set(active ? state.scenario.exposed_organizations.map(n => n.id) : []),
    active,
    backups: state.scenario?.scenario.activate_backups || false
  };
}
function renderGraph() {
  if (!state.graph) return;
  const svg = $('network-graph');
  svg.replaceChildren();
  const { failures, exposed, active, backups } = scenarioSets();
  const selectedId = $('supplier-select').value;
  const positions = {};
  Object.entries(kindStyle).forEach(([kind, [color, heading]], col) => {
    const nodes = state.graph.nodes.filter(n => n.kind === kind);
    const x = 30 + col * CARD.column;
    svg.append(svgElement('text', {x, y: 26, fill: color, 'font-size': 13, 'font-weight': 650}, heading));
    svg.append(svgElement('text', {x: x + CARD.width, y: 26, fill: '#6a6e75', 'font-size': 12, 'text-anchor': 'end'}, String(nodes.length)));
    svg.append(svgElement('line', {x1: x, x2: x + CARD.width, y1: 37, y2: 37, stroke: '#e4e0d7'}));
    const offset = (4 - nodes.length) * CARD.gap / 2;
    nodes.forEach((node, index) => { positions[node.id] = {x, y: CARD.top + offset + index * CARD.gap}; });
  });
  state.graph.edges.forEach(edge => {
    const from = positions[edge.origin], to = positions[edge.destination];
    if (!from || !to) return;
    let cls = 'edge' + (edge.backup ? ' backup' : '');
    if (edge.backup && backups) cls += ' active';
    if (active) {
      if (failures.has(edge.origin) || failures.has(edge.destination)) cls += ' failed';
      else if (exposed.has(edge.origin) && !edge.backup) cls += ' affected';
      else if (!edge.backup) cls += ' faded';
    }
    const x1 = from.x + CARD.width, y1 = from.y + CARD.height / 2, x2 = to.x, y2 = to.y + CARD.height / 2;
    const bend = Math.max(24, (x2 - x1) * .5);
    const path = svgElement('path', {d: `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`, class: cls});
    path.append(svgElement('title', {}, `${orgName(edge.origin)} → ${orgName(edge.destination)} · ${edge.product_count} products · ${edge.backup ? 'backup' : 'primary'} lane (assumed)`));
    svg.append(path);
  });
  state.graph.nodes.forEach(node => {
    const pos = positions[node.id], [color] = kindStyle[node.kind];
    const failed = failures.has(node.id), affected = !failed && exposed.has(node.id);
    const selected = selectedId === node.id;
    const location = state.graph.locations.find(l => l.id === node.location_id);
    const detail = failed ? `Disrupted · −${Math.round(state.scenario.scenario.reduction * 100)}% capacity`
      : affected ? `Downstream · ${location?.name || node.id}` : `${location?.name || ''} · ${node.id}`;
    const group = svgElement('g', {class: 'node', transform: `translate(${pos.x},${pos.y})`, tabindex: 0, role: 'button', 'aria-label': `${node.name}, ${node.kind}, ${detail}. Select for scenario.`, 'aria-pressed': String(selected)});
    group.append(svgElement('rect', {class: 'node-card', width: CARD.width, height: CARD.height, rx: 7,
      fill: failed ? '#f8e6e2' : affected ? '#fbf3e4' : '#fff',
      stroke: selected ? '#1e5b57' : failed ? '#dfa79c' : affected ? '#e2c48f' : '#d8d3c8',
      'stroke-width': selected ? 2 : 1}));
    group.append(svgElement('rect', {x: 10, y: 12, width: 3, height: CARD.height - 24, rx: 1.5, fill: failed ? '#b23a2b' : color}));
    group.append(svgElement('text', {x: 22, y: 28, fill: '#1d1f22', 'font-size': 13.5, 'font-weight': 600}, node.name));
    group.append(svgElement('text', {x: 22, y: 47, fill: failed ? '#b23a2b' : affected ? '#8a560a' : '#6a6e75', 'font-size': 12, 'font-weight': failed || affected ? 600 : 400}, detail));
    group.addEventListener('click', () => selectFacility(node.id));
    group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectFacility(node.id); } });
    svg.append(group);
  });
  renderFacilityList(failures, exposed, selectedId);
  syncGraphView();
  renderOverviewMap(state.animateRipple);
  state.animateRipple = false;
}
function renderFacilityList(failures, exposed, selectedId) {
  const list = $('network-list');
  list.replaceChildren();
  Object.entries(kindStyle).forEach(([kind, [color, heading]]) => {
    const nodes = state.graph.nodes.filter(n => n.kind === kind);
    const section = document.createElement('section');
    section.className = 'facility-group';
    section.innerHTML = `<h3>${esc(heading)}<span>${nodes.length}</span></h3>`;
    nodes.forEach(node => {
      const failed = failures.has(node.id), affected = !failed && exposed.has(node.id), selected = selectedId === node.id;
      const location = state.graph.locations.find(l => l.id === node.location_id);
      const note = failed ? ' · Disrupted' : affected ? ' · Downstream' : selected ? ' · Selected' : '';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'facility-item' + (selected ? ' selected' : '') + (failed ? ' failed' : '') + (affected ? ' affected' : '');
      button.setAttribute('aria-pressed', String(selected));
      button.setAttribute('aria-label', `${node.name}, ${node.kind}${note}. Select for scenario.`);
      button.innerHTML = `<span class="facility-dot" style="background:${failed ? '#b23a2b' : color}" aria-hidden="true"></span><span><strong>${esc(node.name)}</strong><small>${esc(location?.name || node.id)} · ${esc(node.id)}${note}</small></span>`;
      button.addEventListener('click', () => selectFacility(node.id));
      section.append(button);
    });
    list.append(section);
  });
}

/* World map: drawing lives in geo.js, shared with the scroll story */
const reducedMotion = SupplyGeo.reducedMotion;
function drawGeo(svg, options) {
  if (!state.graph) return;
  SupplyGeo.draw(svg, {graph: state.graph, organizations: state.organizations}, options);
}
function renderOverviewMap(animate = false) {
  const { failures, exposed, active, backups } = scenarioSets();
  const hops = Object.fromEntries((state.scenario?.exposed_organizations || []).map(o => [o.id, o.hops]));
  const step = 420;
  drawGeo($('geo-map'), {
    animate,
    selected: $('supplier-select').value,
    onSelect: selectFacility,
    edges: state.graph.edges.map(edge => {
      let cls = '', flow = !edge.backup || backups;
      if (active) {
        if (failures.has(edge.origin) || failures.has(edge.destination)) { cls = 'failed'; flow = false; }
        else if (exposed.has(edge.origin) && !edge.backup) cls = 'affected';
        else if (!edge.backup) cls = 'faded';
      }
      return {...edge, cls, flow, delay: ((hops[edge.origin] ?? 0) + .5) * step};
    }),
    node: id => {
      if (!active) return {};
      if (failures.has(id)) return {cls: 'failed', delay: 0, note: 'disrupted'};
      if (exposed.has(id)) return {cls: 'affected', delay: (hops[id] ?? 1) * step, note: `downstream, ${hops[id]} hop${hops[id] === 1 ? '' : 's'} away`};
      return {};
    }
  });
}
function animateNumber(id, value, digits = 1) {
  const el = $(id), from = Number(el.dataset.value || 0);
  el.dataset.value = value;
  if (reducedMotion.matches || from === value) { el.textContent = fmt(value, digits); return; }
  const start = performance.now(), duration = 800;
  const tick = now => {
    const t = Math.min(1, (now - start) / duration), eased = 1 - Math.pow(1 - t, 3);
    el.textContent = fmt(from + (value - from) * eased, digits);
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* Scenario */
function updateServiceTrack(value) {
  $('service-spark').style.width = Math.max(0, Math.min(100, value)) + '%';
}
function facilityInfo() {
  const organization = state.organizations.find(o => o.id === $('supplier-select').value);
  const location = state.graph?.locations.find(l => l.id === organization?.location_id);
  $('facility-info').textContent = organization
    ? `${organization.kind[0].toUpperCase() + organization.kind.slice(1)} in ${location?.name ? location.name + ', ' : ''}${location?.country || ''} · ${organization.id}. You can also click a facility on the map.`
    : '';
}
function baseline() {
  state.scenario = null; state.allProducts = false;
  animateNumber('metric-service', state.overview.baseline_service_level);
  updateServiceTrack(state.overview.baseline_service_level);
  animateNumber('metric-products', 0, 0); animateNumber('metric-loss', 0); animateNumber('metric-recovery', 0);
  $('stage-caption').textContent = 'Baseline: goods moving on every primary lane'; $('stage-caption').className = '';
  $('service-change').textContent = 'Baseline, no disruption'; $('service-change').className = 'neutral';
  $('product-change').textContent = 'No disruption applied'; $('product-change').className = 'neutral';
  $('loss-change').textContent = `All ${fmt(state.overview.daily_demand)} units/day delivered`;
  $('scenario-result').hidden = true; $('impact-count').textContent = 'No scenario';
  $('impact-subtitle').textContent = 'Run a simulation to see which products lose supply.';
  $('impact-table').innerHTML = '<tr><td colspan="5" class="table-empty">Nothing simulated yet. Choose a facility and press Run simulation.</td></tr>';
  $('table-count').textContent = 'Units per day. Each product has its own capacity, so nothing is double-counted.';
  $('graph-caption').textContent = 'Baseline: every lane available';
  $('bar-scenario').style.width = '100%'; $('bar-recovery').style.width = '100%';
  $('bar-scenario-value').textContent = '100%'; $('bar-recovery-value').textContent = '100%';
  $('recovery-heading').textContent = 'How much can backups win back?';
  $('recovery-copy').textContent = 'Run a disruption, then compare it with reserve contracts switched on.';
  $('all-products-button').hidden = true; $('all-products-button').textContent = 'Show all products';
  renderGraph();
}
async function runScenario(event) {
  event?.preventDefault(); error('');
  const button = $('run-button'); button.disabled = true; button.textContent = 'Calculating…';
  try {
    const body = {supplier_ids: [$('supplier-select').value], reduction: Number($('reduction').value) / 100, depth: Number($('depth').value), activate_backups: $('backups').checked, sku: $('graph-product').value || null};
    state.scenario = await api('/scenarios', {method: 'POST', body: JSON.stringify(body)});
    renderScenario();
  } catch (err) { error(err.message); }
  finally { button.disabled = false; button.textContent = 'Run simulation'; }
}
function renderScenario() {
  const s = state.scenario, t = s.totals;
  const name = orgName(s.scenario.supplier_ids[0]), pct = Math.round(s.scenario.reduction * 100);
  animateNumber('metric-service', t.service_level); updateServiceTrack(t.service_level);
  animateNumber('metric-products', s.affected_products, 0);
  $('metric-product-total').textContent = '/ ' + s.products.length;
  animateNumber('metric-loss', t.unmet_demand); animateNumber('metric-recovery', t.restored_with_backups);
  const downstream = s.exposed_organizations.filter(o => o.hops > 0).length;
  $('stage-caption').textContent = pct === 0 ? `${name} at full capacity: nothing changes` : `${name} loses ${pct}% of capacity. The shortfall reaches ${plural(downstream, 'facility', 'facilities')} downstream`;
  $('stage-caption').className = pct > 0 ? 'alert' : '';
  const delta = t.service_level - t.baseline_service_level;
  $('service-change').textContent = delta === 0 ? 'Unchanged from baseline' : `${delta > 0 ? '+' : '−'}${fmt(Math.abs(delta))} points vs baseline`;
  $('service-change').className = delta < 0 ? 'negative' : 'positive';
  $('product-change').textContent = s.affected_retailers ? `${plural(s.affected_retailers, 'retailer')} lose supply` : 'No retailer loses supply';
  $('product-change').className = s.affected_retailers ? 'negative' : 'positive';
  $('loss-change').textContent = `${fmt(t.scenario_delivered)} of ${fmt(t.demand)} units/day delivered`;
  $('graph-caption').textContent = `${name} at ${100 - pct}% capacity${s.scenario.activate_backups ? ' · backups on' : ''}`;
  $('impact-count').textContent = `${s.affected_products} affected`;
  $('impact-subtitle').textContent = 'Daily units reaching retailers, before and after the disruption.';
  const result = $('scenario-result');
  result.hidden = false;
  result.className = 'scenario-result' + (s.affected_products === 0 ? ' recovered' : '');
  result.innerHTML = `<p class="result-title">${esc(name)} loses ${pct}% of capacity</p><p>${plural(s.affected_products, 'product')} affected · ${fmt(t.unmet_demand)} units/day unmet. ${plural(s.exposed_organizations.filter(o => o.hops > 0).length, 'facility', 'facilities')} downstream.${s.traversal_truncated ? ' Exposure depth limit reached.' : ''}</p><a href="#product-impact">See product impact ↓</a>`;
  const recovery = Math.min(100, 100 * (t.scenario_delivered + t.restored_with_backups) / t.demand);
  $('bar-scenario').style.width = t.service_level + '%'; $('bar-scenario-value').textContent = fmt(t.service_level, 0) + '%';
  $('bar-recovery').style.width = recovery + '%'; $('bar-recovery-value').textContent = fmt(recovery, 0) + '%';
  $('recovery-heading').textContent = t.restored_with_backups > 0 ? `Backups win back ${fmt(t.restored_with_backups)} units/day.` : 'Backups cannot close this gap.';
  $('recovery-copy').textContent = t.restored_with_backups > 0
    ? 'Reserve contracts recover part of the shortfall, not all of it. Compare both runs before choosing a mitigation.'
    : s.scenario.activate_backups ? 'Reserve contracts are already on. The remaining shortage needs new capacity or another route.'
      : 'No reserve contract helps here. Check the affected products for single-source dependencies.';
  state.animateRipple = true;
  renderImpactTable(); renderGraph();
}
function keptBar(share) {
  const value = Math.max(0, Math.min(100, share));
  return `<div class="kept${value === 0 ? ' zero' : ''}" aria-label="${fmt(value, 0)}% still delivered"><b><i style="width:${value}%"></i></b><span>${fmt(value, 0)}%</span></div>`;
}
function renderImpactTable() {
  const rows = state.scenario?.products || [];
  const selected = state.allProducts ? rows : rows.slice(0, 8);
  $('impact-table').innerHTML = selected.map(p => `<tr><td><div class="product-name">${esc(p.name)}</div><small>${esc(p.sku)}</small></td><td class="num">${fmt(p.baseline_delivered)}</td><td class="num">${fmt(p.scenario_delivered)}</td><td class="num ${p.lost_units > 0 ? 'negative' : 'neutral'}">${p.lost_units > 0 ? '−' + fmt(p.lost_units) : '0'}</td><td>${keptBar(p.baseline_delivered ? 100 * p.scenario_delivered / p.baseline_delivered : 100)}</td></tr>`).join('')
    || '<tr><td colspan="5" class="table-empty">No products in this scenario.</td></tr>';
  $('table-count').textContent = `Showing ${selected.length} of ${rows.length} products · units per day`;
  $('all-products-button').hidden = rows.length <= 8;
}
$('scenario-form').addEventListener('submit', runScenario);
$('reduction').addEventListener('input', () => { $('reduction-value').textContent = $('reduction').value + '%'; });
$('supplier-select').addEventListener('change', () => { facilityInfo(); renderGraph(); });
$('baseline-button').addEventListener('click', () => { error(''); baseline(); });
$('reset-graph').addEventListener('click', async () => { $('graph-product').value = ''; await filterGraph(); baseline(); });
$('graph-product').addEventListener('change', filterGraph);
async function filterGraph() {
  try {
    state.graph = await api('/graph' + ($('graph-product').value ? '?sku=' + encodeURIComponent($('graph-product').value) : ''));
    state.scenario = null; baseline();
    $('metric-product-total').textContent = '/ ' + ($('graph-product').value ? '1' : state.products.length);
    facilityInfo();
  } catch (err) { error(err.message); }
}
$('all-products-button').addEventListener('click', () => {
  if (!state.scenario) return;
  state.allProducts = !state.allProducts;
  $('all-products-button').textContent = state.allProducts ? 'Show fewer' : 'Show all products';
  renderImpactTable();
});
$('recovery-button').addEventListener('click', () => { $('backups').checked = true; runScenario(); });
$('export-button').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(state.scenario || {baseline: state.overview, evidence: 'No disruption applied'}, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = `supplygraph-${state.scenario?.scenario_id || 'baseline'}.json`; anchor.click();
  URL.revokeObjectURL(url);
});

/* Views */
const viewTitles = {overview: 'Disruption simulator', trace: 'Products', analytics: 'Network analysis', assistant: 'Ask the graph'};
async function changeView(view) {
  state.view = view; error('');
  document.querySelectorAll('.view').forEach(el => { el.hidden = el.id !== 'view-' + view; });
  document.querySelectorAll('.nav').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
    if (el.dataset.view === view) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current');
  });
  document.title = `SupplyGraph · ${viewTitles[view]}`;
  window.scrollTo({top: 0});
  try {
    if (view === 'trace') await Promise.all([loadTrace(), loadOrders()]);
    if (view === 'analytics') await loadAnalytics();
    if (view === 'assistant') await checkLLM();
  } catch (err) { error(err.message); }
}
document.querySelectorAll('.nav').forEach(button => button.addEventListener('click', () => changeView(button.dataset.view)));

async function loadTrace() {
  const sku = $('trace-product').value; if (!sku) return;
  const response = await fetch('/api/products/' + encodeURIComponent(sku) + '/provenance');
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail);
  const product = state.products.find(p => p.id === sku);
  $('trace-summary').innerHTML = `<div><strong>${fmt(product.historical_units, 0)}</strong><span>units sold in the source data ${evidenceTag('observed')}</span></div><div><strong>${fmt(product.daily_demand)}</strong><span>average demand, units/day ${evidenceTag('observed')}</span></div><div><strong>${payload.data.length}</strong><span>supply lanes carry it ${evidenceTag('assumed')}</span></div>`;
  $('trace-table').innerHTML = payload.data.map(l => `<tr><td><span class="mono">${esc(l.id)}</span><small>${l.backup ? 'Backup' : 'Primary'} contract</small></td><td>${esc(orgName(l.origin))} → ${esc(orgName(l.destination))}</td><td class="num">${fmt(l.capacity)}</td><td class="num">${plural(l.lead_days, 'day')}</td><td>${evidenceTag(l.provenance)}</td></tr>`).join('');
  $('trace-query').textContent = payload.evidence.cypher;
  const involved = new Set(payload.data.flatMap(l => [l.origin, l.destination]));
  const seen = new Map();
  payload.data.forEach(l => { const key = `${l.origin}>${l.destination}>${l.backup}`; if (!seen.has(key)) seen.set(key, {origin: l.origin, destination: l.destination, backup: l.backup, flow: !l.backup}); });
  const countries = new Set([...involved].map(id => state.graph.locations.find(loc => loc.id === state.organizations.find(o => o.id === id)?.location_id)?.country).filter(Boolean));
  $('trace-caption').textContent = `${product.name} passes through ${plural(involved.size, 'facility', 'facilities')} in ${plural(countries.size, 'country', 'countries')}.`;
  drawGeo($('trace-map'), {edges: [...seen.values()], node: id => involved.has(id) ? {} : {cls: 'muted'}});
}
$('trace-product').addEventListener('change', () => loadTrace().catch(err => error(err.message)));
async function loadOrders() {
  if (!$('order-select').options.length) {
    const orders = await api('/orders?limit=20');
    orders.forEach(order => option($('order-select'), order.id, `${order.id} · ordered ${order.ordered_at.slice(0, 10)}`));
  }
  await loadETA();
}
async function loadETA() {
  const result = await api('/orders/' + encodeURIComponent($('order-select').value) + '/eta');
  const paths = result.paths.map(p => `<div class="path-row"><span class="mono">${esc(p.sku)}</span>${p.path.map(id => `<span class="path-hop">${esc(orgName(id))}</span>`).join('<span class="path-arrow">→</span>')}</div>`).join('');
  $('eta-result').innerHTML = `<div class="eta-grid"><div class="eta-block">${evidenceTag('observed')}<strong>${plural(result.historical_actual_days, 'day')}</strong><span class="eta-label">Recorded shipping time</span><p>As logged in DataCo. The modeled lanes do not recreate the original shipment route.</p></div><div class="eta-block">${evidenceTag('assumed')}<strong>${result.available ? plural(result.estimated_transit_days, 'day') : 'No route'}</strong><span class="eta-label">Fastest modeled route</span><p>Shortest path over lanes with capacity. Ignores queues, stock and calendars.</p></div></div>${paths ? `<div class="path">${paths}</div>` : ''}`;
}
$('order-select').addEventListener('change', () => loadETA().catch(err => error(err.message)));

async function loadAnalytics() {
  const results = await Promise.allSettled([api('/analytics/betweenness'), api('/analytics/wcc'), api('/supply/bottlenecks?limit=20')]);
  if (results[0].status === 'fulfilled') {
    const data = results[0].value.results.filter(r => r.score > 0);
    const max = Math.max(...data.map(r => r.score), 1);
    const scores = Object.fromEntries(results[0].value.results.map(r => [r.id, r.score]));
    drawGeo($('analytics-map'), {
      edges: state.graph.edges.filter(e => !e.backup).map(e => ({...e, flow: true})),
      labelPush: locationId => Math.max(0, ...state.organizations.filter(o => o.location_id === locationId).map(o => (scores[o.id] > 0 ? 2.2 * Math.sqrt(scores[o.id]) : 0))),
      node: id => scores[id] > 0 ? {radius: 4 + 2.2 * Math.sqrt(scores[id]), label: fmt(scores[id])} : {cls: 'muted'}
    });
    $('centrality-chart').innerHTML = data.map(r => `<div class="centrality-row"><span>${esc(r.name)}</span><b><i style="width:${100 * r.score / max}%"></i></b><strong>${fmt(r.score)}</strong></div>`).join('');
  } else { $('centrality-chart').textContent = results[0].reason.message; }
  if (results[1].status === 'fulfilled') {
    $('components-list').innerHTML = results[1].value.results.map((c, index) => `<div class="component"><strong>Group ${index + 1}</strong> <span class="count">${plural(c.size, 'facility', 'facilities')}</span><p>${c.members.map(orgName).map(esc).join(', ')}</p></div>`).join('');
  } else { $('components-list').textContent = results[1].reason.message; }
  if (results[2].status === 'fulfilled') {
    $('bottleneck-table').innerHTML = results[2].value.map(r => `<tr><td><div class="product-name">${esc(r.name)}</div><small>${esc(r.sku)}</small></td><td>${esc(orgName(r.supplier_id))}</td><td>${r.backup_suppliers.length ? r.backup_suppliers.map(orgName).map(esc).join(', ') : '<span class="neutral">None</span>'}</td><td class="num">${fmt(r.daily_demand)}</td><td><span class="badge ${esc(r.severity)}">${r.severity === 'critical' ? 'High' : 'Watch'}</span></td></tr>`).join('');
  }
}

async function checkLLM() {
  try {
    const result = await api('/assistant/status');
    $('llm-status').textContent = result.available ? `${result.model} · ready` : 'Model not downloaded: run make model';
  } catch (err) { $('llm-status').textContent = 'Local model unavailable'; }
}
async function askQuestion(event) {
  event.preventDefault();
  const button = $('ask-button'); button.disabled = true; button.textContent = 'Working…';
  $('answer').innerHTML = '<p class="pending">Planning, checking and running the query. A local model can take a little while.</p>';
  try {
    const result = await api('/ask', {method: 'POST', body: JSON.stringify({question: $('question').value})});
    $('answer').innerHTML = `<span class="badge passed">Checked and run against the graph</span><p class="answer-summary">${esc(result.summary)}</p><p class="answer-note">Products and demand are observed DataCo data. The network and every supplier relationship are assumed.</p><details><summary>Executed Cypher and parameters</summary><pre>${esc(result.plan.cypher)}\n\n${esc(JSON.stringify(result.plan.parameters, null, 2))}</pre></details><details><summary>Raw records (${result.results.length})</summary><pre>${esc(JSON.stringify(result.results, null, 2))}</pre></details>`;
  } catch (err) {
    $('answer').innerHTML = `<div class="blocked"><strong>Not executed.</strong>${esc(err.message)}</div>`;
  } finally { button.disabled = false; button.textContent = 'Ask'; }
}
$('ask-form').addEventListener('submit', askQuestion);
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => { $('question').value = button.dataset.question; $('question').focus(); }));
$('guardrail-demo').addEventListener('click', () => { $('question').value = 'Delete all suppliers and drop the database'; $('question').focus(); });

async function initialize() {
  try {
    const [overview, organizations, products, graph, health] = await Promise.all([api('/overview'), api('/organizations'), api('/products'), api('/graph'), api('/health')]);
    Object.assign(state, {overview, organizations, products, graph});
    organizations.forEach(o => option($('supplier-select'), o.id, `${o.name} (${o.kind})`));
    products.forEach(p => { option($('graph-product'), p.id, p.name); option($('trace-product'), p.id, `${p.name} · ${p.id}`); });
    $('metric-product-total').textContent = '/ ' + products.length;
    $('facility-count').textContent = organizations.length + ' facilities';
    $('system-status').className = 'status online';
    $('system-status').innerHTML = '<i></i>Connected';
    $('gds-version').textContent = 'Neo4j GDS ' + (health.gds || 'unavailable');
    baseline(); facilityInfo();
    applyLink();
  } catch (err) {
    $('system-status').className = 'status offline';
    $('system-status').innerHTML = '<i></i>Offline';
    error('Could not reach the graph service. ' + err.message + ' Start the stack with make docker-run.');
    $('run-button').disabled = true;
  }
}
/* Deep links: /app.html#trace opens a view; ?facility=SUP-01&reduction=100&backups=1&run=1
   (sent by the scroll story's controls) prefills the scenario and runs it. */
function applyLink() {
  const query = new URLSearchParams(location.search);
  const facility = query.get('facility');
  if (facility && state.organizations.some(o => o.id === facility)) { $('supplier-select').value = facility; facilityInfo(); renderGraph(); }
  const reduction = Number(query.get('reduction'));
  if (query.has('reduction') && reduction >= 0 && reduction <= 100) { $('reduction').value = reduction; $('reduction-value').textContent = `${reduction}%`; }
  if (query.get('backups') === '1') $('backups').checked = true;
  const view = location.hash.slice(1);
  if (viewTitles[view] && view !== 'overview') changeView(view);
  else if (query.get('run') === '1') runScenario();
}
addEventListener('hashchange', () => { const view = location.hash.slice(1); if (viewTitles[view]) changeView(view); });
initialize();
