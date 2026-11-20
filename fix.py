#!/usr/bin/env python3
"""Fork fix for FBA Box & Freight Packer (Bankr app fba-pack-master).

Fixes, against original/index.html:
 1. Metric mode: values were relabeled, never converted. Canonical internal
    unit is now inches/lbs; display converts both ways (inputs, outputs,
    guardrails, pallet math, manifest). CSV stays imperial (Amazon format).
 2. Packing Strategy (and other native <select>s) replaced with the toggle
    button groups the app already uses for mode/units, which work reliably
    in the sandboxed iframe. Changing one recalculates when results exist.
 3. Copy Manifest / CSV now give toast feedback, use bankr.copy when the
    Bankr host provides it, and fall back clipboard -> execCommand.
    Added a Copy CSV button as a guaranteed export path if the sandboxed
    iframe blocks the file download.
 4. Editing inventory / settings auto-recalculates when results are shown.
Also fixed: Euro pallet selection was ignored (math always used GMA 48x40).
R36 (Nov 20 2026): consolidated packing swapped from volume-sum greedy
(82% fudge) to extreme-point first-fit decreasing with real 3D placement.
R37-R39 (Nov 20 2026): click a carton card for a detail modal: dimensions,
contents and a top-down SVG layout drawn from the real placement data
(consolidated cuboids, case-pack layer grid).
"""
import pathlib

SRC = pathlib.Path('/home/hatch/workspace/fba-pack-master/original/index.html')
DST = pathlib.Path('/home/hatch/workspace/fba-pack-master/fixed/index.html')
html = SRC.read_text()


def rep(old, new, count=1):
    global html
    n = html.count(old)
    assert n == count, f'expected {count}x, found {n}x: {old[:90]!r}'
    html = html.replace(old, new)


# --- R1: toast + toggle CSS ---
rep("""</style>
</head>""", """#toast {
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translateX(-50%) translateY(20px);
  background: #182234;
  border: 1px solid var(--surface-border);
  color: var(--text);
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  opacity: 0;
  pointer-events: none;
  transition: all 0.25s ease;
  z-index: 1000;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  max-width: 90vw;
  text-align: center;
}
#toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
#toast.error { border-color: var(--danger); color: #fca5a5; }
#toast.success { border-color: var(--success); color: #a7f3d0; }
.toggle-group { flex-wrap: wrap; }
.toggle-group .toggle-btn { line-height: 1.35; }
</style>
</head>""")

# --- R2: strategy select -> toggle group ---
rep("""    <div class="form-group">
      <label>Packing Strategy</label>
      <select id="packingStrategy">
        <option value="consolidated">Consolidated Mixed SKUs (Fewest Boxes)</option>
        <option value="casepack">Case-Packed (Uniform Single SKU per Carton)</option>
      </select>
    </div>""", """    <div class="form-group">
      <label>Packing Strategy</label>
      <div class="toggle-group">
        <button class="toggle-btn active" id="stratConsolidated">Consolidated Mixed SKUs</button>
        <button class="toggle-btn" id="stratCasepack">Case-Packed (Single SKU)</button>
      </div>
    </div>""")

# --- R3: box source select -> toggle group ---
rep("""    <div class="form-group">
      <label>Box Selection Source</label>
      <select id="boxSelectionMode">
        <option value="standard">Amazon Standard Compliant Boxes</option>
        <option value="warehouse">Warehouse Shelf Inventory (Custom Flock)</option>
        <option value="autosize">Auto-Calculate Ideal Carton Size</option>
      </select>
    </div>""", """    <div class="form-group">
      <label>Box Selection Source</label>
      <div class="toggle-group">
        <button class="toggle-btn active" id="boxSrcStandard">Amazon Standard Boxes</button>
        <button class="toggle-btn" id="boxSrcWarehouse">Warehouse Flock</button>
        <button class="toggle-btn" id="boxSrcAutosize">Auto-Calculate Size</button>
      </div>
    </div>""")

# --- R4: pallet selects -> toggle groups ---
rep("""      <div class="form-group">
        <label>Pallet Base Standard</label>
        <select id="palletStandard">
          <option value="gma">Standard GMA Pallet (48" x 40" x 6")</option>
          <option value="euro">Euro Pallet (120cm x 80cm)</option>
        </select>
      </div>
      <div class="form-group">
        <label>Max Pallet Height (Inc. 6" Pallet)</label>
        <select id="palletMaxHeight">
          <option value="72">72 Inches (Amazon Standard Limit)</option>
          <option value="60">60 Inches (Double-Stackable Limit)</option>
          <option value="50">50 Inches (Heavy / Bulk)</option>
        </select>
      </div>""", """      <div class="form-group">
        <label>Pallet Base Standard</label>
        <div class="toggle-group">
          <button class="toggle-btn active" id="palletGma">GMA 48" x 40"</button>
          <button class="toggle-btn" id="palletEuro">Euro 120 x 80 cm</button>
        </div>
      </div>
      <div class="form-group">
        <label>Max Pallet Height (Inc. 6" Pallet)</label>
        <div class="toggle-group">
          <button class="toggle-btn active" id="palletH72">72 in (Standard)</button>
          <button class="toggle-btn" id="palletH60">60 in (Stackable)</button>
          <button class="toggle-btn" id="palletH50">50 in (Heavy)</button>
        </div>
      </div>""")

# --- R5: pallet ceiling note gets an id ---
rep("""<span style="font-size:10px; color:var(--text-dim);">Amazon FBA absolute ceiling: 1,500 lbs</span>""",
    """<span id="palletCeilingNote" style="font-size:10px; color:var(--text-dim);">Amazon FBA absolute ceiling: 1,500 lbs</span>""")

# --- R6: min carton size gets an id ---
rep("""<div>• Min carton size: <b>6" x 4" x 1"</b> (for Amazon barcodes)</div>""",
    """<div>• Min carton size: <b id="ruleMinSize">6" x 4" x 1"</b> (for Amazon barcodes)</div>""")

