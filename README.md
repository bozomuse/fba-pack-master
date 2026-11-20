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
   Ti/Hi changes accordingly (sample: GMA 12x8, Euro 9x8).

## Verified

- `node test.mjs original`: all 5 bug-reproduction checks pass (bugs confirmed present).
- `node test.mjs fixed`: 27/27 checks pass, including imperial/metric parity
  (same 38 cartons, 241 lbs = 109.5 kg), case-pack toggle (7 cartons),
  all four copy paths (Bankr / clipboard / execCommand / total failure),
  CSV staying imperial, auto-recalc on add/edit, Euro Ti change, and an
  imperial round trip after metric edits.
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
