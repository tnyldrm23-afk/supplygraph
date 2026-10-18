'use strict';
const $ = id => document.getElementById(id);
const state = { organizations: [], products: [], graph: null, overview: null, scenario: null, allProducts: false, view: 'overview' };
const fmt = (value, digits = 1) => new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const orgName = id => state.organizations.find(o => o.id === id)?.name || id;
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

function svgElement(tag, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs || {}).forEach(([key, value]) => el.setAttribute(key, value));
  if (text !== undefined) el.textContent = text;
  return el;
}
const kindStyle = {
  supplier: ['#426bc2', '#eaf0ff', 'Suppliers'],
  manufacturer: ['#8963b7', '#f2edfa', 'Manufacturers'],
  distributor: ['#8e5d22', '#fbf2e4', 'Distributors'],
  retailer: ['#276e5a', '#e8f4ee', 'Retailers']
};
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
function renderGraph() {
  if (!state.graph) return;
  const svg = $('network-graph');
  svg.replaceChildren();
  const defs = svgElement('defs');
  ['normal', 'affected', 'failed'].forEach((type, index) => {
    const marker = svgElement('marker', {id:`arrow-${type}`, markerWidth:6, markerHeight:6, refX:5.5, refY:3, orient:'auto'});
    marker.append(svgElement('path', {d:'M0,0 L6,3 L0,6 Z',fill:['#9eb2d3','#d49336','#c45a66'][index]}));
    defs.append(marker);
  });
  svg.append(defs);
  const positions = {};
  Object.entries(kindStyle).forEach(([kind, colors], col) => {
    const nodes = state.graph.nodes.filter(n => n.kind === kind);
    const x = 34 + col * 263;
    svg.append(svgElement('rect', {x:x-14,y:14,width:236,height:406,rx:12,fill:colors[1],opacity:.45}));
    svg.append(svgElement('text', {x,y:43,fill:colors[0],'font-size':13,'font-family':'system-ui','font-weight':650}, colors[2]));
    svg.append(svgElement('text', {x:x+207,y:43,fill:'#5e718e','font-size':12,'text-anchor':'end','font-family':'system-ui'}, String(nodes.length).padStart(2,'0')));
    nodes.forEach((node,index) => { positions[node.id] = {x,y:74+index*82+(nodes.length===3?41:0)}; });
  });
  const failures = new Set(state.scenario?.scenario.supplier_ids || []);
  const exposed = new Set(state.scenario?.exposed_organizations.map(n => n.id) || []);
  const reduction = state.scenario?.scenario.reduction || 0;
  const backups = state.scenario?.scenario.activate_backups || false;
  state.graph.edges.forEach(edge => {
    const from = positions[edge.origin], to = positions[edge.destination];
    if (!from || !to) return;
    let cls = 'edge' + (edge.backup ? ' backup' : ''), marker = 'normal';
    if (reduction > 0) {
      if (failures.has(edge.origin) || failures.has(edge.destination)) { cls += ' failed'; marker = 'failed'; }
      else if (exposed.has(edge.origin) && !edge.backup) { cls += ' affected'; marker = 'affected'; }
      else if (!edge.backup) cls += ' faded';
    }
    const x1=from.x+208, y1=from.y+34, x2=to.x, y2=to.y+34;
    const bend=Math.max(25,Math.abs(x2-x1)*.5);
    const path=svgElement('path',{d:`M${x1},${y1} C${x1+bend},${y1} ${x2-bend},${y2} ${x2},${y2}`,class:cls,'marker-end':`url(#arrow-${marker})`});
    if (edge.backup && backups) path.setAttribute('style','opacity:1;stroke:#3b9070;stroke-width:2');
    path.append(svgElement('title',{},`${orgName(edge.origin)} → ${orgName(edge.destination)} · ${edge.product_count} products · ${edge.backup?'Reserve':'Primary'} contract · Assumed topology`));
    svg.append(path);
  });
  state.graph.nodes.forEach(node => {
    const pos=positions[node.id], colors=kindStyle[node.kind];
    const failed=failures.has(node.id)&&reduction>0, affected=exposed.has(node.id)&&reduction>0;
    const selected=$('supplier-select').value===node.id;
    const group=svgElement('g',{class:'node',transform:`translate(${pos.x},${pos.y})`,tabindex:0,role:'button','aria-label':`${node.name}, ${node.kind}. Select for scenario.`,'aria-pressed':String(selected)});
    group.append(svgElement('title',{},`${node.name} · ${node.id} · ${failed?'Disrupted':affected?'Downstream exposure':'Assumed facility'}`));
    group.append(svgElement('rect',{class:'node-card',width:208,height:68,rx:9,fill:failed?'#fff2f2':selected?'#f3f7ff':'#fff',stroke:failed?'#d58c96':selected?'#6488d0':affected?'#d9b584':'#d5dfed','stroke-width':selected?1.8:1}));
    group.append(svgElement('rect',{x:12,y:16,width:35,height:35,rx:9,fill:failed?'#fae1e4':colors[1]}));
    const icon=node.kind==='supplier'?'M20 32h18m-16-6 7-5 7 5v16H22V26m5 9h5':node.kind==='manufacturer'?'M20 41V26l8 4v-7l9 6v12H20m4-4h3m5 0h3':node.kind==='distributor'?'m20 27 9-5 9 5v12l-9 5-9-5V27m0 0 9 5 9-5m-9 5v12':'M20 31h19l-3-8H23l-3 8m3 0v13h13V31m-9 13v-8h5v8';
    group.append(svgElement('path',{d:icon,fill:'none',stroke:failed?'#b54a5b':colors[0],'stroke-width':1.5,'stroke-linejoin':'round'}));
    group.append(svgElement('text',{x:57,y:29,fill:failed?'#a34554':'#2d456b','font-size':13,'font-family':'system-ui','font-weight':600},node.name));
    const location=state.graph.locations.find(l=>l.id===node.location_id);
    group.append(svgElement('text',{x:57,y:48,fill:'#5e718e','font-size':10,'font-family':'system-ui'},`${location?.name||node.id} · ${node.id}`));
    group.append(svgElement('circle',{cx:195,cy:12,r:2.6,fill:failed?'#bc4d5e':affected?'#bc8e49':'#76a98d'}));
    group.addEventListener('click',()=>selectFacility(node.id));
    group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectFacility(node.id);}});
    svg.append(group);
  });
  const list=$('network-list');list.replaceChildren();
  Object.entries(kindStyle).forEach(([kind,colors])=>{
    const nodes=state.graph.nodes.filter(n=>n.kind===kind);
    const section=document.createElement('section');section.className='facility-group';
    const heading=document.createElement('h3');heading.innerHTML=`${esc(colors[2])}<span>${nodes.length}</span>`;section.append(heading);
    nodes.forEach(node=>{
      const failed=failures.has(node.id)&&reduction>0, selected=$('supplier-select').value===node.id;
      const location=state.graph.locations.find(l=>l.id===node.location_id);
      const button=document.createElement('button');button.type='button';button.className='facility-item'+(selected?' selected':'')+(failed?' failed':'');
      button.setAttribute('aria-pressed',String(selected));button.setAttribute('aria-label',`${node.name}, ${node.kind}. Select for scenario.`);
      button.innerHTML=`<span class="facility-dot" style="background:${failed?'#bc4d5e':colors[0]}" aria-hidden="true"></span><span><strong>${esc(node.name)}</strong><small>${esc(location?.name||node.id)} · ${esc(node.id)}${failed?' · Disrupted':selected?' · Selected':''}</small></span>`;
      button.addEventListener('click',()=>selectFacility(node.id));section.append(button);
    });list.append(section);
  });
  syncGraphView();
}
function updateServiceTrack(value) {
  $('service-spark').style.width = Math.max(0,Math.min(100,value))+'%';
}
function facilityInfo() {
  const organization = state.organizations.find(o => o.id === $('supplier-select').value);
  const location = state.graph?.locations.find(l => l.id === organization?.location_id);
  $('facility-info').textContent = organization ? `${organization.id} · ${location?.country || ''} · Assumed facility` : '';
}
function baseline() {
  state.scenario = null; state.allProducts = false;
  $('metric-service').textContent = fmt(state.overview.baseline_service_level);
  updateServiceTrack(state.overview.baseline_service_level);
  $('metric-products').textContent = '0'; $('metric-loss').textContent = '0'; $('metric-recovery').textContent = '0';
  $('service-change').textContent = 'Baseline capacity'; $('service-change').className='positive';
  $('product-change').textContent='No disruption applied'; $('loss-change').textContent='Baseline network intact';
  $('scenario-result').hidden=true; $('impact-count').textContent='No scenario';
  $('impact-subtitle').textContent='Run a scenario to reveal the downstream effect.';
  $('impact-table').innerHTML='<tr><td colspan="5" class="table-empty">Your baseline is ready. Choose a facility and run a disruption scenario.</td></tr>';
  $('graph-caption').textContent='Baseline network · primary connections available';
  $('bar-scenario').style.width='100%'; $('bar-recovery').style.width='100%';
  $('bar-scenario-value').textContent='100%'; $('bar-recovery-value').textContent='100%';
  $('recovery-heading').textContent='Build resilience into your next decision.';
  $('recovery-copy').textContent='Compare a disruption with reserve capacity activated. See what can be recovered — and what still needs attention.';
  $('all-products-button').textContent='Show all products ↗'; renderGraph();
}
async function runScenario(event) {
  event?.preventDefault(); error('');
  const button = $('run-button'); button.disabled = true; button.textContent='Calculating network impact…';
  try {
    const body = {supplier_ids:[$('supplier-select').value],reduction:Number($('reduction').value)/100,depth:Number($('depth').value),activate_backups:$('backups').checked,sku:$('graph-product').value || null};
    state.scenario = await api('/scenarios',{method:'POST',body:JSON.stringify(body)});
    renderScenario();
  } catch (err) { error(err.message); }
  finally { button.disabled=false; button.innerHTML='Run scenario <span>↗</span>'; }
}
function renderScenario() {
  const s = state.scenario, t = s.totals;
  $('metric-service').textContent=fmt(t.service_level); updateServiceTrack(t.service_level); $('metric-products').textContent=fmt(s.affected_products,0);
  $('metric-product-total').textContent='/ '+s.products.length;
  $('metric-loss').textContent=fmt(t.unmet_demand); $('metric-recovery').textContent=fmt(t.restored_with_backups);
  const delta = t.service_level - t.baseline_service_level;
  $('service-change').textContent=`${delta >= 0 ? '+' : ''}${fmt(delta)} pp vs baseline`; $('service-change').className=delta<0?'negative':'positive';
  $('product-change').textContent=`${s.affected_retailers} retailer${s.affected_retailers===1?'':'s'} lose delivery capacity`;
  $('loss-change').textContent=`${fmt(t.scenario_delivered)} / ${fmt(t.demand)} units fulfilled`;
  $('graph-caption').textContent=`${orgName(s.scenario.supplier_ids[0])} · ${Math.round(s.scenario.reduction*100)}% capacity reduction`;
  $('impact-count').textContent=`${s.affected_products} affected`;
  $('impact-subtitle').textContent='Baseline versus scenario · independent product-specific capacity';
  $('scenario-result').hidden=false;
  $('scenario-result').innerHTML=`<div><strong>Scenario calculated</strong><p>${fmt(s.affected_products,0)} products affected · ${fmt(t.unmet_demand)} unmet units/day</p><small>${s.exposed_organizations.length} facilities in exposure scope. Results use assumed supply lanes.${s.traversal_truncated?' Exposure depth limit reached.':''}</small></div><a href="#product-impact">Review product impact ↓</a>`;
  const recovery = Math.min(100,100*(t.scenario_delivered+t.restored_with_backups)/t.demand);
  $('bar-scenario').style.width=t.service_level+'%'; $('bar-scenario-value').textContent=fmt(t.service_level,0)+'%';
  $('bar-recovery').style.width=recovery+'%'; $('bar-recovery-value').textContent=fmt(recovery,0)+'%';
  $('recovery-heading').textContent=t.restored_with_backups>0?`${fmt(t.restored_with_backups)} units/day can be recovered.`:'Understand the remaining exposure.';
  $('recovery-copy').textContent=t.restored_with_backups>0?'Reserve contracts provide partial recovery. Compare both scenarios before choosing a mitigation.':s.scenario.activate_backups?'Reserve contracts are already active. Residual shortages need new capacity or another route.':'No additional reserve capacity improves this scenario. Inspect affected products for single-source dependencies.';
  renderImpactTable(); renderGraph();
}
function renderImpactTable() {
  const rows = state.scenario?.products || [];
  const selected = state.allProducts ? rows : rows.slice(0,6);
  $('impact-table').innerHTML=selected.map(p=>`<tr><td><div class="product-name">${esc(p.name)}</div><small>${esc(p.sku)}</small></td><td>${fmt(p.baseline_delivered)}</td><td>${fmt(p.scenario_delivered)}</td><td class="${p.lost_units>0?'negative':''}">${p.lost_units>0?'−':''}${fmt(p.lost_units)}</td><td><span class="badge ${esc(p.status)}">${p.status==='disrupted'?'Disrupted':'Stable'}</span></td></tr>`).join('');
  $('table-count').textContent=`Showing ${selected.length} of ${rows.length} products · units/day`;
}
$('scenario-form').addEventListener('submit',runScenario);
$('reduction').addEventListener('input',()=>{$('reduction-value').textContent=$('reduction').value+'%';});
$('supplier-select').addEventListener('change',()=>{facilityInfo();renderGraph();});
$('baseline-button').addEventListener('click',()=>{error('');baseline();});
$('reset-graph').addEventListener('click',async()=>{$('graph-product').value='';await filterGraph();baseline();});
$('graph-product').addEventListener('change',filterGraph);
async function filterGraph(){try{state.graph=await api('/graph'+($('graph-product').value?'?sku='+encodeURIComponent($('graph-product').value):''));state.scenario=null;baseline();$('metric-product-total').textContent='/ '+($('graph-product').value?'1':state.products.length);facilityInfo();}catch(err){error(err.message);}}
$('all-products-button').addEventListener('click',()=>{if(!state.scenario)return;state.allProducts=!state.allProducts;$('all-products-button').textContent=state.allProducts?'Show fewer products ↑':'Show all products ↗';renderImpactTable();});
$('recovery-button').addEventListener('click',()=>{$('backups').checked=true;runScenario();});
$('export-button').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(state.scenario || {baseline:state.overview,evidence:'No disruption applied'},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=`supplygraph-${state.scenario?.scenario_id || 'baseline'}.json`;anchor.click();URL.revokeObjectURL(url);});