# --- R7: Copy CSV button ---
rep("""          <button class="btn" id="btnCopyManifest">Copy Box Manifest</button>
          <button class="btn btn-accent" id="btnExportCsv">Download Amazon 2D CSV</button>""",
    """          <button class="btn" id="btnCopyManifest">Copy Box Manifest</button>
          <button class="btn" id="btnCopyCsv">Copy CSV</button>
          <button class="btn btn-accent" id="btnExportCsv">Download Amazon 2D CSV</button>""")

# --- R8: toast div ---
rep("""    </div>
  </div>
</div>

<script>""", """    </div>
  </div>
</div>

<div id="toast" role="status" aria-live="polite"></div>

<script>""")

# --- R9: DOM refs for removed selects -> toggle buttons + Copy CSV ---
rep("""const packingStrategySelect = document.getElementById('packingStrategy');""",
    """const stratConsolidatedBtn = document.getElementById('stratConsolidated');
const stratCasepackBtn = document.getElementById('stratCasepack');""")
rep("""const boxSelectionSelect = document.getElementById('boxSelectionMode');""",
    """const boxSrcStandardBtn = document.getElementById('boxSrcStandard');
const boxSrcWarehouseBtn = document.getElementById('boxSrcWarehouse');
const boxSrcAutosizeBtn = document.getElementById('boxSrcAutosize');""")
rep("""const btnExportCsv = document.getElementById('btnExportCsv');""",
    """const btnExportCsv = document.getElementById('btnExportCsv');
const btnCopyCsv = document.getElementById('btnCopyCsv');""")

# --- R10: conversion helpers + toast + copy pipeline + recalc, before Unit Labels ---
rep("""// --- Unit Labels ---
function updateUnitLabels() {""", """// --- Unit Conversion ---
// Canonical internal unit is inches / lbs. Display values convert both
// ways so the packing math, guardrails and outputs are always correct
// in either unit system (the original only relabeled the units).
const CM_PER_IN = 2.54;
const KG_PER_LB = 0.45359237;
const isMetric = () => state.units === 'metric';
function trimNum(v) { return parseFloat(v.toFixed(2)); }
function lenToDisplay(vIn) { return isMetric() ? Math.round(vIn * CM_PER_IN * 10) / 10 : trimNum(vIn); }
function wtToDisplay(vLb) { return isMetric() ? Math.round(vLb * KG_PER_LB * 100) / 100 : trimNum(vLb); }
function lenToStorage(vDisp) { return isMetric() ? vDisp / CM_PER_IN : vDisp; }
function wtToStorage(vDisp) { return isMetric() ? vDisp / KG_PER_LB : vDisp; }
function fmtLen(vIn) { return isMetric() ? `${lenToDisplay(vIn)} cm` : `${trimNum(vIn)}"`; }
function fmtLenShort(vIn) { return isMetric() ? `${lenToDisplay(vIn)}cm` : `${trimNum(vIn)}"`; }
function fmtWt(vLb) { return isMetric() ? `${wtToDisplay(vLb)} kg` : `${trimNum(vLb)} lbs`; }

// --- Toast feedback ---
let toastTimer = null;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'show ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = ''; }, 3200);
}

// --- Clipboard with sandbox fallbacks ---
// The Bankr iframe runs at null origin, where navigator.clipboard can be
// blocked with no error surfaced. Prefer the host-mediated bankr.copy(),
// then navigator.clipboard, then a textarea + execCommand fallback.
async function copyTextToClipboard(text) {
  try {
    if (window.bankr && typeof window.bankr.copy === 'function') {
      await window.bankr.copy(text);
      return true;
    }
  } catch (e) { /* fall through */ }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) { /* fall through */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch (e) { return false; }
}

// --- Recalculate outputs when inputs change (only if results are shown) ---
function maybeRecalculate() {
  if (!state.packingResult) return;
  if (state.inventory.length === 0) {
    state.packingResult = null;
    resultsPanel.style.display = 'none';
    return;
  }
  calculatePacking();
}

function syncPalletWeightInput() {
  const el = document.getElementById('palletMaxWeight');
  if (!el) return;
  el.value = wtToDisplay(state.pallet.maxWeight);
  el.step = isMetric() ? '25' : '50';
  el.min = isMetric() ? 227 : 500;
  el.max = isMetric() ? 997 : 2200;
}

function setUnits(u) {
  if (state.units === u) return;
  state.units = u;
  btnImperial.classList.toggle('active', u === 'imperial');
  btnMetric.classList.toggle('active', u === 'metric');
  updateUnitLabels();
  renderInventoryTable();
  renderCustomBoxes();
  syncPalletWeightInput();
  maybeRecalculate();
}

// --- Unit Labels ---
function updateUnitLabels() {""")

# --- R11: updateUnitLabels also converts min size + ceiling note ---
rep("""  document.getElementById('ruleSide').textContent = isImp ? '25.0 in' : '63.5 cm';
  document.getElementById('ruleWeight').textContent = isImp ? '50.0 lbs' : '22.6 kg';
}""", """  document.getElementById('ruleSide').textContent = isImp ? '25.0 in' : '63.5 cm';
  document.getElementById('ruleWeight').textContent = isImp ? '50.0 lbs' : '22.6 kg';
  document.getElementById('ruleMinSize').textContent = isImp ? '6" x 4" x 1"' : '15.2 cm x 10.2 cm x 2.5 cm';
  document.getElementById('palletCeilingNote').textContent = isImp ? 'Amazon FBA absolute ceiling: 1,500 lbs' : 'Amazon FBA absolute ceiling: 680.4 kg';
}""")

# --- R12: mode toggles recalculate (pallet plan depends on mode) ---
rep("""  if (state.packingResult) renderResults();
});""", """  maybeRecalculate();
});""", count=2)

# --- R13: strategy toggle buttons ---
rep("""packingStrategySelect.addEventListener('change', (e) => {
  state.strategy = e.target.value;
});""", """function setStrategy(s) {
  state.strategy = s;
  stratConsolidatedBtn.classList.toggle('active', s === 'consolidated');
  stratCasepackBtn.classList.toggle('active', s === 'casepack');
  maybeRecalculate();
}
stratConsolidatedBtn.addEventListener('click', () => setStrategy('consolidated'));
stratCasepackBtn.addEventListener('click', () => setStrategy('casepack'));""")

