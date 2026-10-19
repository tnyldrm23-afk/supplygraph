/* SupplyGeo: the dotted world map shared by the app and the scroll story.
   The projection must match scripts/create_land_map.py, which generated land.svg. */
'use strict';
const SupplyGeo = (() => {
  const GEO = { width: 1060, height: 359, lon0: -84, lon1: 124, latTop: 60 };
  const K = GEO.width / ((GEO.lon1 - GEO.lon0) * Math.PI / 180);
  const merc = lat => Math.log(Math.tan(Math.PI / 4 + Math.max(-80, Math.min(84, lat)) * Math.PI / 360));
  const Y0 = merc(GEO.latTop);
  const project = (lon, lat) => [K * (lon - GEO.lon0) * Math.PI / 180, K * (Y0 - merc(lat))];
  // [text-anchor, dx, dy] chosen by hand so the crowded European labels never overlap
  const cityLabel = {'LOC-PT': ['end', -20, 4], 'LOC-GB': ['end', -10, 0], 'LOC-NL': ['start', 9, 13], 'LOC-DE': ['start', 10, -3], 'LOC-FR': ['start', 9, 8], 'LOC-TR': ['start', 15, 4], 'LOC-VN': ['end', -15, 4], 'LOC-US': ['start', 15, 4]};
  const color = {supplier: 'var(--geo-supplier)', manufacturer: 'var(--geo-manufacturer)', distributor: 'var(--geo-distributor)', retailer: 'var(--geo-retailer)'};
  const stageOrder = ['supplier', 'manufacturer', 'distributor', 'retailer'];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function el(tag, attrs, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function positions({graph, organizations}) {
    const out = {};
    graph.locations.forEach(location => {
      const [x, y] = project(location.longitude, location.latitude);
      const here = organizations.filter(o => o.location_id === location.id)
        .sort((a, b) => stageOrder.indexOf(a.kind) - stageOrder.indexOf(b.kind));
      here.forEach((o, i) => { out[o.id] = [x + (i - (here.length - 1) / 2) * 10, y]; });
    });
    return out;
  }
  function arcPath([x1, y1], [x2, y2]) {
    const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
    if (len < 14) return `M${x1},${y1} L${x2},${y2}`;
    let nx = -dy / len, ny = dx / len;
    if (ny > 0) { nx = -nx; ny = -ny; }
    const lift = Math.min(90, len * .22);
    return `M${x1},${y1} Q${(x1 + x2) / 2 + nx * lift},${(y1 + y2) / 2 + ny * lift} ${x2},${y2}`;
  }
  /* data: {graph, organizations}
     options: edges [{origin, destination, backup, cls, flow, delay}], node(id) -> {cls, delay, radius, label, note},
              selected, animate, onSelect(id), labelPush(locationId) */
  function draw(svg, data, options) {
    const name = id => data.organizations.find(o => o.id === id)?.name || id;
    svg.replaceChildren();
    const box = svg.parentElement;
    if (box.scrollWidth > box.clientWidth && !box.dataset.centered) { box.scrollLeft = (box.scrollWidth - box.clientWidth) * .42; box.dataset.centered = '1'; }
    svg.classList.toggle('animate', Boolean(options.animate) && !reducedMotion.matches);
    svg.append(el('image', {href: '/land.svg', x: 0, y: 0, width: GEO.width, height: GEO.height, class: 'geo-land'}));
    const pos = positions(data);
    options.edges.forEach(edge => {
      const a = pos[edge.origin], b = pos[edge.destination];
      if (!a || !b) return;
      const d = arcPath(a, b), style = `--d:${edge.delay || 0}ms`;
      const lane = el('path', {d, class: `geo-lane ${edge.backup ? 'backup ' : ''}${edge.cls || ''}`, style});
      lane.append(el('title', {}, `${name(edge.origin)} → ${name(edge.destination)}${edge.backup ? ' (backup lane)' : ''}`));
      svg.append(lane);
      if (edge.flow) svg.append(el('path', {d, class: `geo-flow ${edge.backup ? 'backup ' : ''}${edge.cls || ''}`, style}));
    });
    data.graph.nodes.forEach(node => {
      const p = pos[node.id]; if (!p) return;
      const info = options.node ? options.node(node.id) : {};
      const r = info.radius || 4.2;
      const g = el('g', {class: `geo-node ${info.cls || ''}`, transform: `translate(${p[0]},${p[1]})`, style: `--d:${info.delay || 0}ms`});
      g.append(el('title', {}, `${node.name} · ${node.kind}${info.note ? ' · ' + info.note : ''}`));
      g.append(el('circle', {r: r + 6, class: 'halo', fill: color[node.kind]}));
      if (info.cls?.includes('failed')) g.append(el('circle', {r: r + 2, class: 'geo-pulse'}));
      g.append(el('circle', {r, class: 'core', fill: color[node.kind]}));
      if (options.selected === node.id) g.append(el('circle', {r: r + 4, class: 'select-ring'}));
      if (info.label) g.append(el('text', {x: 0, y: -r - 6, 'text-anchor': 'middle', class: 'geo-score'}, info.label));
      if (options.onSelect) g.addEventListener('click', () => options.onSelect(node.id));
      svg.append(g);
    });
    data.graph.locations.forEach(location => {
      const [x, y] = project(location.longitude, location.latitude);
      const [anchor, dx, dy] = cityLabel[location.id] || ['start', 10, 4];
      const push = options.labelPush?.(location.id) || 0;
      svg.append(el('text', {x: x + dx + Math.sign(dx) * push, y: y + dy, 'text-anchor': anchor, class: 'geo-city'}, location.name));
    });
  }
  return { GEO, project, positions, draw, reducedMotion };
})();
