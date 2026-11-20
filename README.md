# FBA Box & Freight Packer — fork + fix

Fork of Kyle's Bankr app `fba-pack-master` (owner `0xda641d4ff3a5ea3c8b5265db8701622a68998903`,
public, created 2026-11-19). Source pulled from Bankr's public app endpoint
(`GET api.bankr.bot/public/apps/<owner>/fba-pack-master`, `indexHtml` field).
Bankr's own fork button is turned off per their docs, so this is a source fork.

## Files

- `index.html` — the fixed app itself (repo root, GitHub Pages entry point; identical to `fixed/index.html`)
- `original/index.html` — pristine source as published (43,994 bytes, single file, no backend scripts)
- `fixed/index.html` — fixed copy (52,004 bytes, same single-file app)
- `fix.py` — the patch script that turns original into fixed (re-runnable, every replacement asserted)
- `test.mjs` — headless test harness (jsdom). `node test.mjs original` reproduces the bugs,
  `node test.mjs fixed` runs the full suite (27 checks, all passing)

## What was broken, and the fix

1. **Metric mode only relabeled units, never converted.** Gross weight showed
   the pound number with a "kg" label (241 lbs became "241 kg"), carton dims
   stayed in inches, guardrail math ran against metric inputs with imperial
   constants. Fix: inches/lbs are now the canonical internal unit. Every
   input converts to imperial on entry, every output converts to the display
   unit (2.54 cm/in, 0.45359237 kg/lb). Inventory table, custom box flock,
   pallet max weight, guardrail text, warnings, carton cards, pallet plan,
   and manifest all convert. The CSV export stays imperial on purpose:
   Amazon's 2D barcode format is inches/lbs.
2. **Packing Strategy dropdown ignored a click** (only keyboard worked).
   Fix: all four native `<select>`s (strategy, box source, pallet standard,
   pallet height) are now toggle-button groups, the same control the app
   already uses for mode and units, which worked in the live browser test.
   Changing one recalculates when results are shown.
3. **Copy Manifest / Download CSV gave no feedback** (clipboard silently
   fails in Bankr's sandboxed iframe). Fix: a toast confirms or reports
   failure, copy tries `bankr.copy()` (host-mediated) then
   `navigator.clipboard` then a textarea + `execCommand` fallback, and a new
   Copy CSV button guarantees an export path even if the iframe blocks the
   file download.
4. **Editing inventory never recalculated.** Fix: add/delete/edit row, paste,
   file import, strategy, box source, mode, units, and pallet settings all
   recalculate automatically once results are shown.
5. **Bonus: Euro pallet was ignored.** The pallet math always used GMA 48x40
   even when Euro was selected. Euro now uses 47x31 in and its own label;
   Ti/Hi changes accordingly (sample: GMA 16x8, Euro 9x8).

## Carton detail view (added Nov 20 2026)

Click any carton card (or focus it and press Enter/Space) to open a detail
modal for just that carton. It shows the dimensions, gross weight,
utilization, and packing mode as text, the full contents list with each
SKU's dimensions and weight, and a top-down layout image (inline SVG)
drawn from the real placement data: one rectangle per unit, colored by
SKU, labeled with the height where it sits in the carton. Case-pack
cartons draw one layer as a grid and state the layer count. Close with
the X button, by clicking the backdrop, with Escape, or by recalculating.

## Box math (swapped in Nov 20 2026)

Consolidated mode used to sum volumes and cap at 82% of box volume, with no
check that items fit together in 3D. It claimed 38 cartons at 80% on the
sample, a number no real packing achieves.

Now it is first-fit decreasing with extreme-point placement: units sorted by
volume, each placed as a real cuboid at the lowest free corner point in one
of its six orientations, weight cap as a hard limit. Utilization is measured
from placed volume. Sample result: 43 cartons, 244 lbs, 78% average, max
88% in any carton, no carton over the 50 lb cap, all 275 units accounted
for. Recalc takes ~94 ms on the sample. Case-pack mode is unchanged (min of
volume / weight / orientation counts, 7 cartons on the sample).

## Verified

- `node test.mjs original`: all 5 bug-reproduction checks pass (bugs confirmed present).
- `node test.mjs fixed`: 47/47 checks pass, including imperial/metric parity
  (same 43 cartons, 244 lbs = 110.5 kg), case-pack toggle (7 cartons),
  all four copy paths (Bankr / clipboard / execCommand / total failure),
  CSV staying imperial, auto-recalc on add/edit, Euro Ti change, an
  imperial round trip after metric edits, placement sanity (units
  conserved, no carton over 50 lbs, no utilization over 99%), and the
  carton detail view (open/close/Escape/recalc-close, SVG layout with
  one rect per placed unit, case-pack layer grid).
- JS syntax checked with `node --check`; no references remain to the removed
  select element ids. Not yet clicked through in a live browser; the
  headless run covers the same interactions, and the toggle buttons are the
  control type already proven in the live Bankr test.

## Putting the fix live in Bankr

Bozo cannot push to Kyle's Bankr account (owner-only, passkey-gated). Kyle,
signed in to Bankr: upload `fixed/index.html` to Bankr files, open the app,
and paste in the app chat:

> Replace this app's index.html with the fixed file I just uploaded.
> It fixes metric conversion, the strategy dropdown, copy/download
> feedback, auto-recalc, and Euro pallets. Keep everything else the same.

Or ask Bankr to install it as a new app under a new slug (a true fork copy).