# --- R14: unit toggles use setUnits ---
rep("""btnImperial.addEventListener('click', () => {
  if (state.units !== 'imperial') {
    state.units = 'imperial';
    btnImperial.classList.add('active');
    btnMetric.classList.remove('active');
    updateUnitLabels();
  }
});

btnMetric.addEventListener('click', () => {
  if (state.units !== 'metric') {
    state.units = 'metric';
    btnMetric.classList.add('active');
    btnImperial.classList.remove('active');
    updateUnitLabels();
  }
});""", """btnImperial.addEventListener('click', () => setUnits('imperial'));
btnMetric.addEventListener('click', () => setUnits('metric'));""")

# --- R15: box source toggle buttons ---
rep("""boxSelectionSelect.addEventListener('change', (e) => {
  state.boxSelection = e.target.value;
  warehouseFlockSection.style.display = state.boxSelection === 'warehouse' ? 'block' : 'none';
});""", """function setBoxSelection(s) {
  state.boxSelection = s;
  boxSrcStandardBtn.classList.toggle('active', s === 'standard');
  boxSrcWarehouseBtn.classList.toggle('active', s === 'warehouse');
  boxSrcAutosizeBtn.classList.toggle('active', s === 'autosize');
  warehouseFlockSection.style.display = s === 'warehouse' ? 'block' : 'none';
  maybeRecalculate();
}
boxSrcStandardBtn.addEventListener('click', () => setBoxSelection('standard'));
boxSrcWarehouseBtn.addEventListener('click', () => setBoxSelection('warehouse'));
boxSrcAutosizeBtn.addEventListener('click', () => setBoxSelection('autosize'));""")

# --- R16: custom box editor shows display units ---
rep("""      <input type="number" value="${b.l}" class="table-input" step="0.5" onchange="updateBox(${idx}, 'l', parseFloat(this.value)||0)">""",
    """      <input type="number" value="${lenToDisplay(b.l)}" class="table-input" step="0.5" onchange="updateBox(${idx}, 'l', parseFloat(this.value)||0)">""")
rep("""      <input type="number" value="${b.w}" class="table-input" step="0.5" onchange="updateBox(${idx}, 'w', parseFloat(this.value)||0)">""",
    """      <input type="number" value="${lenToDisplay(b.w)}" class="table-input" step="0.5" onchange="updateBox(${idx}, 'w', parseFloat(this.value)||0)">""")
rep("""      <input type="number" value="${b.h}" class="table-input" step="0.5" onchange="updateBox(${idx}, 'h', parseFloat(this.value)||0)">""",
    """      <input type="number" value="${lenToDisplay(b.h)}" class="table-input" step="0.5" onchange="updateBox(${idx}, 'h', parseFloat(this.value)||0)">""")
rep("""      <input type="number" value="${b.tare}" class="table-input" step="0.1" onchange="updateBox(${idx}, 'tare', parseFloat(this.value)||0)">""",
    """      <input type="number" value="${wtToDisplay(b.tare)}" class="table-input" step="0.1" onchange="updateBox(${idx}, 'tare', parseFloat(this.value)||0)">""")

# --- R17: updateBox converts back to imperial ---
rep("""window.updateBox = (idx, field, val) => {
  state.customBoxes[idx][field] = val;
};""", """window.updateBox = (idx, field, val) => {
  if (!state.customBoxes[idx]) return;
  if (field === 'l' || field === 'w' || field === 'h') state.customBoxes[idx][field] = lenToStorage(val);
  else if (field === 'tare') state.customBoxes[idx][field] = wtToStorage(val);
  else state.customBoxes[idx][field] = val;
  maybeRecalculate();
};""")

# --- R18: inventory table shows display units ---
rep("""      <td><input type="number" class="table-input" step="0.1" value="${item.l}" onchange="updateInventoryItem(${idx}, 'l', parseFloat(this.value)||0)"></td>""",
    """      <td><input type="number" class="table-input" step="0.1" value="${lenToDisplay(item.l)}" onchange="updateInventoryItem(${idx}, 'l', parseFloat(this.value)||0)"></td>""")
rep("""      <td><input type="number" class="table-input" step="0.1" value="${item.w}" onchange="updateInventoryItem(${idx}, 'w', parseFloat(this.value)||0)"></td>""",
    """      <td><input type="number" class="table-input" step="0.1" value="${lenToDisplay(item.w)}" onchange="updateInventoryItem(${idx}, 'w', parseFloat(this.value)||0)"></td>""")
rep("""      <td><input type="number" class="table-input" step="0.1" value="${item.h}" onchange="updateInventoryItem(${idx}, 'h', parseFloat(this.value)||0)"></td>""",
    """      <td><input type="number" class="table-input" step="0.1" value="${lenToDisplay(item.h)}" onchange="updateInventoryItem(${idx}, 'h', parseFloat(this.value)||0)"></td>""")
rep("""      <td><input type="number" class="table-input" step="0.01" value="${item.wt}" onchange="updateInventoryItem(${idx}, 'wt', parseFloat(this.value)||0)"></td>""",
    """      <td><input type="number" class="table-input" step="0.01" value="${wtToDisplay(item.wt)}" onchange="updateInventoryItem(${idx}, 'wt', parseFloat(this.value)||0)"></td>""")

# --- R19: updateInventoryItem converts back to imperial ---
rep("""window.updateInventoryItem = (idx, field, val) => {
  if (state.inventory[idx]) state.inventory[idx][field] = val;
};""", """window.updateInventoryItem = (idx, field, val) => {
  if (!state.inventory[idx]) return;
  if (field === 'l' || field === 'w' || field === 'h') state.inventory[idx][field] = lenToStorage(val);
  else if (field === 'wt') state.inventory[idx][field] = wtToStorage(val);
  else state.inventory[idx][field] = val;
  maybeRecalculate();
};""")

# --- R20: delete row recalcs ---
rep("""window.deleteInventoryItem = (idx) => {
  state.inventory.splice(idx, 1);
  renderInventoryTable();
};""", """window.deleteInventoryItem = (idx) => {
  state.inventory.splice(idx, 1);
  renderInventoryTable();
  maybeRecalculate();
};""")

