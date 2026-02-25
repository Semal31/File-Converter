/* ── API module — all fetch() calls to /api/* endpoints ─────────────────── */

import { currentQuality } from './state.js';

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
