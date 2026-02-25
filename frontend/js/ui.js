/* ── UI helpers and rendering functions ─────────────────────────────────── */

import { history, clearHistoryState, setBulkFormat, removeBulkFile, getBulkFiles } from './state.js';
import { apiDownloadUrl } from './api.js';

/* ── Circular dependency resolution ─────────────────────────────────────── */
// renderSingleFormats needs selectSingleFormat from single.js, but single.js
// imports from ui.js. Use a registration pattern: single.js calls
// registerSelectSingleFormat(fn) at import time, then renderSingleFormats
// uses the registered function.

let _selectSingleFormat = null;

/**
 * Register the selectSingleFormat callback (called by single.js at import time).
 * @param {Function} fn
 */
export function registerSelectSingleFormat(fn) {
  _selectSingleFormat = fn;
}

/* ── Pure helpers (no state dependency) ─────────────────────────────────── */

/**
 * Show a status message element.
 * @param {string} elementId
 * @param {string} type - 'success' | 'error' | 'info'
 * @param {string} html
 */
export function showStatus(elementId, type, html) {
  const el = document.getElementById(elementId);
  el.className = `status-msg visible ${type}`;
  el.innerHTML = html;
}

/**
 * Clear a status message element.
 * @param {string} elementId
 */
export function clearStatus(elementId) {
  const el = document.getElementById(elementId);
  el.className = 'status-msg';
  el.innerHTML = '';
}

/**
 * Return SVG/HTML icon string for a status type.
 * @param {string} status - 'pending' | 'converting' | 'done' | 'error'
 * @returns {string}
 */
export function statusIcon(status) {
  if (status === 'pending')    return '<span class="status-pending">○</span>';
  if (status === 'converting') return '<span class="status-converting">↻</span>';
  if (status === 'done')       return '<span class="status-done">✓</span>';
  if (status === 'error')      return '<span class="status-error">✕</span>';
  return '';
}

/**
 * Return emoji for a file category.
 * @param {string} category
 * @returns {string}
 */
export function categoryIcon(category) {
  const icons = { document: '📄', image: '🖼', audio: '🎵', video: '🎬', data: '📊', archive: '📦' };
  return icons[category] || '📄';
}

/**
 * Format a byte count to a human-readable string.
 * @param {number} bytes
 * @returns {string}
 */
export function fmtSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024)       return `${bytes} B`;
  if (bytes < 1048576)    return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}

/**
 * Format a timestamp to a relative time string.
 * @param {number} ts - epoch milliseconds
 * @returns {string}
 */
export function timeAgo(ts) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

/**
 * HTML-escape a string.
 * @param {string} str
 * @returns {string}
 */
export function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/**
 * Build error HTML with optional details toggle.
 * @param {string} message
 * @param {string|null} rawDetail
 * @returns {string}
 */
export function buildErrorHtml(message, rawDetail) {
  let html = esc(message);
  if (rawDetail) {
    html += `<details style="margin-top:6px;font-size:10px;color:var(--text-2);">` +
            `<summary style="cursor:pointer;user-select:none;">Show details</summary>` +
            `<pre style="margin-top:4px;white-space:pre-wrap;word-break:break-all;` +
            `max-height:200px;overflow-y:auto;">${esc(rawDetail)}</pre>` +
            `</details>`;
  }
  return html;
}

/* ── Rendering functions (read state) ───────────────────────────────────── */

/**
 * Switch visible page and update nav active states.
 * Calls renderHistory() when switching to the history page.
 * @param {string} page
 */
export function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelector(`.nav-item[data-page="${page}"]`).classList.add('active');
  if (page === 'history') renderHistory();
}

/**
 * Render the single file info card.
 * @param {Object} meta - API response from /api/upload
 * @param {number} [sizeBytes] - file size in bytes (optional, falls back to meta.size)
 */