# --- R21: add row recalcs ---
rep("""btnAddRow.addEventListener('click', () => {
  state.inventory.push({ sku: `SKU-${state.inventory.length + 1}`, l: 8, w: 6, h: 4, wt: 1.0, qty: 20 });
  renderInventoryTable();
});""", """btnAddRow.addEventListener('click', () => {
  state.inventory.push({ sku: `SKU-${state.inventory.length + 1}`, l: 8, w: 6, h: 4, wt: 1.0, qty: 20 });
  renderInventoryTable();
  maybeRecalculate();
});""")

# --- R22: clear also drops the stored result ---
rep("""btnClearTable.addEventListener('click', () => {
  state.inventory = [];
  renderInventoryTable();
  resultsPanel.style.display = 'none';
});""", """btnClearTable.addEventListener('click', () => {
  state.inventory = [];
  state.packingResult = null;
  renderInventoryTable();
  resultsPanel.style.display = 'none';
});""")

# --- R23: pasted/file values are in display units -> convert ---
rep("""    const sku = cols[0] || `SKU-${newItems.length + 1}`;
    const l = parseFloat(cols[1]) || 6;
    const w = parseFloat(cols[2]) || 4;
    const h = parseFloat(cols[3]) || 2;
    const wt = parseFloat(cols[4]) || 1;
    const qty = parseInt(cols[5]) || 10;""", """    const sku = cols[0] || `SKU-${newItems.length + 1}`;
    const l = lenToStorage(parseFloat(cols[1]) || 6);
    const w = lenToStorage(parseFloat(cols[2]) || 4);
    const h = lenToStorage(parseFloat(cols[3]) || 2);
    const wt = wtToStorage(parseFloat(cols[4]) || 1);
    const qty = parseInt(cols[5]) || 10;""")

# --- R24: pallet math uses state + honors Euro dimensions ---
rep("""  let palletData = null;
  if (state.mode === 'freight') {
    const palletLength = 48; // inches
    const palletWidth = 40;  // inches
    const palletBaseHeight = 6; // inches
    const palletBaseWeight = 45; // lbs (standard wooden GMA pallet)
    const maxHeight = parseFloat(document.getElementById('palletMaxHeight').value) || 72;
    const maxWeight = parseFloat(document.getElementById('palletMaxWeight').value) || 1500;""",
    """  let palletData = null;
  if (state.mode === 'freight') {
    const isEuro = state.pallet.standard === 'euro';
    const palletLength = isEuro ? 47 : 48; // inches (Euro 120cm ~ 47")
    const palletWidth = isEuro ? 31 : 40;  // inches (Euro 80cm ~ 31")
    const palletBaseHeight = 6; // inches
    const palletBaseWeight = 45; // lbs (standard wooden pallet)
    const maxHeight = state.pallet.maxHeight;
    const maxWeight = state.pallet.maxWeight;""")

# --- R25: pallet warnings in display units ---
rep("""    if (stackHeight > maxHeight) {
      warnings.push(`Pallet height calculated (${stackHeight}") exceeds selected limit (${maxHeight}"). Reduce layer count.`);
    }
    if (avgPalletWeight > maxWeight) {
      warnings.push(`Pallet weight (${avgPalletWeight} lbs) exceeds Amazon 1,500 lb limit! Requires splitting across additional pallets.`);
    }""", """    if (stackHeight > maxHeight) {
      warnings.push(`Pallet height calculated (${fmtLen(stackHeight)}) exceeds selected limit (${fmtLen(maxHeight)}). Reduce layer count.`);
    }
    if (avgPalletWeight > maxWeight) {
      warnings.push(`Pallet weight (${fmtWt(avgPalletWeight)}) exceeds Amazon ${fmtWt(maxWeight)} limit! Requires splitting across additional pallets.`);
    }""")

# --- R26: pallet data carries its standard label ---
rep("""    palletData = {
      standard: '48" x 40" GMA Standard Wooden Pallet',""",
    """    palletData = {
      standard: isEuro ? '47" x 31" Euro Pallet' : '48" x 40" GMA Standard Wooden Pallet',
      palletLabel: isEuro ? 'Euro' : 'GMA',""")

# --- R27: oversize / overweight warnings in display units ---
rep("""    if (Math.max(item.l, item.w, item.h) > MAX_SIDE) {
      warnings.push(`SKU <b>${item.sku}</b> length exceeds 25". Amazon requires Single-Oversize handling or Freight classification.`);
    }
    if (item.wt > MAX_SPD_WT) {
      warnings.push(`SKU <b>${item.sku}</b> weight exceeds 50 lbs. Requires Team Lift label and special LTL routing.`);
    }""", """    if (Math.max(item.l, item.w, item.h) > MAX_SIDE) {
      warnings.push(`SKU <b>${item.sku}</b> length exceeds ${fmtLen(MAX_SIDE)}. Amazon requires Single-Oversize handling or Freight classification.`);
    }
    if (item.wt > MAX_SPD_WT) {
      warnings.push(`SKU <b>${item.sku}</b> weight exceeds ${fmtWt(MAX_SPD_WT)}. Requires Team Lift label and special LTL routing.`);
    }""")

# --- R28: gross weight stat converts ---
rep("""      <span class="stat-val">${Math.round(totalNetWeight)} ${isImp ? 'lbs' : 'kg'}</span>""",
    """      <span class="stat-val">${isImp ? Math.round(totalNetWeight) : wtToDisplay(totalNetWeight).toFixed(1)} ${isImp ? 'lbs' : 'kg'}</span>""")

# --- R29: pallet output converts ---
rep("""            <span class="badge badge-ok">${p.totalPallets} GMA ${p.totalPallets === 1 ? 'Pallet' : 'Pallets'}</span>""",
    """            <span class="badge badge-ok">${p.totalPallets} ${p.palletLabel} ${p.totalPallets === 1 ? 'Pallet' : 'Pallets'}</span>""")
