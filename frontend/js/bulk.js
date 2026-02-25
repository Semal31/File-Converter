/* ── Bulk conversion feature module ──────────────────────────────────────── */

import {
  currentQuality,
  resetBulkState,
  getBulkFiles,
  addBulkFile,
  addToHistory,
} from './state.js';

import { apiBulkUpload, apiBulkConvert, apiDownloadUrl } from './api.js';

import {
  showStatus,
  clearStatus,
  buildErrorHtml,
  renderBulkList,
  updateBulkRowStatus,
} from './ui.js';

/* ── Bulk conversion flow ────────────────────────────────────────────────── */

/**
 * Upload multiple files, store results in state, render bulk list.
 * @param {File[]|FileList} files
 */
export async function uploadBulk(files) {
  const filesArr = Array.from(files);

  showStatus('status-bulk', 'info', `Uploading ${filesArr.length} file(s)…`);

  try {
    const data = await apiBulkUpload(filesArr);

    // Merge results into bulkFiles state
    data.files.forEach(f => {
      if (f.error) {
        addBulkFile({ filename: f.filename, error: f.error, status: 'error' });
      } else {
        addBulkFile({
          file_id:           f.file_id,
          filename:          f.filename,
          size:              f.size,
          category:          f.category,
          detected_format:   f.detected_format,
          available_formats: f.available_formats || [],
          target_format:     '',
          status:            'pending',
          error:             null,
        });
      }
    });

    clearStatus('status-bulk');
    renderBulkList(getBulkFiles());
    document.getElementById('bulk-list-card').style.display = '';
  } catch (err) {
    showStatus('status-bulk', 'error', buildErrorHtml(err.message, err.rawDetail || null));
  }
}

/**
 * Apply the global format selector value to all compatible bulk files.
 * Updates state and DOM select elements in-place.
 */
export function applyGlobalFormat() {
  const fmt = document.getElementById('bulk-global-fmt').value;
  if (!fmt) return;

  const bulkFiles = getBulkFiles();
  bulkFiles.forEach((f, i) => {
    if (!f.error && f.available_formats.includes(fmt)) {
      f.target_format = fmt;
      const sel = document.querySelector(`#bulk-row-${i} select`);
      if (sel) sel.value = fmt;
    }
  });
}

/**
 * Convert all bulk files that have a target format selected.
 */
export async function convertBulk() {
  const bulkFiles = getBulkFiles();
  const eligible = bulkFiles.filter(f => !f.error && f.target_format);

  if (!eligible.length) {
    showStatus('status-bulk', 'error', 'Select an output format for at least one file.');
    return;
  }

  const missing = bulkFiles.filter(f => !f.error && !f.target_format);
  if (missing.length) {
    showStatus('status-bulk', 'info',
      `${missing.length} file(s) have no format selected and will be skipped.`);
  } else {
    clearStatus('status-bulk');
  }

  const btn = document.getElementById('bulk-convert-btn');
  btn.disabled = true;
  btn.textContent = 'Converting…';

  // Mark eligible as converting
  bulkFiles.forEach((f, i) => {
    if (!f.error && f.target_format) updateBulkRowStatus(bulkFiles, i, 'converting', null);
  });

  const conversions = eligible.map(f => ({
    file_id:       f.file_id,
    target_format: f.target_format,
  }));

  try {
    const data = await apiBulkConvert(conversions, currentQuality);

    // Mark errors from partial failures
    if (data.errors && data.errors.length) {
      data.errors.forEach(e => {
        const i = bulkFiles.findIndex(f => f.file_id === e.file_id);
        if (i >= 0) updateBulkRowStatus(bulkFiles, i, 'error', e.message || 'Failed', e.detail || null);
      });
    }

    // Mark successes
    eligible.forEach(f => {
      const i = bulkFiles.indexOf(f);
      const wasError = data.errors && data.errors.some(e => e.file_id === f.file_id);
      if (!wasError) updateBulkRowStatus(bulkFiles, i, 'done', null);
    });

    // Add to history
    addToHistory({
      type:        'bulk',
      count:       data.count,
      errors:      (data.errors || []).length,
      quality:     currentQuality,
      download_id: data.download_id,
    });

    const dlUrl = apiDownloadUrl(data.download_id);
    const total  = eligible.length;
    const failed = (data.errors && data.errors.length) || 0;
    const summaryText = failed
      ? `${data.count} of ${total} files converted. ${failed} failed.`
      : `${data.count} file(s) converted.`;

    showStatus('status-bulk', 'success',
      `✓ ${summaryText}` +
      ` <a href="${dlUrl}" download="converted.zip" style="color:inherit;text-decoration:underline;margin-left:6px;">` +
      `↓ Download ZIP</a>`);
  } catch (err) {
    const allFailMsg = err.message;
    eligible.forEach(f => {
      const i = bulkFiles.indexOf(f);
      updateBulkRowStatus(bulkFiles, i, 'error', allFailMsg, null);
    });
    showStatus('status-bulk', 'error', buildErrorHtml(allFailMsg, err.rawDetail || null));
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg> Convert All`;
  }
}
