/* ── ES module entry point — wires all addEventListener calls ───────────── */
// <script type="module"> is deferred by spec — DOM is already parsed here.
// No DOMContentLoaded wrapper needed.

import { setQuality } from './state.js';

import {
  onDragOver,
  onDrop,
  onFilePick,
  resetAll,
  convertSingle,
} from './single.js';

import {
  applyGlobalFormat,
  convertBulk,
} from './bulk.js';

import {
  showPage,
  clearHistory,
  initBulkListDelegation,
  renderHistory,
} from './ui.js';

/* ── Navigation ─────────────────────────────────────────────────────────── */
document.querySelectorAll('.nav-item[data-page]').forEach(el => {
  el.addEventListener('click', () => showPage(el.dataset.page));
});

/* ── Quality buttons — event delegation on #quality-opts ────────────────── */
document.getElementById('quality-opts').addEventListener('click', e => {
  const btn = e.target.closest('.quality-opt');
  if (btn) setQuality(btn.dataset.q);
});

/* ── Drop zone ──────────────────────────────────────────────────────────── */
const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', onDragOver);
dropZone.addEventListener('drop', onDrop);
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

/* ── File input ─────────────────────────────────────────────────────────── */
document.getElementById('file-input').addEventListener('change', onFilePick);

/* ── Single mode buttons ────────────────────────────────────────────────── */
// Clear button inside #file-info-single (no ID — query by context)
document.querySelector('#file-info-single button').addEventListener('click', resetAll);

// Convert button
document.getElementById('convert-btn-single').addEventListener('click', convertSingle);

/* ── Bulk toolbar buttons ───────────────────────────────────────────────── */
// The three .bulk-apply-btn buttons: Apply to compatible, + Add files, Clear all
const bulkApplyBtns = document.querySelectorAll('.bulk-toolbar .bulk-apply-btn');
bulkApplyBtns[0].addEventListener('click', applyGlobalFormat);                                     // Apply to compatible
bulkApplyBtns[1].addEventListener('click', () => document.getElementById('file-input').click());  // + Add files
bulkApplyBtns[2].addEventListener('click', resetAll);                                              // Clear all

// Bulk convert button
document.getElementById('bulk-convert-btn').addEventListener('click', convertBulk);

/* ── History ────────────────────────────────────────────────────────────── */
// Clear history button in #page-history header
document.querySelector('#page-history .btn-secondary').addEventListener('click', clearHistory);

/* ── Event delegation for dynamically-created bulk format selects ────────── */
initBulkListDelegation();

/* ── Initialize on load ─────────────────────────────────────────────────── */
// Render any persisted history (none in this session-only app, but keeps renderHistory callable)
renderHistory();