async function changeView(view) {
  state.view=view;error('');
  document.querySelectorAll('.view').forEach(el=>{el.hidden=el.id!=='view-'+view;});
  document.querySelectorAll('.nav').forEach(el=>{el.classList.toggle('active',el.dataset.view===view);if(el.dataset.view===view)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
  $('breadcrumb-title').textContent={overview:'Overview',trace:'Products',analytics:'Analytics',assistant:'Assistant'}[view];
  try{if(view==='trace')await Promise.all([loadTrace(),loadOrders()]);if(view==='analytics')await loadAnalytics();if(view==='assistant')await checkLLM();}catch(err){error(err.message);}
}
document.querySelectorAll('.nav').forEach(button=>button.addEventListener('click',()=>changeView(button.dataset.view)));
async function loadTrace(){
  const sku=$('trace-product').value;if(!sku)return;
  const response=await fetch('/api/products/'+encodeURIComponent(sku)+'/provenance');const payload=await response.json();if(!response.ok)throw new Error(payload.detail);
  const product=state.products.find(p=>p.id===sku);
  $('trace-summary').innerHTML=`<div><strong>${fmt(product.historical_units,0)}</strong><span>observed historical units</span></div><div><strong>${fmt(product.daily_demand)}</strong><span>daily demand · units/day</span></div><div><strong>${payload.data.length}</strong><span>assumed supply lanes</span></div>`;
  $('trace-table').innerHTML=payload.data.map(l=>`<tr><td>${esc(l.id)}<small>${l.backup?'Reserve':'Primary'} contract</small></td><td>${esc(orgName(l.origin))} → ${esc(orgName(l.destination))}</td><td>${fmt(l.capacity)}</td><td>${l.lead_days} days</td><td>${evidenceTag(l.provenance)}</td></tr>`).join('');
  $('trace-query').textContent=payload.evidence.cypher;
}
$('trace-product').addEventListener('change',()=>loadTrace().catch(err=>error(err.message)));
async function loadOrders(){if(!$('order-select').options.length){const orders=await api('/orders?limit=20');orders.forEach(order=>option($('order-select'),order.id,`${order.id} · ${order.ordered_at.slice(0,10)}`));}await loadETA();}
async function loadETA(){const result=await api('/orders/'+encodeURIComponent($('order-select').value)+'/eta');$('eta-result').innerHTML=`<div class="eta-grid"><div class="eta-block">${evidenceTag('observed')}<strong>${result.historical_actual_days} days</strong>Historical actual shipping duration<p>DataCo observation. These fictional lanes do not reconstruct the original shipment route.</p></div><div class="eta-block">${evidenceTag('assumed')}<strong>${result.available?result.estimated_transit_days+' days':'No path'}</strong>Modeled transit lower bound<p>Shortest positive-capacity route. Excludes queues, stock and calendar effects.</p></div></div><div class="path">${result.paths.map(p=>`${esc(p.sku)}: ${p.path.map(orgName).map(esc).join(' → ')}`).join('<br>')}</div>`;}
$('order-select').addEventListener('change',()=>loadETA().catch(err=>error(err.message)));
async function loadAnalytics(){
  const results=await Promise.allSettled([api('/analytics/betweenness'),api('/analytics/wcc'),api('/supply/bottlenecks?limit=20')]);
  if(results[0].status==='fulfilled'){const data=results[0].value.results.filter(r=>r.score>0);const max=Math.max(...data.map(r=>r.score),1);$('centrality-chart').innerHTML=data.map(r=>`<div class="centrality-row"><span>${esc(r.name)}</span><b><i style="width:${100*r.score/max}%"></i></b><strong>${fmt(r.score)}</strong></div>`).join('');}else{$('centrality-chart').textContent=results[0].reason.message;}
  if(results[1].status==='fulfilled'){$('components-list').innerHTML=results[1].value.results.map((c,index)=>`<div class="component"><strong>Component ${index+1} <span class="pill">${c.size} ${c.size===1?'facility':'facilities'}</span></strong><p>${c.members.map(orgName).map(esc).join(' · ')}</p></div>`).join('');}else{$('components-list').textContent=results[1].reason.message;}
  if(results[2].status==='fulfilled'){$('bottleneck-table').innerHTML=results[2].value.map(r=>`<tr><td class="product-name">${esc(r.name)}<small>${esc(r.sku)}</small></td><td>${esc(orgName(r.supplier_id))}</td><td>${r.backup_suppliers.length?r.backup_suppliers.map(orgName).map(esc).join(', '):'No reserve contract'}</td><td>${fmt(r.daily_demand)}</td><td><span class="badge ${esc(r.severity)}">${r.severity==='critical'?'Critical':'Watch'}</span></td></tr>`).join('');}
}
async function checkLLM(){try{const result=await api('/assistant/status');$('llm-status').textContent=result.available?result.model+' · ready':'Local model not ready · run make model';}catch(err){$('llm-status').textContent='Local model unavailable';}}
async function askQuestion(event){event.preventDefault();const button=$('ask-button');button.disabled=true;button.textContent='Querying local model…';$('answer').innerHTML='<p>Generating and validating an audited Cypher plan. The local model may take a moment.</p>';try{const result=await api('/ask',{method:'POST',body:JSON.stringify({question:$('question').value})});$('answer').innerHTML=`<span class="badge">Guardrails passed · actual graph evidence</span><p class="answer-summary">${esc(result.summary)}</p><p>Observed: DataCo products and historical demand. Assumed: scenario network and all supplier relationships.</p><details><summary>Executed Cypher & parameters</summary><pre>${esc(result.plan.cypher)}\n\n${esc(JSON.stringify(result.plan.parameters,null,2))}</pre></details><details><summary>Graph records (${result.results.length})</summary><pre>${esc(JSON.stringify(result.results,null,2))}</pre></details>`;}catch(err){$('answer').innerHTML=`<div class="blocked"><strong>Request was not executed.</strong><br>${esc(err.message)}</div>`;}finally{button.disabled=false;button.textContent='Ask SupplyGraph ↗';}}
$('ask-form').addEventListener('submit',askQuestion);
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{$('question').value=button.dataset.question;$('question').focus();}));
$('guardrail-demo').addEventListener('click',()=>{$('question').value='Delete all suppliers and drop the database';$('question').focus();});
async function initialize(){
  try{
    const [overview,organizations,products,graph,health]=await Promise.all([api('/overview'),api('/organizations'),api('/products'),api('/graph'),api('/health')]);
    Object.assign(state,{overview,organizations,products,graph});
    organizations.forEach(o=>option($('supplier-select'),o.id,`${o.name} · ${o.kind}`));
    products.forEach(p=>{option($('graph-product'),p.id,p.name);option($('trace-product'),p.id,`${p.name} · ${p.id}`);});
    $('metric-product-total').textContent='/ '+products.length;
    $('facility-count').textContent=organizations.length+' facilities';
    $('system-status').innerHTML='<i></i>Network connected';$('gds-version').textContent='Neo4j GDS '+(health.gds || 'unavailable');
    baseline();facilityInfo();
  }catch(err){$('system-status').textContent='Connection unavailable';error('Unable to load the graph service. '+err.message+' Start the stack with make docker-run.');$('run-button').disabled=true;}
}
initialize();
