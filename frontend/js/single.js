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

import { apiUploadWithProgress, apiConvert, watchJobProgress, apiDownloadUrl } from './api.js';

import {
  showStatus,
  clearStatus,
  buildErrorHtml,
  renderSingleFileInfo,
  renderSingleFormats,
  registerSelectSingleFormat,
  setProgressBar,
  showDownloadButton,
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
 * Upload a single file using XHR with upload progress (0-50% of the bar).
 * After upload completes, hides progress bar and shows format selection.
 * @param {File} file
 */
export async function uploadSingle(file) {
  resetAll();
  document.getElementById('format-card-single').style.display = '';
  document.getElementById('progress-wrap-single').style.display = '';
  document.getElementById('download-area-single').style.display = 'none';
  document.getElementById('download-area-single').innerHTML = '';

  // Upload phase: 0% to 50% of the bar
  setProgressBar('progress-fill-single', 'progress-label-single', 0, 'Uploading…');

  try {
    const data = await apiUploadWithProgress(file, (ratio) => {
      setProgressBar('progress-fill-single', 'progress-label-single', ratio * 50, 'Uploading…');
    });

    // Upload complete — bar at 50%
    setProgressBar('progress-fill-single', 'progress-label-single', 50, 'Uploaded.');
    document.getElementById('progress-wrap-single').style.display = 'none';
    document.getElementById('progress-fill-single').style.width = '0%';

    // Store state
    setSingleFile(data.file_id, null, data.category, data.available_formats || []);
    renderSingleFileInfo(data, file.size);
    renderSingleFormats(data.available_formats || []);
    clearStatus('status-single');
  } catch (err) {
    document.getElementById('format-card-single').style.display = 'none';
    document.getElementById('progress-wrap-single').style.display = 'none';
    document.getElementById('progress-fill-single').style.width = '0%';
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
 * Two-phase progress: SSE conversion maps 0-100% onto bar range 50-100%.
 * Shows a Download button on completion (no auto-download).
 */
export async function convertSingle() {
  if (!singleFileId || !singleFormat) return;

  const btn = document.getElementById('convert-btn-single');
  btn.disabled = true;
  document.getElementById('progress-wrap-single').style.display = '';
  document.getElementById('download-area-single').style.display = 'none';
  document.getElementById('download-area-single').innerHTML = '';
  clearStatus('status-single');

  // Start at 50% (upload was 0-50%)
  setProgressBar('progress-fill-single', 'progress-label-single', 50, 'Converting…');

  try {
    // Fire conversion — returns {job_id}
    const { job_id } = await apiConvert(singleFileId, singleFormat, currentQuality);

    // SSE phase: 50% to 100% of the bar
    const downloadId = await watchJobProgress(job_id, (pct) => {
      const barPct = 50 + (pct / 100) * 50;
      setProgressBar('progress-fill-single', 'progress-label-single', barPct, 'Converting…');
    });

    // Done — bar at 100%
    setProgressBar('progress-fill-single', 'progress-label-single', 100, 'Done!');

    // Derive output filename: {original_stem}.{target_format}
    const originalName = document.getElementById('fi-name').textContent || 'file';
    const stem = originalName.replace(/\.[^.]+$/, '');
    const outputFilename = `${stem}.${singleFormat}`;

    // Show Download button (per user decision: no auto-download, user clicks to save)
    showDownloadButton('download-area-single', downloadId, outputFilename);

    // Add to history
    addToHistory({
      type:        'single',
      filename:    outputFilename,
      from:        document.getElementById('fi-fmt').textContent,
      to:          singleFormat.toUpperCase(),
      quality:     currentQuality,
      download_id: downloadId,
    });

    showStatus('status-single', 'success', `Conversion complete — file ready for download.`);
  } catch (err) {
    showStatus('status-single', 'error', buildErrorHtml(err.message, err.rawDetail || null));
    document.getElementById('progress-wrap-single').style.display = 'none';
    document.getElementById('progress-fill-single').style.width = '0%';
  } finally {
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
  document.getElementById('download-area-single').style.display = 'none';
  document.getElementById('download-area-single').innerHTML = '';

  resetBulkState();
  document.getElementById('progress-wrap-bulk-upload').style.display = 'none';
  document.getElementById('bulk-file-list').innerHTML = '';
  document.getElementById('bulk-list-card').style.display = 'none';
  document.getElementById('bulk-summary').style.display = 'none';
  document.getElementById('bulk-download-all').style.display = 'none';
  document.getElementById('bulk-download-all').innerHTML = '';
  clearStatus('status-bulk');
}