export function renderSingleFileInfo(meta, sizeBytes) {
  const info = document.getElementById('file-info-single');
  document.getElementById('fi-icon').textContent = categoryIcon(meta.category);
  document.getElementById('fi-name').textContent = meta.filename;
  document.getElementById('fi-size').textContent = fmtSize(sizeBytes !== undefined ? sizeBytes : meta.size);
  const badge = document.getElementById('fi-badge');
  badge.textContent = meta.category;
  badge.className   = `file-badge badge-${meta.category}`;
  document.getElementById('fi-fmt').textContent = meta.detected_format.toUpperCase();
  info.classList.add('visible');
}

/**
 * Render format chip grid for single-mode.
 * Uses the registered selectSingleFormat callback.
 * @param {string[]} fmts
 */
export function renderSingleFormats(fmts) {
  const grid = document.getElementById('format-grid-single');
  grid.innerHTML = '';
  if (!fmts.length) {
    grid.innerHTML = '<div class="format-empty">No output formats available.</div>';
    return;
  }
  fmts.forEach(f => {
    const btn = document.createElement('button');
    btn.className = 'format-chip';
    btn.textContent = f.toUpperCase();
    btn.addEventListener('click', () => {
      if (_selectSingleFormat) _selectSingleFormat(f, btn);
    });
    grid.appendChild(btn);
  });
}

/**
 * Render the full bulk file list (calls renderBulkRow for each item).
 * Also populates the global format dropdown.
 * @param {Object[]} bulkFiles - bulk files array from state
 */
export function renderBulkList(bulkFiles) {
  const list = document.getElementById('bulk-file-list');
  list.innerHTML = '';

  const good = bulkFiles.filter(f => !f.error);
  document.getElementById('bulk-count-badge').textContent =
    `${good.length} file${good.length !== 1 ? 's' : ''}`;

  // Populate global format dropdown (union of all available_formats)
  const allFmts = [...new Set(good.flatMap(f => f.available_formats))].sort();
  const gfmt = document.getElementById('bulk-global-fmt');
  gfmt.innerHTML = '<option value="">— pick format —</option>' +
    allFmts.map(f => `<option value="${f}">${f.toUpperCase()}</option>`).join('');

  bulkFiles.forEach((f, i) => renderBulkRow(f, i, list));
}

/**
 * Render a single bulk file row.
 * Includes per-row progress bar, X remove button (pending only),
 * Download button (done only), and smart format default.
 * The format select has NO inline handler — event delegation handles changes.
 * @param {Object} f - bulk file descriptor
 * @param {number} i - row index
 * @param {HTMLElement} container - parent element to append to
 */
export function renderBulkRow(f, i, container) {
  const row = document.createElement('div');
  row.className = `bulk-file-row ${f.status}`;
  row.id = `bulk-row-${i}`;

  if (f.error && f.status === 'error' && !f.file_id) {
    // Upload-time error row (no file_id means upload itself failed)
    row.innerHTML = `
      <span class="bulk-file-icon">⚠</span>
      <span class="bulk-file-name" style="color:var(--error);">${esc(f.filename)}</span>
      <span style="font-size:10px;color:var(--error);flex:1;">${esc(f.error)}</span>
    `;
    container.appendChild(row);
    return;
  }

  // Smart default: pre-fill first available format if none set
  if (!f.target_format && f.available_formats && f.available_formats.length > 0) {
    f.target_format = f.available_formats[0];
  }

  const fmtOptions = (f.available_formats || []).map(fmt =>
    `<option value="${fmt}" ${fmt === f.target_format ? 'selected' : ''}>${fmt.toUpperCase()}</option>`
  ).join('');

  // Build action cell based on status
  let actionHtml = '';
  if (f.status === 'pending') {
    actionHtml = `<button class="bulk-row-remove" data-index="${i}" title="Remove">&times;</button>`;
  } else if (f.status === 'done' && f.download_id) {
    actionHtml = `<a href="${apiDownloadUrl(f.download_id)}" download="${esc(f.filename)}" class="bulk-row-dl" title="Download">↓</a>`;
  }

  row.innerHTML = `
    <span class="bulk-file-icon">${categoryIcon(f.category)}</span>
    <span class="bulk-file-name">${esc(f.filename)}</span>
    <span class="bulk-file-size">${fmtSize(f.size)}</span>
    <span class="bulk-file-fmt">
      <select ${f.status !== 'pending' ? 'disabled' : ''}>
        <option value="">— format —</option>
        ${fmtOptions}
      </select>
    </span>
    <span class="bulk-file-progress" id="bulk-progress-${i}">
      <span class="bulk-progress-bar"><span class="bulk-progress-fill" id="bulk-fill-${i}"></span></span>
      <span class="bulk-progress-label" id="bulk-plabel-${i}"></span>
    </span>
    <span class="bulk-file-status" id="bulk-status-${i}">${statusIcon(f.status)}</span>
    <span class="bulk-file-action" id="bulk-action-${i}">${actionHtml}</span>
  `;

  // Set initial progress bar width if progress > 0
  if (f.progress && f.progress > 0) {
    const fill = row.querySelector(`#bulk-fill-${i}`);
    if (fill) fill.style.width = `${f.progress}%`;
  }

  // Append error note if this is a conversion-time error
  if (f.error && f.status === 'error') {
    const note = document.createElement('div');
    note.className = 'bulk-error-note';
    note.innerHTML = buildErrorHtml(f.error, f.errorDetail || null);
    row.appendChild(note);
  }

  container.appendChild(row);
}

