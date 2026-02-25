/* ── Shared mutable state ───────────────────────────────────────────────── */

export let currentQuality = 'original';

/* Single mode */
export let singleFileId   = null;
export let singleFormat   = null;
export let singleCategory = null;
export let singleFmts     = [];

/* Bulk mode */
export let bulkFiles = [];
// [{file_id, filename, size, category, detected_format, available_formats, target_format, status, error}]

/* History */
export let history = [];

/* ── Quality ─────────────────────────────────────────────────────────────── */

/**
 * Set currentQuality and update quality button active states in DOM.
 * @param {string} q - quality level
 */
export function setQuality(q) {
  currentQuality = q;
  document.querySelectorAll('#quality-opts .quality-opt').forEach(b => {
    b.classList.toggle('active', b.dataset.q === q);
  });
}

/* ── Single mode mutations ───────────────────────────────────────────────── */

/**
 * Set all single-mode state at once after upload.
 * @param {string} id - file_id from API
 * @param {string} fmt - detected format
 * @param {string} cat - category
 * @param {string[]} fmts - available output formats
 */
export function setSingleFile(id, fmt, cat, fmts) {
  singleFileId   = id;
  singleFormat   = fmt;
  singleCategory = cat;
  singleFmts     = fmts;
}

/**
 * Reset single-mode state back to defaults.
 */
export function resetSingleState() {
  singleFileId   = null;
  singleFormat   = null;
  singleCategory = null;
  singleFmts     = [];
}

/* ── Bulk mode mutations ─────────────────────────────────────────────────── */

/**
 * Reset bulk-mode state back to defaults.
 */
export function resetBulkState() {
  bulkFiles = [];
}

/**
 * Set the target format for a bulk row.
 * @param {number} i - row index
 * @param {string} value - selected format value
 */
export function setBulkFormat(i, value) {
  bulkFiles[i].target_format = value;
}

/**
 * Add a file object to the bulk files array.
 * @param {Object} fileObj - bulk file descriptor
 */
export function addBulkFile(fileObj) {
  bulkFiles.push(fileObj);
}

/**
 * Return the bulkFiles array reference.
 * Needed because importers cannot read a reassigned export let array directly.
 * @returns {Object[]}
 */
export function getBulkFiles() {
  return bulkFiles;
}

/* ── History mutations ───────────────────────────────────────────────────── */

/**
 * Add an entry to the history array (prepend, cap at 50).
 * @param {Object} entry
 */
export function addToHistory(entry) {
  history.unshift({ ...entry, ts: Date.now() });
  if (history.length > 50) history.pop();
}

/**
 * Reset history to empty array.
 */
export function clearHistoryState() {
  history = [];
}