rep("""          <div><span style="color:var(--text-muted);">Stack Height:</span> <br><b style="color:#fff;">${p.stackHeight}" / ${p.maxHeight}" Max</b></div>
          <div><span style="color:var(--text-muted);">Avg Pallet Weight:</span> <br><b style="color:#fff;">${p.avgPalletWeight} lbs</b></div>
          <div><span style="color:var(--text-muted);">Total Freight Weight:</span> <br><b style="color:#fff;">${p.totalShipmentWeight} lbs</b></div>""",
    """          <div><span style="color:var(--text-muted);">Stack Height:</span> <br><b style="color:#fff;">${fmtLen(p.stackHeight)} / ${fmtLen(p.maxHeight)} Max</b></div>
          <div><span style="color:var(--text-muted);">Avg Pallet Weight:</span> <br><b style="color:#fff;">${fmtWt(p.avgPalletWeight)}</b></div>
          <div><span style="color:var(--text-muted);">Total Freight Weight:</span> <br><b style="color:#fff;">${fmtWt(p.totalShipmentWeight)}</b></div>""")

# --- R30: carton dims + weight convert ---
rep("""          ${box.l}" &times; ${box.w}" &times; ${box.h}" | <b>${box.weight} ${isImp ? 'lbs' : 'kg'}</b>""",
    """          ${fmtLen(box.l)} &times; ${fmtLen(box.w)} &times; ${fmtLen(box.h)} | <b>${fmtWt(box.weight)}</b>""")

# --- R31: tare converts ---
rep("""        <span>Carton Tare: <b>${box.tare} ${isImp ? 'lbs' : 'kg'}</b></span>""",
    """        <span>Carton Tare: <b>${fmtWt(box.tare)}</b></span>""")

# --- R32: copy manifest with feedback + display units ---
rep("""btnCopyManifest.addEventListener('click', () => {
  if (!state.packingResult) return;
  let text = `AMAZON FBA CARTON MANIFEST\\n`;
  text += `Generated: ${new Date().toLocaleDateString()}\\n`;
  text += `Total Cartons: ${state.packingResult.boxes.length}\\n`;
  text += `Strategy: ${state.strategy}\\n`;
  if (state.packingResult.pallet) {
    text += `Pallets: ${state.packingResult.pallet.totalPallets} (Ti: ${state.packingResult.pallet.ti}, Hi: ${state.packingResult.pallet.hi})\\n`;
  }
  text += `--------------------------------------------------\\n`;

  state.packingResult.boxes.forEach((b, idx) => {
    text += `Box #${idx + 1} (${b.l}x${b.w}x${b.h} in, ${b.weight} lbs):\\n`;
    b.items.forEach(it => {
      text += `  - ${it.sku}: ${it.count} units\\n`;
    });
  });

  navigator.clipboard.writeText(text).then(() => {
    const orig = btnCopyManifest.textContent;
    btnCopyManifest.textContent = 'Copied to Clipboard!';
    setTimeout(() => btnCopyManifest.textContent = orig, 2000);
  });
});""", """btnCopyManifest.addEventListener('click', async () => {
  if (!state.packingResult) return;
  let text = `AMAZON FBA CARTON MANIFEST\\n`;
  text += `Generated: ${new Date().toLocaleDateString()}\\n`;
  text += `Units: ${isMetric() ? 'cm / kg' : 'in / lbs'}\\n`;
  text += `Total Cartons: ${state.packingResult.boxes.length}\\n`;
  text += `Strategy: ${state.strategy}\\n`;
  if (state.packingResult.pallet) {
    text += `Pallets: ${state.packingResult.pallet.totalPallets} (Ti: ${state.packingResult.pallet.ti}, Hi: ${state.packingResult.pallet.hi})\\n`;
  }
  text += `--------------------------------------------------\\n`;

  state.packingResult.boxes.forEach((b, idx) => {
    text += `Box #${idx + 1} (${fmtLenShort(b.l)}x${fmtLenShort(b.w)}x${fmtLenShort(b.h)}, ${fmtWt(b.weight)}):\\n`;
    b.items.forEach(it => {
      text += `  - ${it.sku}: ${it.count} units\\n`;
    });
  });

  const ok = await copyTextToClipboard(text);
  if (ok) {
    const orig = btnCopyManifest.textContent;
    btnCopyManifest.textContent = 'Copied to Clipboard!';
    setTimeout(() => btnCopyManifest.textContent = orig, 2000);
    showToast('Manifest copied to clipboard', 'success');
  } else {
    showToast('Copy blocked in this view. Select the manifest text manually.', 'error');
  }
});""")

# --- R33: CSV builder shared by download + copy, with toast feedback ---
rep("""btnExportCsv.addEventListener('click', () => {
  if (!state.packingResult) return;
  // Amazon 2D Barcode Box Content CSV format standard
  let csv = "Box Name,Length (in),Width (in),Height (in),Weight (lbs),SKU,Units Packed\\n";
  state.packingResult.boxes.forEach((b, idx) => {
    b.items.forEach(it => {
      csv += `"Box ${idx + 1}",${b.l},${b.w},${b.h},${b.weight},"${it.sku}",${it.count}\\n`;
    });
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fba-box-manifest-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});""", """// Amazon 2D Barcode Box Content CSV. Amazon's format is inches/lbs, so the
// export stays imperial whatever the display units are.
function buildBoxCsv() {
  let csv = "Box Name,Length (in),Width (in),Height (in),Weight (lbs),SKU,Units Packed\\n";
  state.packingResult.boxes.forEach((b, idx) => {
    b.items.forEach(it => {
      csv += `"Box ${idx + 1}",${b.l},${b.w},${b.h},${b.weight},"${it.sku}",${it.count}\\n`;
    });
  });
  return csv;
}

btnExportCsv.addEventListener('click', () => {
  if (!state.packingResult) return;
  const csv = buildBoxCsv();
  const filename = `fba-box-manifest-${Date.now()}.csv`;

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`CSV download started: ${filename} (inches/lbs, Amazon format)`, 'success');
});

btnCopyCsv.addEventListener('click', async () => {
  if (!state.packingResult) return;
  const ok = await copyTextToClipboard(buildBoxCsv());
  showToast(ok ? 'CSV copied to clipboard (inches/lbs, Amazon format)' : 'Copy blocked in this view.', ok ? 'success' : 'error');
});""")

