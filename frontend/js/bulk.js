/* ── Bulk conversion feature module ──────────────────────────────────────── */

import {
  currentQuality,
  resetBulkState,
  getBulkFiles,
  addBulkFile,
  addToHistory,
} from './state.js';

import { apiBulkUploadWithProgress, apiConvert, watchJobProgress, apiBulkDownloadZip } from './api.js';

import {
  showStatus,
  clearStatus,
  buildErrorHtml,
  renderBulkList,
  updateBulkRowStatus,
  updateBulkRowProgress,
  esc,
} from './ui.js';

/* ── Bulk conversion flow ────────────────────────────────────────────────── */

/**
 * Upload multiple files using apiBulkUploadWithProgress, store results in
 * state, and render the bulk list.
 * @param {File[]|FileList} files
 */
export async function uploadBulk(files) {
  const filesArr = Array.from(files);

  showStatus('status-bulk', 'info', `Uploading ${filesArr.length} file(s)…`);

  try {
    const data = await apiBulkUploadWithProgress(filesArr, (_fileIndex, _ratio) => {
      // Upload progress per file — noted but not wired to rows here because
      // rows are added after upload completes (we don't yet have row indices).
      // General status message serves as upload phase feedback.
    });

    // Merge results into bulkFiles state
    data.files.forEach(f => {
      if (f.error) {
        addBulkFile({ filename: f.filename, error: f.error, status: 'error', progress: 0 });
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
          download_id:       null,
          progress:          0,
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
 * Per-file XHR conversion with individual SSE tracking per row.
 */
export async function convertBulk() {
  const bulkFiles = getBulkFiles();
  const eligible = bulkFiles.filter(f => !f.error && f.target_format && f.status === 'pending');

  if (!eligible.length) {
    showStatus('status-bulk', 'error', 'Select an output format for at least one file.');
    return;
  }

  const btn = document.getElementById('bulk-convert-btn');
  btn.disabled = true;
  btn.textContent = 'Converting…';
  clearStatus('status-bulk');

  // Hide summary and download-all from any previous run
  document.getElementById('bulk-summary').style.display = 'none';
  document.getElementById('bulk-download-all').style.display = 'none';

  // Mark eligible as converting
  eligible.forEach(f => {
    const i = bulkFiles.indexOf(f);
    updateBulkRowStatus(bulkFiles, i, 'converting', null);
    updateBulkRowProgress(i, 0, 'Starting…');
  });

  // Phase 1: Fire all conversions and collect job_ids
  const jobMap = []; // [{bulkIndex, jobId, file}]
  for (const f of eligible) {
    const i = bulkFiles.indexOf(f);
    try {
      const { job_id } = await apiConvert(f.file_id, f.target_format, currentQuality);
      jobMap.push({ bulkIndex: i, jobId: job_id, file: f });
      updateBulkRowProgress(i, 5, 'Queued');
    } catch (err) {
      updateBulkRowStatus(bulkFiles, i, 'error', err.message, err.rawDetail || null);
      updateBulkRowProgress(i, 0, '');
    }
  }

  // Phase 2: Open SSE for each queued job and track per-row
  const ssePromises = jobMap.map(({ bulkIndex, jobId }) =>
    watchJobProgress(jobId, (pct) => {
      updateBulkRowProgress(bulkIndex, pct, 'Converting…');
    })
    .then(downloadId => {
      bulkFiles[bulkIndex].download_id = downloadId;
      updateBulkRowStatus(bulkFiles, bulkIndex, 'done', null);
      updateBulkRowProgress(bulkIndex, 100, 'Done');
    })
    .catch(err => {
      updateBulkRowStatus(bulkFiles, bulkIndex, 'error', err.message, err.rawDetail || null);
      updateBulkRowProgress(bulkIndex, 0, '');
    })
  );

  await Promise.allSettled(ssePromises);

  // Phase 3: Show summary banner
  const doneFiles = bulkFiles.filter(f => f.status === 'done');
  const errorFiles = bulkFiles.filter(f => f.status === 'error');
  const total = eligible.length;
  const succeeded = doneFiles.length;
  const failed = errorFiles.length;

  const summary = document.getElementById('bulk-summary');
  if (succeeded === total) {
    summary.className = 'bulk-summary success';
    summary.textContent = `All ${succeeded} file(s) converted successfully.`;
  } else if (succeeded > 0) {
    summary.className = 'bulk-summary partial';
    summary.textContent = `${succeeded} of ${total} files converted. ${failed} failed.`;
  } else {
    summary.className = 'bulk-summary failure';
    summary.textContent = `All ${total} conversions failed.`;
  }
  summary.style.display = '';

  // Phase 4: Show Download All ZIP button (if any succeeded)
  if (doneFiles.length > 0) {
    const dlAll = document.getElementById('bulk-download-all');
    dlAll.innerHTML = `<button class="btn btn-success" id="bulk-dl-all-btn">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      Download All as ZIP (${doneFiles.length} file${doneFiles.length !== 1 ? 's' : ''})
    </button>`;
    dlAll.style.display = '';

    // Download All handler — hits /api/bulk-download-zip to get a single ZIP file
    document.getElementById('bulk-dl-all-btn').addEventListener('click', () => {
      const downloadIds = doneFiles
        .filter(f => f.download_id)
        .map(f => f.download_id);
      if (downloadIds.length > 0) {
        apiBulkDownloadZip(downloadIds);
      }
    });
  }

  // Add to history
  if (doneFiles.length > 0) {
    addToHistory({
      type:    'bulk',
      count:   doneFiles.length,
      errors:  failed,
      quality: currentQuality,
      // Use first completed file's download_id for the history link
      download_id: doneFiles[0].download_id,
    });
  }

  btn.disabled = false;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg> Convert All`;
}