/**
 * Update a bulk row's progress bar fill and label.
 * @param {number} index - row index
 * @param {number} percent - 0-100
 * @param {string} [label] - optional label prefix
 */
export function updateBulkRowProgress(index, percent, label) {
  const fill = document.getElementById(`bulk-fill-${index}`);
  const plabel = document.getElementById(`bulk-plabel-${index}`);
  if (fill) fill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
  if (plabel) plabel.textContent = label ? `${label} ${Math.round(percent)}%` : '';
}

/**
 * Update a bulk row's action cell (X remove or download button).
 * @param {Object[]} bulkFiles - bulk files array from state
 * @param {number} index - row index
 */
export function updateBulkRowAction(bulkFiles, index) {
  const f = bulkFiles[index];
  const container = document.getElementById(`bulk-action-${index}`);
  if (!container) return;
  if (f.status === 'done' && f.download_id) {
    container.innerHTML = `<a href="${apiDownloadUrl(f.download_id)}" download="${esc(f.filename)}" class="bulk-row-dl" title="Download">↓</a>`;
  } else if (f.status === 'pending') {
    container.innerHTML = `<button class="bulk-row-remove" data-index="${index}" title="Remove">&times;</button>`;
  } else {
    container.innerHTML = '';
  }
}

/**
 * Update a bulk row's status display.
 * @param {Object[]} bulkFiles - bulk files array from state
 * @param {number} index
 * @param {string} status
 * @param {string|null} errMsg
 * @param {string|null} errDetail
 */
export function updateBulkRowStatus(bulkFiles, index, status, errMsg, errDetail) {
  bulkFiles[index].status = status;
  if (errMsg) bulkFiles[index].error = errMsg;
  if (errDetail !== undefined) bulkFiles[index].errorDetail = errDetail;

  const row = document.getElementById(`bulk-row-${index}`);
  if (row) {
    row.className = `bulk-file-row ${status}`;
  }
  const si = document.getElementById(`bulk-status-${index}`);
  if (si) si.innerHTML = statusIcon(status);

  // Remove any existing error note
  const oldNote = row && row.querySelector('.bulk-error-note');
  if (oldNote) oldNote.remove();

  // Add error note if there's an error message
  if (row && errMsg && status === 'error') {
    const note = document.createElement('div');
    note.className = 'bulk-error-note';
    note.innerHTML = buildErrorHtml(errMsg, errDetail || null);
    row.appendChild(note);
  }

  // Update action cell and disable select when not pending
  updateBulkRowAction(bulkFiles, index);
  const sel = row && row.querySelector('select');
  if (sel && status !== 'pending') sel.disabled = true;
}

/**
 * Render the history list from state.
 */
