'use strict';
/* SupplyGraph story page. Normal scrolling only: sections fade in once, and the
   status bar follows the section in view. The capacity control in the "dial"
   section shows the max-flow solver's real answer at every 10% step, prefetched
   from POST /api/scenarios. */
document.documentElement.classList.add('js');
const $ = id => document.getElementById(id);
const fmt = (value, digits = 1) => new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const reduced = SupplyGeo.reducedMotion.matches;
const narrow = matchMedia('(max-width: 860px)');
const FACILITY = 'SUP-01';
const STAGES = [['supplier', 'Suppliers', 'var(--geo-supplier)'], ['manufacturer', 'Manufacturers', 'var(--geo-manufacturer)'], ['distributor', 'Distributors', 'var(--geo-distributor)'], ['retailer', 'Retailers', 'var(--geo-retailer)']];
const data = { graph: null, organizations: [], overview: null, steps: [], backups: null };
const view = { dialStep: -1, rippled: false, statusAct: '' };

async function api(path, options = {}) {
  const response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json' } });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : response.status);
  return payload.data ?? payload;
}
const orgName = id => data.organizations.find(o => o.id === id)?.name || id;
const cityOf = id => data.graph.locations.find(l => l.id === data.organizations.find(o => o.id === id)?.location_id)?.name || '';
const list = items => items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`;

/* ---------- section tracking ---------- */
const acts = [...document.querySelectorAll('[data-act]')];
function update() {
  let current = acts[0].dataset.act;
  acts.forEach(act => { if (act.getBoundingClientRect().top <= innerHeight * .5) current = act.dataset.act; });
  document.querySelectorAll('[data-wp]').forEach(a => a.classList.toggle('on', a.dataset.wp === current));
  status(current);
}
let ticking = false;
addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; update(); }); } }, { passive: true });

const entrance = new IntersectionObserver(entries => entries.forEach(entry => {
  if (!entry.isIntersecting) return;
  const group = entry.target, step = Number(group.dataset.stagger || 0);
  [...group.children].forEach((child, i) => child.style.setProperty('--delay', `${i * step}ms`));
  group.classList.add('is-in');
  group.querySelectorAll('[data-count]').forEach(countUp);
  if (group.contains($('r-bars'))) fillBars();
  entrance.unobserve(group);
}), { rootMargin: '0px 0px -12% 0px' });
document.querySelectorAll('[data-in]').forEach(group => { if (!group.children.length) group.classList.add('solo'); entrance.observe(group); });

function countUp(el) {
  const target = Number(el.dataset.count), digits = (el.dataset.count.split('.')[1] || '').length;
  if (reduced || !target) { el.textContent = fmt(target, digits); return; }
  const start = performance.now(), duration = 1400;
  const tick = now => {
    const t = clamp((now - start) / duration);
    el.textContent = fmt(target * (1 - Math.pow(1 - t, 3)), digits);
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* ---------- status bar ---------- */
function status(act) {
  if (!data.overview || act === view.statusAct && act !== 'dial') return;
  view.statusAct = act;
  const demand = data.overview.daily_demand;
  let label = 'Baseline · every lane available', delivered = demand, alert = false;
  if (act === 'dial' && view.dialStep >= 0) {
    const s = data.steps[view.dialStep];
    label = view.dialStep === 0 ? 'Atlas Textiles selected · full capacity' : `Atlas Textiles · ${100 - view.dialStep * 10}% capacity left`;
    delivered = s.totals.scenario_delivered; alert = view.dialStep > 0;
  } else if ((act === 'recovery' || act === 'short') && data.backups) {
    label = 'Atlas Textiles offline · backups on'; delivered = data.backups.totals.scenario_delivered; alert = true;
  } else if (act === 'controls') {
    label = 'Your scenario';
  }
  $('sb-scenario').textContent = label;
  $('sb-scenario').classList.toggle('alert', alert);
  $('sb-delivered').textContent = fmt(delivered);
  $('sb-demand').textContent = fmt(demand);
}

/* ---------- maps ---------- */
const geoData = () => ({ graph: data.graph, organizations: data.organizations });
function fitMaps() {
  // Phones get a crop centred on Europe so labels stay legible; Ho Chi Minh City falls outside it.
  document.querySelectorAll('.map-frame svg').forEach(svg => svg.setAttribute('viewBox', narrow.matches ? '18 40 650 300' : '0 0 1060 359'));
}
function drawBaseline() {
  SupplyGeo.draw($('map-baseline'), geoData(), { edges: data.graph.edges.map(e => ({ ...e, flow: !e.backup })), node: id => id === FACILITY ? {} : {} });
}
function drawDial(step, animate) {
  const s = data.steps[step], hit = step > 0, short = s.affected_products > 0;
  const hops = Object.fromEntries(s.exposed_organizations.map(o => [o.id, o.hops]));
  const gap = 380;
  SupplyGeo.draw($('map-dial'), geoData(), {
    animate,
    selected: FACILITY,
    edges: data.graph.edges.map(e => {
      if (hit && (e.origin === FACILITY || e.destination === FACILITY)) return { ...e, cls: short ? 'failed' : 'affected', flow: !short };
      if (short && hops[e.origin] !== undefined && !e.backup) return { ...e, cls: 'affected', flow: true, delay: (hops[e.origin] + .5) * gap };
      return { ...e, cls: short && !e.backup ? 'faded' : '', flow: !e.backup, delay: 600 };
    }),
    node: id => {
      if (id === FACILITY && hit) return short ? { cls: 'failed', note: 'capacity reduced' } : { cls: 'affected' };
      if (short && hops[id] > 0) return { cls: 'affected', delay: hops[id] * gap, note: `${hops[id]} hop${hops[id] === 1 ? '' : 's'} downstream` };
      return {};
    }
  });
}
function drawRecovery() {
  const b = data.backups, hops = Object.fromEntries(b.exposed_organizations.map(o => [o.id, o.hops]));
  SupplyGeo.draw($('map-recovery'), geoData(), {
    edges: data.graph.edges.map(e => {
      if (e.origin === FACILITY || e.destination === FACILITY) return { ...e, cls: 'failed', flow: false };
      if (e.backup) return { ...e, flow: true };
      return { ...e, cls: hops[e.origin] > 0 ? 'affected' : 'faded', flow: true };
    }),
    node: id => id === FACILITY ? { cls: 'failed' } : hops[id] > 0 ? { cls: 'affected' } : {}
  });
}

/* ---------- the dial ---------- */
const slider = $('d-slider');
let playing = null;
function stepFromSlider() { return (100 - Number(slider.value)) / 10; }
slider.addEventListener('input', () => { stopPlay(); renderDial(stepFromSlider()); });
$('d-play').addEventListener('click', () => {
  if (playing) return stopPlay();
  if (stepFromSlider() === 10) { slider.value = 100; renderDial(0); }
  $('d-play').textContent = 'Pause';
  playing = setInterval(() => {
    slider.value = Number(slider.value) - 10;
    renderDial(stepFromSlider());
    if (stepFromSlider() === 10) stopPlay();
  }, reduced ? 50 : 650);
});
function stopPlay() {
  if (!playing) return;
  clearInterval(playing); playing = null;
  $('d-play').textContent = stepFromSlider() === 10 ? 'Start again' : 'Take it offline';
}
function renderDial(step) {
  if (!data.steps.length) return;
  const changed = step !== view.dialStep;
  view.dialStep = step;
  const s = data.steps[step], t = s.totals, left = 100 - step * 10;
  const short = s.affected_products > 0;
  if (changed) {
    const ripple = short && !view.rippled;
    if (short) view.rippled = true; else if (step === 0) view.rippled = false;
    drawDial(step, ripple);
    $('d-capacity').textContent = `${left}%`;
    slider.value = left;
    $('d-service').textContent = fmt(t.service_level);
    $('d-products').textContent = s.affected_products;
    $('d-unmet').textContent = fmt(t.unmet_demand);
    document.querySelector('.readings').classList.toggle('hit', short);
    const losing = s.products.filter(x => x.lost_units > 0).sort((a, b) => b.lost_units - a.lost_units).slice(0, 5);
    $('d-losing').innerHTML = losing.length
      ? losing.map(x => `<li><span>${esc(x.name)}</span><strong>−${fmt(x.lost_units)}</strong></li>`).join('')
      : '<li class="empty">No product is short.</li>';
  }
  const retailers = Object.keys(s.retailer_losses || {}).filter(id => s.retailer_losses[id] > 0).map(cityOf);
  let line = 'Full capacity. Drag the slider or press Take it offline.';
  if (step > 0 && !short) line = `${step * 10}% gone and nothing breaks. Spare capacity downstream absorbs it.`;
  else if (short && step < 10) line = `${step * 10}% gone. ${s.affected_products} products are now short in ${list(retailers)}.`;
  else if (step === 10) line = `Atlas Textiles is offline. The shortfall reaches ${list(retailers)}.`;
  $('d-status').textContent = line;
  $('d-status').classList.toggle('alert', short);
  if (changed) status('dial');
}

/* ---------- static acts ---------- */
function renderStructure() {
  $('stages').innerHTML = STAGES.map(([kind, heading, color]) => {
    const orgs = data.organizations.filter(o => o.kind === kind);
    return `<li><h3><i style="--c:${color}"></i>${heading}<span>${orgs.length}</span></h3><ul>${orgs.map(o => `<li class="${o.id === FACILITY ? 'focus' : ''}"><strong>${esc(o.name)}</strong><small>${esc(cityOf(o.id))} · ${esc(o.id)}</small></li>`).join('')}</ul></li>`;
  }).join('');
}
function fillBars() {
  if (!data.backups) return;
  const down = data.steps[10].totals.service_level, up = data.backups.totals.service_level;
  $('r-bar-down').style.setProperty('--w', `${down}%`);
  $('r-bar-up').style.setProperty('--w', `${up}%`);
}
function renderRecovery() {
  const down = data.steps[10].totals.service_level, up = data.backups.totals.service_level;
  $('r-restored').dataset.count = fmt(data.steps[10].totals.restored_with_backups, 1).replace(/,/g, '');
  $('r-down').textContent = `${fmt(down, 0)}%`;
  $('r-up').textContent = `${fmt(up, 0)}%`;
  if ($('r-bars').closest('[data-in]').classList.contains('is-in')) { fillBars(); countUp($('r-restored')); }
  drawRecovery();
}
function renderRail() {
  const rail = $('rail');
  const without = Object.fromEntries(data.steps[10].products.map(p => [p.sku, p]));
  const still = data.backups.products.filter(p => p.lost_units > 0).sort((a, b) => b.lost_units - a.lost_units);
  const cards = still.slice(0, 8).map(p => {
    const before = without[p.sku] || p, after = before.scenario_delivered, added = Math.max(0, p.scenario_delivered - after);
    return `<article class="label-card"><p class="sku">${esc(p.sku)}</p><h3>${esc(p.name)}</h3><dl>
      <div><dt>Demand</dt><dd>${fmt(p.demand)}</dd></div>
      <div><dt>Atlas offline</dt><dd>${fmt(after)}</dd></div>
      <div><dt>Backups add</dt><dd>+${fmt(added)}</dd></div>
      <div class="gap"><dt>Still short</dt><dd>${fmt(p.lost_units)}</dd></div></dl>
      <div class="kept" aria-hidden="true"><i class="a" style="width:${100 * after / p.demand}%"></i><i class="b" style="width:${100 * added / p.demand}%"></i></div></article>`;
  }).join('');
  rail.innerHTML = cards;
  const affected = data.steps[10].affected_products, recovered = affected - still.length;
  $('rail-end').innerHTML = `<strong>${still.length} of ${affected}</strong> affected products stay short with backups on. ${recovered ? `${recovered} recover completely.` : ''} Shown: the ${Math.min(8, still.length)} largest gaps.`;
}
function renderConsole() {
  const select = $('c-facility');
  data.organizations.forEach(o => select.add(new Option(`${o.name} (${o.kind}, ${cityOf(o.id)})`, o.id, o.id === FACILITY, o.id === FACILITY)));
  const out = () => { $('c-out').textContent = `${$('c-reduction').value}%`; };
  $('c-reduction').addEventListener('input', out); out();
  select.addEventListener('change', drawControls);
  $('c-backups').addEventListener('change', drawControls);
  drawControls();
}
function downstreamOf(id) {
  // Breadth-first walk over primary lanes: every facility this one can starve.
  const reach = new Map([[id, 0]]), queue = [id];
  while (queue.length) {
    const at = queue.shift();
    data.graph.edges.filter(e => e.origin === at && !e.backup).forEach(e => {
      if (!reach.has(e.destination)) { reach.set(e.destination, reach.get(at) + 1); queue.push(e.destination); }
    });
  }
  return reach;
}
function drawControls() {
  const id = $('c-facility').value, reach = downstreamOf(id), backups = $('c-backups').checked;
  SupplyGeo.draw($('map-controls'), geoData(), {
    selected: id,
    edges: data.graph.edges.map(e => reach.has(e.origin) && reach.has(e.destination) && !e.backup ? { ...e, cls: 'affected', flow: true } : { ...e, cls: e.backup && backups ? '' : 'faded', flow: e.backup && backups }),
    node: o => o === id ? { cls: 'failed' } : reach.has(o) ? { cls: 'affected' } : { cls: 'muted' }
  });
  const retailers = [...reach.keys()].filter(o => data.organizations.find(x => x.id === o)?.kind === 'retailer').map(cityOf);
  $('c-reach').innerHTML = reach.size > 1
    ? `<strong>${esc(orgName(id))}</strong> sits upstream of ${reach.size - 1} ${reach.size === 2 ? 'facility' : 'facilities'}${retailers.length ? `, including stores in ${esc(list(retailers))}` : ''}.`
    : `<strong>${esc(orgName(id))}</strong> is a retailer: nothing sits downstream of it.`;
}

/* ---------- boot ---------- */
async function boot() {
  fitMaps();
  narrow.addEventListener('change', () => { fitMaps(); const step = Math.max(0, view.dialStep); view.dialStep = -1; drawBaseline(); if (data.steps.length) renderDial(step); if (data.backups) drawRecovery(); });
  try {
    const [overview, organizations, graph, health] = await Promise.all([api('/overview'), api('/organizations'), api('/graph'), api('/health')]);
    Object.assign(data, { overview, organizations, graph });
    $('conn').className = 'conn online'; $('conn').innerHTML = `<i></i>Connected · GDS ${esc(health.gds || '')}`;
    $('b-orgs').textContent = overview.organizations; $('b-lanes').textContent = fmt(overview.lanes, 0); $('b-products').textContent = overview.products;
    $('b-service').textContent = fmt(overview.baseline_service_level);
    drawBaseline(); renderStructure(); renderConsole();
    // The solver allows a limited number of concurrent runs, so the steps are fetched one at a time.
    for (let i = 0; i <= 10; i++) {
      data.steps.push(await api('/scenarios', { method: 'POST', body: JSON.stringify({ supplier_ids: [FACILITY], reduction: i / 10, depth: 6, activate_backups: false }) }));
    }
    data.backups = await api('/scenarios', { method: 'POST', body: JSON.stringify({ supplier_ids: [FACILITY], reduction: 1, depth: 6, activate_backups: true }) });
    renderDial(0); renderRecovery(); renderRail();
  } catch (err) {
    $('conn').className = 'conn offline'; $('conn').innerHTML = '<i></i>Offline';
    $('sb-scenario').textContent = `Could not reach the graph service (${err.message}). Start it with make docker-run.`;
  }
  update();
}
boot();
