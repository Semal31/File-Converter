/* ── API module — all fetch() calls to /api/* endpoints ─────────────────── */

const API = '';  // same origin; empty string = relative URLs

/**
 * Upload a single file.
 * @param {File} file
 * @returns {Promise<{file_id: string, filename: string, size: number, format: string, category: string, formats: string[]}>}
 */
export async function apiUpload(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API}/api/upload`, { method: 'POST', body: fd });
  return res.json().then(data => {
    if (!res.ok) {
      const err = new Error((data && data.message) || 'Upload failed');
      err.rawDetail = (data && data.detail) || null;
      throw err;
    }
    return data;
  });
}

/**
 * Upload a single file with upload progress reporting via XHR.
 * @param {File} file
 * @param {function(number): void} onProgress - called with ratio 0.0-1.0 as data uploads
 * @returns {Promise<Object>}
 */
export function apiUploadWithProgress(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const fd = new FormData();
    fd.append('file', file);

    // MUST be registered BEFORE xhr.send()
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(e.loaded / e.total);  // 0.0 to 1.0
      }
    });

    xhr.addEventListener('load', () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 400) {
          const err = new Error((data && data.message) || 'Upload failed');
          err.rawDetail = (data && data.detail) || null;
          reject(err);
        } else {
          resolve(data);
        }
      } catch {
        reject(new Error('Invalid server response'));
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
    xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));

    xhr.open('POST', '/api/upload');
    xhr.send(fd);
  });
}

/**
 * Watch conversion job progress via SSE (EventSource).
 * Backend sends unnamed events, so we listen on 'message'.
 * Always closes the EventSource on terminal states to prevent reconnect loops.
 * @param {string} jobId
 * @param {function(number): void} onProgress - called with percent 0-99 during running state
 * @returns {Promise<string>} resolves with download_id on done, rejects on error
 */
export function watchJobProgress(jobId, onProgress) {
  return new Promise((resolve, reject) => {
    const es = new EventSource(`/api/progress/${jobId}`);

    // Backend sends unnamed events -> 'message' listener (NOT 'done' or 'running')
    es.addEventListener('message', (e) => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }

      if (msg.state === 'running') {
        if (onProgress) onProgress(msg.percent);  // 0-99
      } else if (msg.state === 'done') {
        es.close();  // MUST close to prevent reconnect loop
        resolve(msg.download_id);
      } else if (msg.state === 'error') {
        es.close();  // MUST close to prevent reconnect loop
        const err = new Error(msg.message || 'Conversion failed');
        err.rawDetail = msg.detail || null;
        reject(err);
      }
    });

    es.addEventListener('error', () => {
      es.close();
      reject(new Error('Progress connection lost'));
    });
  });
}

/**
 * Upload multiple files individually via XHR, reporting per-file progress.
 * Files are uploaded sequentially to avoid overwhelming the server.
 * Each file gets its own XHR so per-file progress is accurate.
 * @param {File[]} files
 * @param {function(number, number): void} onFileProgress - called with (fileIndex, ratio 0.0-1.0)
 * @returns {Promise<{files: Array, count: number}>}
 */
export async function apiBulkUploadWithProgress(files, onFileProgress) {
  const results = [];
  for (let i = 0; i < files.length; i++) {
    try {
      const data = await apiUploadWithProgress(files[i], (ratio) => {
        if (onFileProgress) onFileProgress(i, ratio);
      });
      results.push(data);
    } catch (err) {
      results.push({
        filename: files[i].name,
        error: err.message,
      });
    }
  }
  return { files: results, count: results.length };
}

/**
 * Trigger a ZIP download of multiple converted files from the backend.
 * Uses a hidden <a> element click so the browser handles the file download.
 * @param {string[]} downloadIds - list of download_id values from completed conversions
 */
export function apiBulkDownloadZip(downloadIds) {
  // Build URL with query params: /api/bulk-download-zip?ids=uuid1&ids=uuid2&...
  const params = new URLSearchParams();
  downloadIds.forEach(id => params.append('ids', id));
  const url = `/api/bulk-download-zip?${params.toString()}`;

  // Trigger browser download via hidden <a> element
  const a = document.createElement('a');
  a.href = url;
  a.download = 'converted-files.zip';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Convert a single file.
 * NOTE: As of Phase 3, this returns {job_id} for async processing.
 * @param {string} fileId
 * @param {string} targetFormat
 * @param {string} quality
 * @returns {Promise<Object>}
 */
export async function apiConvert(fileId, targetFormat, quality) {
  const fd = new FormData();
  fd.append('file_id', fileId);
  fd.append('target_format', targetFormat);
  fd.append('quality', quality);
  const res = await fetch(`${API}/api/convert`, { method: 'POST', body: fd });
  return res.json().then(data => {
    if (!res.ok) {
      const err = new Error((data && data.message) || 'Conversion failed');
      err.rawDetail = (data && data.detail) || null;
      throw err;
    }
    return data;
  });
}

/**
 * Upload multiple files for bulk conversion.
 * @param {File[]} files
 * @returns {Promise<Object>}
 */
export async function apiBulkUpload(files) {
  const fd = new FormData();
  files.forEach(f => fd.append('files', f));
  const res = await fetch(`${API}/api/bulk-upload`, { method: 'POST', body: fd });
  return res.json().then(data => {
    if (!res.ok) {
      const err = new Error((data && data.message) || 'Upload failed');
      err.rawDetail = (data && data.detail) || null;
      throw err;
    }
    return data;
  });
}

/**
 * Start bulk conversion.
 * NOTE: As of Phase 3, this returns job_ids for async processing.
 * @param {Array<{file_id: string, target_format: string}>} items
 * @param {string} quality
 * @returns {Promise<Object>}
 */
export async function apiBulkConvert(items, quality) {
  const fd = new FormData();
  fd.append('conversions', JSON.stringify(items));
  fd.append('quality', quality);
  const res = await fetch(`${API}/api/bulk-convert`, { method: 'POST', body: fd });
  return res.json().then(data => {
    if (!res.ok) {
      const err = new Error((data && data.message) || 'Bulk conversion failed.');
      err.rawDetail = (data && data.detail) || null;
      throw err;
    }
    return data;
  });
}

/**
 * Build the download URL for a given download ID (no fetch needed).
 * @param {string} downloadId
 * @returns {string}
 */
export function apiDownloadUrl(downloadId) {
  return `${API}/api/download/${downloadId}`;
}