export function renderHistory() {
  const list = document.getElementById('history-list');
  if (!history.length) {
    list.innerHTML = '<div class="history-empty">No conversions yet.</div>';
    return;
  }
  list.innerHTML = '';
  history.forEach(h => {
    const item = document.createElement('div');
    item.className = 'history-item';

    let icon, nameHtml, detailHtml, actionHtml;

    if (h.type === 'single') {
      icon       = '📄';
      nameHtml   = esc(h.filename);
      detailHtml = `${h.from} → ${h.to} &nbsp;·&nbsp; quality: ${h.quality} &nbsp;·&nbsp; ${timeAgo(h.ts)}`;
      actionHtml = `<a class="history-dl" href="/api/download/${h.download_id}" download="${h.filename}">↓ Download</a>`;
    } else {
      icon       = '📦';
      nameHtml   = `converted.zip`;
      detailHtml = `${h.count} file(s) converted${h.errors ? ` (${h.errors} failed)` : ''} &nbsp;·&nbsp; quality: ${h.quality} &nbsp;·&nbsp; ${timeAgo(h.ts)}`;
      actionHtml = `<a class="history-dl" href="/api/download/${h.download_id}" download="converted.zip">↓ Download ZIP</a>`;
    }

    item.innerHTML = `
      <span class="history-icon">${icon}</span>
      <div class="history-meta">
        <div class="history-name">${nameHtml}</div>
        <div class="history-detail">${detailHtml}</div>
      </div>
      <div class="history-action">${actionHtml}</div>
    `;
    list.appendChild(item);
  });
}

/**
 * Clear history state and re-render the now-empty list.
 * Convenience function: combines clearHistoryState() + renderHistory()
 * so main.js can wire it to the clear-history button with a single import.
 */
export function clearHistory() {
  clearHistoryState();
  renderHistory();
}

/**
 * Set the progress bar fill width and update the label text with percentage.
 * @param {string} fillId - ID of the progress bar fill element
 * @param {string} labelId - ID of the progress label element
 * @param {number} percent - progress percentage (0-100)
 * @param {string} labelText - label prefix text (e.g. 'Uploading…' or 'Converting…')
 */
export function setProgressBar(fillId, labelId, percent, labelText) {
  const fill = document.getElementById(fillId);
  const label = document.getElementById(labelId);
  if (fill) fill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
  if (label) label.textContent = `${labelText} ${Math.round(percent)}%`;
}

/**
 * Show a download button in a container element.
 * Uses esc() for XSS-safe filename rendering.
 * @param {string} containerId - ID of the container element to populate
 * @param {string} downloadId - download ID for the /api/download/ URL
 * @param {string} filename - output filename shown on the button
 */
export function showDownloadButton(containerId, downloadId, filename) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const url = `/api/download/${downloadId}`;
  container.innerHTML = `<a href="${url}" download="${esc(filename)}" class="btn btn-success">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
    Download ${esc(filename)}
  </a>`;
  container.style.display = '';
}

/**
 * Attach delegated event listeners on #bulk-file-list:
 * - 'change' on SELECT: updates target_format via setBulkFormat
 * - 'click' on .bulk-row-remove: removes file via removeBulkFile and re-renders
 */
export function initBulkListDelegation() {
  const list = document.getElementById('bulk-file-list');

  // Format select change delegation
  list.addEventListener('change', e => {
    if (e.target.tagName !== 'SELECT') return;
    const row = e.target.closest('[id^="bulk-row-"]');
    if (!row) return;
    const index = parseInt(row.id.replace('bulk-row-', ''), 10);
    setBulkFormat(index, e.target.value);
  });

  // Remove button click delegation
  list.addEventListener('click', e => {
    const btn = e.target.closest('.bulk-row-remove');
    if (!btn) return;
    const index = parseInt(btn.dataset.index, 10);
    removeBulkFile(index);
    renderBulkList(getBulkFiles());

    // Hide bulk card if no files left
    const remaining = getBulkFiles();
    if (remaining.length === 0) {
      document.getElementById('bulk-list-card').style.display = 'none';
    }
  });
}