# --- R34: freight / pallet control wiring ---
rep("""renderCustomBoxes();

// --- Inventory Table Rows ---""", """renderCustomBoxes();

// --- Freight / Pallet Controls ---
function setPalletStandard(s) {
  state.pallet.standard = s;
  document.getElementById('palletGma').classList.toggle('active', s === 'gma');
  document.getElementById('palletEuro').classList.toggle('active', s === 'euro');
  maybeRecalculate();
}
document.getElementById('palletGma').addEventListener('click', () => setPalletStandard('gma'));
document.getElementById('palletEuro').addEventListener('click', () => setPalletStandard('euro'));

function setPalletHeight(h) {
  state.pallet.maxHeight = h;
  ['72', '60', '50'].forEach(v => document.getElementById('palletH' + v).classList.toggle('active', parseInt(v) === h));
  maybeRecalculate();
}
document.getElementById('palletH72').addEventListener('click', () => setPalletHeight(72));
document.getElementById('palletH60').addEventListener('click', () => setPalletHeight(60));
document.getElementById('palletH50').addEventListener('click', () => setPalletHeight(50));

document.getElementById('palletMaxWeight').addEventListener('change', (e) => {
  const v = parseFloat(e.target.value);
  state.pallet.maxWeight = Math.round(wtToStorage(isNaN(v) ? 1500 : v));
  syncPalletWeightInput();
  maybeRecalculate();
});

// --- Inventory Table Rows ---""")

# --- R35: init syncs unit labels + pallet weight display ---
rep("""// Initialize Sample on first load
state.inventory = JSON.parse(JSON.stringify(sampleCatalog));
renderInventoryTable();
calculatePacking();""", """// Initialize Sample on first load
state.inventory = JSON.parse(JSON.stringify(sampleCatalog));
renderInventoryTable();
updateUnitLabels();
syncPalletWeightInput();
calculatePacking();""")

# --- R36: consolidated packing -> extreme-point first-fit decreasing ---
# Replaces the volume-sum greedy fill (82% fudge factor, no 3D geometry
# check) with real cuboid placement: units sorted by volume desc, each
# placed at the lowest free extreme point in one of its six orientations,
# weight cap as a hard limit. Utilization is measured from placed volume.
_START = "  } else {\n    // Consolidated Mode: 3D heuristic bin packing (Best Fit Decreasing)"
_END = "  }\n\n  // Calculate Freight / Pallet Configuration"
assert html.count(_START) == 1, 'consolidated block start not found'
assert html.count(_END) == 1, 'consolidated block end not found'
_s = html.index(_START)
_e = html.index(_END) + len("  }\n")
_NEW_CONSOLIDATED = """  } else {
    // Consolidated Mode: first-fit decreasing with extreme-point placement.
    // Every unit is placed as a real 3D cuboid at a free corner point, in
    // one of its six orientations, so the reported utilization is measured
    // from actual placed volume, not a guessed efficiency factor.
    expandedItems.sort((a, b) => b.vol - a.vol || Math.max(b.l, b.w, b.h) - Math.max(a.l, a.w, a.h));

    const orientations = (it) => {
      const [l, w, h] = [it.l, it.w, it.h];
      return [[l, w, h], [l, h, w], [w, l, h], [w, h, l], [h, l, w], [h, w, l]];
    };
    const fitsInBox = (it, b) => {
      const dims = [it.l, it.w, it.h].sort((x, y) => x - y);
      const box = [b.l, b.w, b.h].sort((x, y) => x - y);
      return dims[0] <= box[0] && dims[1] <= box[1] && dims[2] <= box[2];
    };
    const overlaps = (placed, x, y, z, l, w, h) => placed.some(p =>
      x < p.x + p.l && x + l > p.x &&
      y < p.y + p.w && y + w > p.y &&
      z < p.z + p.h && z + h > p.z);

    let unassigned = [...expandedItems];

    while (unassigned.length > 0) {
      // Smallest box that can contain the largest remaining item, in any orientation.
      let chosenBox = null;
      for (let b of availableBoxes) {
        if (fitsInBox(unassigned[0], b)) { chosenBox = b; break; }
      }
      // Oversize item: no catalogue box holds it. Use the largest box and
      // force-place it alone (already flagged by the oversize warning).
      if (!chosenBox) chosenBox = availableBoxes[availableBoxes.length - 1];

      const boxVol = chosenBox.l * chosenBox.w * chosenBox.h;
      const placed = []; // {x,y,z,l,w,h} cuboids already in this carton
      let points = [{ x: 0, y: 0, z: 0 }]; // extreme points: free corner candidates
      let currentWeight = chosenBox.tare;
      let currentVol = 0;
      const itemsInThisBox = {};
      const remainingUnassigned = [];

      const tryPlace = (item) => {
        if (currentWeight + item.wt > chosenBox.maxWt) return false;
        // Lowest point first (z, then y, then x); first orientation that fits wins.
        const ordered = [...points].sort((a, b) => a.z - b.z || a.y - b.y || a.x - b.x);
        for (let pt of ordered) {
          for (let [l, w, h] of orientations(item)) {
            if (pt.x + l > chosenBox.l || pt.y + w > chosenBox.w || pt.z + h > chosenBox.h) continue;
            if (overlaps(placed, pt.x, pt.y, pt.z, l, w, h)) continue;
            placed.push({ x: pt.x, y: pt.y, z: pt.z, l, w, h });
            points = points.filter(p => p !== pt);
            for (let np of [{ x: pt.x + l, y: pt.y, z: pt.z }, { x: pt.x, y: pt.y + w, z: pt.z }, { x: pt.x, y: pt.y, z: pt.z + h }]) {
              if (np.x <= chosenBox.l && np.y <= chosenBox.w && np.z <= chosenBox.h) points.push(np);
            }
            // Drop duplicates and points that fell inside a placed cuboid
            // (they can never be a placement origin).
            const seen = new Set();
            points = points.filter(p => {
              const k = p.x + ',' + p.y + ',' + p.z;
              if (seen.has(k)) return false;
              seen.add(k);
              return !placed.some(q => p.x >= q.x && p.x < q.x + q.l && p.y >= q.y && p.y < q.y + q.w && p.z >= q.z && p.z < q.z + q.h);
            });
            currentWeight += item.wt;
            currentVol += item.vol;
            itemsInThisBox[item.sku] = (itemsInThisBox[item.sku] || 0) + 1;
            return true;
          }
        }
        return false;
      };

      for (let item of unassigned) {
        if (!tryPlace(item)) remainingUnassigned.push(item);
      }

      // Nothing fit: force the largest remaining item in alone so the loop always advances.
      if (Object.keys(itemsInThisBox).length === 0 && unassigned.length > 0) {
        const forced = unassigned[0];
        const [l, w, h] = orientations(forced)[0];
        placed.push({ x: 0, y: 0, z: 0, l, w, h });
        currentWeight = chosenBox.tare + forced.wt;
        currentVol = forced.vol;
        itemsInThisBox[forced.sku] = 1;
        remainingUnassigned.shift();
      }

      unassigned = remainingUnassigned;

      const itemsSummary = Object.keys(itemsInThisBox).map(sku => ({
        sku,
        count: itemsInThisBox[sku]
      }));

      const util = Math.min(99, Math.round((currentVol / boxVol) * 100));

      boxesPacked.push({
        boxName: chosenBox.name,
        l: chosenBox.l,
        w: chosenBox.w,
        h: chosenBox.h,
        tare: chosenBox.tare,
        weight: Math.round(currentWeight * 100) / 100,
        utilization: util,
        items: itemsSummary,
        mode: 'Consolidated Mixed'
      });
    }
  }
"""
html = html[:_s] + _NEW_CONSOLIDATED + html[_e:]

