/* ── Single-file conversion feature module ───────────────────────────────── */

import {
  singleFileId,
  singleFormat,
  currentQuality,
  setSingleFile,
  setSingleFormat,
  resetSingleState,
  resetBulkState,
  getBulkFiles,
  addToHistory,
} from './state.js';

import { apiUpload, apiConvert, apiDownloadUrl } from './api.js';

import {
  showStatus,
  clearStatus,
  buildErrorHtml,
  renderSingleFileInfo,
  renderSingleFormats,
  registerSelectSingleFormat,
} from './ui.js';

import { uploadBulk } from './bulk.js';

/* ── Circular-dependency registration ───────────────────────────────────── */
// Register selectSingleFormat with ui.js so renderSingleFormats can invoke it
// without creating a circular import.
registerSelectSingleFormat(selectSingleFormat);

/* ── File handling (shared router) ──────────────────────────────────────── */

/**
 * Central file router. 1 file → single mode; 2+ files → bulk mode.
 * Called by drag-and-drop and file input handlers.
 * @param {File[]|FileList} files
 */
export function handleFiles(files) {
  if (!files.length) return;
  const bulkFiles = getBulkFiles();
  if (files.length === 1 && !bulkFiles.length) {
    uploadSingle(files[0]);
  } else {
    uploadBulk(files);
  }
}

/**
 * Handle file input 'change' event.
 * @param {Event} event
 */
export function onFilePick(event) {
  handleFiles(Array.from(event.target.files));
  // Reset value so picking the same file(s) again still fires 'change'.
  event.target.value = '';
}

/**
 * Handle dragover event on drop zone.
 * @param {DragEvent} event
 */
export function onDragOver(event) {
  event.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}

/**
 * Handle drop event on drop zone.
 * @param {DragEvent} event
 */
export function onDrop(event) {
  event.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  handleFiles(Array.from(event.dataTransfer.files));
}

/* ── Single-file conversion flow ────────────────────────────────────────── */

/**
 * Upload a single file, store result in state, render info and formats.
 * @param {File} file
 */
export async function uploadSingle(file) {
  resetAll();
  showStatus('status-single', 'info', 'Uploading…');
  document.getElementById('format-card-single').style.display = '';

  try {
    const data = await apiUpload(file);

    // Store file_id and category; singleFormat starts null (user must pick from chips).
    setSingleFile(data.file_id, null, data.category, data.available_formats || []);

    renderSingleFileInfo(data, file.size);
    renderSingleFormats(data.available_formats || []);
    clearStatus('status-single');
  } catch (err) {
    document.getElementById('format-card-single').style.display = 'none';
    showStatus('status-single', 'error', buildErrorHtml(err.message, err.rawDetail || null));
  }
}

/**
 * Update selected format in state and toggle active chip styling.
 * Registered with ui.js via registerSelectSingleFormat() to avoid circular import.
 * @param {string} fmt
 * @param {HTMLElement} btn
 */
export function selectSingleFormat(fmt, btn) {
  setSingleFormat(fmt);
  document.querySelectorAll('#format-grid-single .format-chip').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  document.getElementById('convert-btn-single').disabled = false;
}

/**
 * Convert the uploaded single file using current state.
 * Reads singleFileId, singleFormat, currentQuality as live ES module bindings.
 */
export async function convertSingle() {
  if (!singleFileId || !singleFormat) return;

  const btn = document.getElementById('convert-btn-single');
  btn.disabled = true;
  document.getElementById('progress-wrap-single').style.display = '';
  clearStatus('status-single');

  try {
    const data = await apiConvert(singleFileId, singleFormat, currentQuality);

    document.getElementById('progress-fill-single').style.width = '100%';

    addToHistory({
      type:        'single',
      filename:    data.output_filename,
      from:        document.getElementById('fi-fmt').textContent,
      to:          singleFormat.toUpperCase(),
      quality:     currentQuality,
      download_id: data.download_id,
    });

    showStatus('status-single', 'success',
      `✓ Done! <a href="${apiDownloadUrl(data.download_id)}" download="${data.output_filename}"` +
      ` style="color:inherit;text-decoration:underline;margin-left:6px;">Download ${data.output_filename}</a>`);
  } catch (err) {
    showStatus('status-single', 'error', buildErrorHtml(err.message, err.rawDetail || null));
  } finally {
    document.getElementById('progress-wrap-single').style.display = 'none';
    document.getElementById('progress-fill-single').style.width = '0%';
    btn.disabled = false;
  }
}

/**
 * Reset all single and bulk state, hide all dynamic UI, return to upload view.
 */
export function resetAll() {
  resetSingleState();
  document.getElementById('file-info-single').classList.remove('visible');
  document.getElementById('format-card-single').style.display = 'none';
  document.getElementById('format-grid-single').innerHTML = '';
  document.getElementById('convert-btn-single').disabled = true;
  clearStatus('status-single');

  resetBulkState();
  document.getElementById('bulk-file-list').innerHTML = '';
  document.getElementById('bulk-list-card').style.display = 'none';
  clearStatus('status-bulk');
}
