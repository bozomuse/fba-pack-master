import { JSDOM } from 'jsdom';
import fs from 'node:fs';

const mode = process.argv[2] || 'fixed'; // 'fixed' | 'original'
const file = mode === 'fixed'
  ? '/home/hatch/workspace/fba-pack-master/fixed/index.html'
  : '/home/hatch/workspace/fba-pack-master/original/index.html';
const html = fs.readFileSync(file, 'utf8');

let failures = 0;
function check(name, cond, extra = '') {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  [' + extra + ']' : ''}`);
  if (!cond) failures++;
}

const tick = () => new Promise((r) => setTimeout(r, 10));

async function main() {
  let capturedClipboard = null;
  let bankrCopyCalled = false;
  let execCommandResult = true;
  const alerts = [];

  const dom = new JSDOM(html, {
    url: 'https://example.com/',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(window) {
      window.alert = (m) => alerts.push(m);
      window.document.execCommand = () => execCommandResult;
      Object.defineProperty(window.navigator, 'clipboard', {
        value: { writeText: async (t) => { capturedClipboard = t; } },
        configurable: true,
      });
      window.bankr = { copy: async (t) => { bankrCopyCalled = true; capturedClipboard = t; } };
      window.URL.createObjectURL = () => 'blob:test';
      window.URL.revokeObjectURL = () => {};
    },
  });
  const { window } = dom;
  const { document } = window;
  await tick();

  const statVals = () => [...document.querySelectorAll('#statsGrid .stat-val')].map((e) => e.textContent.trim());
  const toast = () => document.getElementById('toast');
  const click = (id) => document.getElementById(id).click();
  const cartonCount = () => document.getElementById('totalBoxCountLabel').textContent.trim();
  const firstCartonHeader = () => document.querySelector('.box-card .box-header')?.textContent.replace(/\s+/g, ' ').trim() || '';

  if (mode === 'original') {
    // Bug-reproduction checks on the ORIGINAL (expect buggy behavior).
    check('orig: initial imperial 38 cartons / 241 lbs / 80%', JSON.stringify(statVals()) === JSON.stringify(['38', '275', '241 lbs', '80%']), statVals().join(','));
    click('unitMetric');
    await tick();
    click('btnCalculate'); // original only relabels on recalc; toggle alone never re-renders
    await tick();
    check('orig BUG: metric gross reads 241 kg (lb number relabeled)', statVals()[2] === '241 kg', statVals()[2]);
    check('orig BUG: carton dims still inches in metric', firstCartonHeader().includes('"') && !firstCartonHeader().includes('cm'), firstCartonHeader().slice(0, 80));
    check('orig BUG: native strategy select present', !!document.getElementById('packingStrategy'));
    check('orig BUG: no toast element', !toast());
    console.log(failures === 0 ? 'ORIGINAL BUGS REPRODUCED' : `${failures} bug-repro check(s) did not match`);
    process.exit(failures ? 1 : 0);
  }

  // ---- FIXED full suite ----
  check('no native <select> remains', document.querySelectorAll('select').length === 0);
  check('strategy toggle buttons exist', !!document.getElementById('stratConsolidated') && !!document.getElementById('stratCasepack'));
  check('toast element exists', !!toast());

  // A. initial imperial (extreme-point placement: 43 honest cartons, not 38 volume-sum ones)
  check('A: initial imperial 43 cartons / 275 units / 244 lbs / 78%', JSON.stringify(statVals()) === JSON.stringify(['43', '275', '244 lbs', '78%']), statVals().join(','));

  // B/C. metric mode: real conversion + parity
  click('unitMetric');
  await tick();
  check('B: metric gross is 110.5 kg (243.7 lb unrounded total converted)', statVals()[2] === '110.5 kg', statVals()[2]);
  check('C: metric carton count parity (still 43)', cartonCount() === '43', cartonCount());
  check('B: carton header shows cm + kg', firstCartonHeader().includes('cm') && firstCartonHeader().includes('kg'), firstCartonHeader().slice(0, 90));
  const firstLen = document.querySelector('#inventoryTbody tr td:nth-child(2) input').value;
  check('B: mug length input shows 14 cm (5.5 in converted)', firstLen === '14', firstLen);
  check('B: guardrails 63.5 cm / 22.6 kg', document.getElementById('ruleSide').textContent === '63.5 cm' && document.getElementById('ruleWeight').textContent === '22.6 kg');
  check('B: min size shows cm', document.getElementById('ruleMinSize').textContent.includes('15.2 cm'));

  // D. case-pack via toggle-button click (the reported dropdown bug)
  click('stratCasepack');
  await tick();
  check('D: case-pack toggle works, 7 cartons', cartonCount() === '7', cartonCount());
  check('D: case-pack metric gross 104.1 kg (229.5 lb unrounded total converted)', statVals()[2] === '104.1 kg', statVals()[2]);
  click('stratConsolidated');
  await tick();
  check('D: back to consolidated, 43 cartons', cartonCount() === '43', cartonCount());

  // E. copy manifest: Bankr path, clipboard path, execCommand path, failure path
  click('btnCopyManifest');
  await tick();
  check('E1: bankr.copy path, toast success', bankrCopyCalled && toast().textContent.includes('Manifest copied'), toast().textContent);
  check('E1: manifest uses metric units', capturedClipboard.includes('Units: cm / kg') && capturedClipboard.includes('cm,'), (capturedClipboard || '').split('\n')[1]);
  delete window.bankr;
  bankrCopyCalled = false; capturedClipboard = null;
  click('btnCopyManifest');
  await tick();
  check('E2: clipboard path, toast success', !bankrCopyCalled && capturedClipboard?.includes('AMAZON FBA CARTON MANIFEST') && toast().textContent.includes('Manifest copied'), toast().textContent);
  Object.defineProperty(window.navigator, 'clipboard', { value: undefined, configurable: true });
  capturedClipboard = null;
  click('btnCopyManifest');
  await tick();
  check('E3: execCommand fallback, toast success', capturedClipboard === null && toast().textContent.includes('Manifest copied'), toast().textContent);
  execCommandResult = false;
  click('btnCopyManifest');
  await tick();
  check('E4: all copy paths fail, error toast', toast().textContent.includes('Copy blocked'), toast().textContent);
  execCommandResult = true;
  Object.defineProperty(window.navigator, 'clipboard', { value: { writeText: async (t) => { capturedClipboard = t; } }, configurable: true });

  // F. CSV: download toast + Copy CSV keeps imperial (Amazon format)
  click('btnExportCsv');
  await tick();
  check('F: CSV download toast with filename + Amazon format note', toast().textContent.includes('CSV download started') && toast().textContent.includes('Amazon format'), toast().textContent);
  capturedClipboard = null;
  click('btnCopyCsv');
  await tick();
  check('F: Copy CSV toast', toast().textContent.includes('CSV copied'), toast().textContent);
  check('F: CSV stays imperial (header + 12x10x8 S1 box, 4.9 lb)', capturedClipboard?.startsWith('Box Name,Length (in),Width (in),Height (in),Weight (lbs)') && capturedClipboard?.includes('"Box 1",12,10,8,4.9,'), (capturedClipboard || '').split('\n')[1]);

  // G. Add SKU auto-recalculates (no Calculate click)
  const before = cartonCount();
  click('btnAddRow');
  await tick();
  check('G: Add SKU auto-recalculates (units 295, no Calculate click)', statVals()[1] === '295', `units=${statVals()[1]} cartons=${cartonCount()} (was ${before})`);
  check('G: adding 20 mid-size units adds 4 cartons (43 -> 47), no blow-up', cartonCount() === '47', cartonCount());
  const newRowLen = [...document.querySelectorAll('#inventoryTbody tr')].pop().querySelector('td:nth-child(2) input').value;
  check('G: new SKU row displays in cm (8 in -> 20.3)', newRowLen === '20.3', newRowLen);

  // H. Freight: pallet plan + Euro honors its dimensions
  click('modeFreight');
  await tick();
  const palletText = () => document.getElementById('palletContainer').textContent.replace(/\s+/g, ' ');
  check('H: freight shows GMA pallet plan', palletText().includes('GMA') && palletText().includes('Ti'), palletText().slice(0, 120));
  check('H: pallet weights in kg (metric, 311 lb avg -> 141.07 kg)', palletText().includes('141.07 kg'), palletText().slice(0, 200));
  const gmaTi = (palletText().match(/(\d+) Ti/) || [])[1];
  click('palletEuro');
  await tick();
  const euroTi = (palletText().match(/(\d+) Ti/) || [])[1];
  check('H: Euro pallet label + Ti changes', palletText().includes('Euro') && euroTi !== gmaTi, `GMA Ti=${gmaTi} Euro Ti=${euroTi}`);

  // I. round trip back to imperial: identical results
  click('modeSpd');
  await tick();
  click('unitImperial');
  await tick();
  check('I: round trip imperial gross is lbs again and above the 241 baseline (extra SKU added)', statVals()[2].endsWith(' lbs') && parseInt(statVals()[2]) > 241, statVals().join(','));
  check('I: carton dims back to inches + lbs', firstCartonHeader().includes('"') && firstCartonHeader().includes('lbs') && !firstCartonHeader().includes('cm'), firstCartonHeader().slice(0, 80));

  // J. edit a cell in metric, auto-recalc, value persists converted
  click('unitMetric');
  await tick();
  const lenInput = document.querySelector('#inventoryTbody tr td:nth-child(2) input');
  lenInput.value = '28';
  lenInput.dispatchEvent(new window.Event('change', { bubbles: true }));
  await tick();
  check('J: editing a cell auto-recalculates (results still shown)', document.getElementById('resultsPanel').style.display === 'block' && statVals()[1] === '295');
  check('J: edited value persists as 28 cm', document.querySelector('#inventoryTbody tr td:nth-child(2) input').value === '28');

  // K. placement sanity: units conserved, no box over the 50 lb cap, no util over 99%
  let summedUnits = 0, maxBoxWt = 0, maxBoxUtil = 0;
  for (const b of document.querySelectorAll('.box-card')) {
    for (const r of b.querySelectorAll('.box-item-row span:last-child')) summedUnits += parseInt(r.textContent);
    const hm = b.querySelector('.box-header').textContent.match(/([\d.]+) (lbs|kg)/);
    if (hm) maxBoxWt = Math.max(maxBoxWt, hm[2] === 'kg' ? parseFloat(hm[1]) / 0.45359237 : parseFloat(hm[1]));
    const um = b.querySelector('.box-details').textContent.match(/Space Utilization:\s*(\d+)%/);
    if (um) maxBoxUtil = Math.max(maxBoxUtil, parseInt(um[1]));
  }
  check('K: units conserved across cartons (295)', summedUnits === 295, `summed=${summedUnits}`);
  check('K: no carton over the weight cap', maxBoxWt <= 50, `max=${maxBoxWt}`);
  check('K: no carton utilization over 99%', maxBoxUtil <= 99, `max=${maxBoxUtil}%`);

  check('no alerts fired', alerts.length === 0, alerts.join(';'));
  console.log(failures === 0 ? 'ALL FIXED CHECKS PASSED' : `${failures} CHECK(S) FAILED`);
  process.exit(failures ? 1 : 0);
}

main().catch((e) => { console.error('HARNESS ERROR', e); process.exit(2); });