# --- R37: store placement/layout data per carton for the detail view ---
# Consolidated: tag each placed cuboid with its SKU and keep the array on the box.
rep("placed.push({ x: pt.x, y: pt.y, z: pt.z, l, w, h });",
          "placed.push({ sku: item.sku, x: pt.x, y: pt.y, z: pt.z, l, w, h });")
rep("placed.push({ x: 0, y: 0, z: 0, l, w, h });",
          "placed.push({ sku: forced.sku, x: 0, y: 0, z: 0, l, w, h });")
rep("""        items: itemsSummary,
        mode: 'Consolidated Mixed'""",
          """        items: itemsSummary,
        placed,
        mode: 'Consolidated Mixed'""")
# Case-pack: record the winning layer orientation so the detail view can draw it.
rep("""      while (remainingQty > 0) {
        const countThisBox = Math.min(remainingQty, maxUnitsPerBox);""",
          """      // Winning layer orientation for the detail-view drawing.
      const layerFits = [
        { cols: Math.floor(bestBox.l / item.l), rows: Math.floor(bestBox.w / item.w), il: item.l, iw: item.w, ih: item.h },
        { cols: Math.floor(bestBox.l / item.w), rows: Math.floor(bestBox.w / item.l), il: item.w, iw: item.l, ih: item.h },
        { cols: Math.floor(bestBox.l / item.h), rows: Math.floor(bestBox.w / item.w), il: item.h, iw: item.w, ih: item.l },
      ];
      layerFits.sort((a, b) => (b.cols * b.rows) - (a.cols * a.rows));
      const bestLayer = layerFits[0];
      const caseLayout = { sku: item.sku, itemL: bestLayer.il, itemW: bestLayer.iw, itemH: item.h, cols: bestLayer.cols, rows: bestLayer.rows, layers: Math.max(1, Math.floor(bestBox.h / bestLayer.ih)) };

      while (remainingQty > 0) {
        const countThisBox = Math.min(remainingQty, maxUnitsPerBox);""")
rep("""          items: packedItems,
          mode: 'Case-Pack (Single SKU)'""",
          """          items: packedItems,
          layout: caseLayout,
          mode: 'Case-Pack (Single SKU)'""")

# --- R38: clickable cards + detail modal (CSS + HTML) ---
rep(""".box-card:hover {
  border-color: #4b5563;
}""",
          """.box-card {
  cursor: pointer;
}
.box-card:hover {
  border-color: #3b82f6;
}
.box-card:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
.box-modal-panel {
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  width: 92%;
  max-width: 600px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 16px;
}
.box-svg {
  width: 100%;
  height: auto;
  max-height: 340px;
  background: #0f172a;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}""")
rep("""      <div class="panel-title" style="margin-top:10px; font-size:12px;">Carton Breakdown (<span id="totalBoxCountLabel">0</span> Cartons)</div>""",
          """      <div class="panel-title" style="margin-top:10px; font-size:12px;">Carton Breakdown (<span id="totalBoxCountLabel">0</span> Cartons)</div>
      <div style="font-size:11px; color:var(--text-muted); margin:2px 0 8px;">Click any carton to see its dimensions, contents, and packing layout.</div>""")
rep("""<div id="toast" role="status" aria-live="polite"></div>""",
          """<!-- Carton detail modal -->
<div id="boxModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:1000; justify-content:center; align-items:center;">
  <div class="box-modal-panel">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
      <h3 id="boxModalTitle" style="font-size:14px; color:var(--primary);"></h3>
      <button class="icon-del" id="btnCloseBoxModal" style="font-size:18px; color:var(--text-muted);">&times;</button>
    </div>
    <div id="boxModalBody"></div>
  </div>
</div>

<div id="toast" role="status" aria-live="polite"></div>""")

# --- R39: carton detail view logic ---
rep("""function calculatePacking() {""",
          """function calculatePacking() {
  closeBoxDetail(); // a recalc invalidates any open carton detail""")
rep("""    const card = document.createElement('div');
    card.className = 'box-card';""",
          """    const card = document.createElement('div');
    card.className = 'box-card';
    card.dataset.idx = i;
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Carton ${i + 1} details`);""")
rep("""// --- Manifest Copy & 2D Barcode CSV Export ---""",
          """// --- Carton detail view (click a carton card) ---
const BOX_COLORS = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];
const skuColor = (sku, box) => {
  const skus = [...new Set(box.items.map(it => it.sku))];
  return BOX_COLORS[Math.max(0, skus.indexOf(sku)) % BOX_COLORS.length];
};
const skuShort = (sku) => sku.split('-')[0];
const escHtml = (s) => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function boxLayoutSvg(box) {
  const L = box.l, W = box.w;
  const fs = Math.max(0.9, Math.min(L, W) / 14);
  let rects = `<rect x="0" y="0" width="${L}" height="${W}" fill="#1e293b" stroke="#64748b" stroke-width="0.15"/>`;
  if (box.placed && box.placed.length) {
    rects += box.placed.map(p => {
      const fill = skuColor(p.sku, box);
      const label = `${skuShort(p.sku)} z${fmtLenShort(p.z)}`;
      const showLabel = p.l > 2 && p.w > 1.2;
      return `<rect x="${p.x}" y="${p.y}" width="${p.l}" height="${p.w}" fill="${fill}" fill-opacity="0.55" stroke="${fill}" stroke-width="0.12"><title>${escHtml(p.sku)} ${fmtLen(p.l)} x ${fmtLen(p.w)} at ${fmtLenShort(p.z)} high</title></rect>` +
        (showLabel ? `<text x="${p.x + p.l / 2}" y="${p.y + p.w / 2}" font-size="${fs}" text-anchor="middle" dominant-baseline="middle" fill="#fff">${escHtml(label)}</text>` : '');
    }).join('');
  } else if (box.layout) {
    const lay = box.layout;
    const fill = skuColor(lay.sku, box);
    for (let r = 0; r < lay.rows; r++) {
      for (let c = 0; c < lay.cols; c++) {
        rects += `<rect x="${c * lay.itemL}" y="${r * lay.itemW}" width="${lay.itemL}" height="${lay.itemW}" fill="${fill}" fill-opacity="0.55" stroke="${fill}" stroke-width="0.12"/>`;
      }
    }
    if (lay.cols > 0 && lay.rows > 0) {
      rects += `<text x="${L / 2}" y="${W / 2}" font-size="${fs * 1.4}" text-anchor="middle" dominant-baseline="middle" fill="#fff">${escHtml(skuShort(lay.sku))} &times; ${lay.layers} layer${lay.layers === 1 ? '' : 's'}</text>`;
    }
  }
  return `<svg class="box-svg" viewBox="0 0 ${L} ${W}" role="img" aria-label="Top-down packing layout">${rects}</svg>`;
}

function openBoxDetail(idx) {
  const box = state.packingResult && state.packingResult.boxes[idx];
  if (!box) return;
  document.getElementById('boxModalTitle').textContent = `Carton #${idx + 1} \\u2014 ${box.boxName}`;
  const rows = box.items.map(it => {
    const inv = state.inventory.find(x => x.sku === it.sku);
    const dims = inv ? `${fmtLen(inv.l)} \\u00d7 ${fmtLen(inv.w)} \\u00d7 ${fmtLen(inv.h)} each` : (it.l ? `${fmtLen(it.l)} \\u00d7 ${fmtLen(it.w)} \\u00d7 ${fmtLen(it.h)} each` : '');
    const wt = inv ? fmtWt(inv.wt) : (it.wt ? fmtWt(it.wt) : '');
    const detail = [dims, wt].filter(Boolean).join(', ');
    return `<div class="box-item-row"><span style="font-family:var(--font-mono); color:var(--text);">${escHtml(it.sku)}${detail ? ` <span style="color:var(--text-muted); font-weight:400;">(${detail})</span>` : ''}</span><span style="font-weight:700; color:var(--primary);">${it.count} units</span></div>`;
  }).join('');
  const legend = box.items.map(it => `<span style="display:inline-flex; align-items:center; gap:4px; margin-right:10px;"><span style="display:inline-block; width:10px; height:10px; border-radius:2px; background:${skuColor(it.sku, box)};"></span>${escHtml(skuShort(it.sku))} (${it.count})</span>`).join('');
  const layerNote = box.placed
    ? 'Top-down view. Each rectangle is one unit; the z number is the height where it sits in the carton.'
    : (box.layout ? `Top-down view of one layer (${box.layout.cols} \\u00d7 ${box.layout.rows} units), stacked ${box.layout.layers} layer${box.layout.layers === 1 ? '' : 's'} high.` : '');
  document.getElementById('boxModalBody').innerHTML = `
    <div class="box-details" style="margin-bottom:10px;">
      <span>Dimensions: <b>${fmtLen(box.l)} \\u00d7 ${fmtLen(box.w)} \\u00d7 ${fmtLen(box.h)}</b></span>
      <span>Gross Weight: <b>${fmtWt(box.weight)}</b></span>
      <span>Space Utilization: <b>${box.utilization}%</b></span>
      <span>Packing Mode: <b>${box.mode}</b></span>
    </div>
    ${boxLayoutSvg(box)}
    <div style="font-size:11px; color:var(--text-muted); margin:6px 0 10px;">${layerNote}</div>
    <div class="box-items-list">${rows}</div>
    <div style="font-size:11px; color:var(--text-muted); margin-top:8px;">${legend}</div>`;
  document.getElementById('boxModal').style.display = 'flex';
}

function closeBoxDetail() {
  const m = document.getElementById('boxModal');
  if (m) m.style.display = 'none';
}

boxListContainer.addEventListener('click', (e) => {
  const card = e.target.closest('.box-card');
  if (card) openBoxDetail(+card.dataset.idx);
});
boxListContainer.addEventListener('keydown', (e) => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.classList.contains('box-card')) {
    e.preventDefault();
    openBoxDetail(+e.target.dataset.idx);
  }
});
document.getElementById('btnCloseBoxModal').addEventListener('click', closeBoxDetail);
document.getElementById('boxModal').addEventListener('click', (e) => {
  if (e.target.id === 'boxModal') closeBoxDetail();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeBoxDetail();
});

// --- Manifest Copy & 2D Barcode CSV Export ---""")

DST.write_text(html)
# Repo-root copy: the fixed app itself, so GitHub Pages serves it at /.
ROOT = pathlib.Path('/home/hatch/workspace/fba-pack-master/index.html')
ROOT.write_text(html)
print('fixed bytes:', len(html), 'lines:', html.count('\n') + 1)
