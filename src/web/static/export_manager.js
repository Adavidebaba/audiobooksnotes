/**
 * ExportManager - Centralized module for exporting quotes to Readwise CSV and JSON.
 * Adheres strictly to RFC 4180 CSV specifications and Readwise format guidelines.
 */
export class ExportManager {
  /**
   * Escapes special characters for CSV compliance.
   * @param {*} field 
   * @returns {string}
   */
  static escapeCsvField(field) {
    if (field === null || field === undefined) return '';
    const stringVal = String(field);
    if (stringVal.includes('"') || stringVal.includes(',') || stringVal.includes('\n') || stringVal.includes('\r')) {
      return `"${stringVal.replace(/"/g, '""')}"`;
    }
    return stringVal;
  }

  /**
   * Formats timestamp into UTC YYYY-MM-DD HH:mm:ss for Readwise compatibility.
   * @param {number} timestamp 
   * @returns {string}
   */
  static formatCsvDate(timestamp) {
    const d = new Date(timestamp || Date.now());
    const year = d.getUTCFullYear();
    const month = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day = String(d.getUTCDate()).padStart(2, '0');
    const hour = String(d.getUTCHours()).padStart(2, '0');
    const minute = String(d.getUTCMinutes()).padStart(2, '0');
    const second = String(d.getUTCSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
  }

  /**
   * Utility to format seconds into mm:ss format.
   * @param {number} secs 
   * @returns {string}
   */
  static formatTime(secs) {
    const m = Math.floor((secs || 0) / 60);
    const s = Math.floor((secs || 0) % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  /**
   * Triggers a browser download using a temporary anchor element.
   * @param {Blob} blob 
   * @param {string} filename 
   */
  static triggerDownload(blob, filename) {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
  }

  /**
   * Exports quotes of a single book as a formatted JSON file.
   * @param {Array} bookQuotes 
   * @param {string} bookTitle 
   * @param {string} bookAuthor 
   */
  static exportBookJson(bookQuotes, bookTitle, bookAuthor) {
    const downloadData = bookQuotes.map(q => ({
      quote: q.quote || '',
      position: this.formatTime(q.time)
    }));

    const jsonString = JSON.stringify(downloadData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    const safeFilename = `${bookTitle || 'Book'} - ${bookAuthor || 'Author'}`.replace(/[\\/:*?"<>|]/g, '_');
    this.triggerDownload(blob, `${safeFilename}.json`);
  }

  /**
   * Exports quotes of a single book as a Readwise-compliant CSV file.
   * @param {Array} bookQuotes 
   * @param {string} bookTitle 
   * @param {string} bookAuthor 
   */
  static exportBookReadwiseCsv(bookQuotes, bookTitle, bookAuthor) {
    const headers = ['Highlight', 'Title', 'Author', 'URL', 'Note', 'Location', '"Date"'];
    const rows = bookQuotes.map(q => [
      this.escapeCsvField(q.quote || ''),
      this.escapeCsvField(bookTitle || q.bookTitle || 'Unknown Book'),
      this.escapeCsvField(bookAuthor || q.bookAuthor || 'Unknown Author'),
      '""', // URL empty for audiobooks
      '""', // Note empty
      Math.floor(q.time || 0),
      `"${this.formatCsvDate(q.createdAt)}"`
    ]);

    const csvContent = '\ufeff' + [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const safeFilename = `${bookTitle || 'Book'} - ${bookAuthor || 'Author'} - Readwise`.replace(/[\\/:*?"<>|]/g, '_');
    this.triggerDownload(blob, `${safeFilename}.csv`);
  }

  /**
   * Exports an array of YouTube quotes into a Readwise-compliant CSV.
   * @param {Array} youtubeQuotes 
   */
  static exportYouTubeReadwiseCsv(youtubeQuotes) {
    const headers = ['Highlight', 'Title', 'Author', 'URL', 'Note', 'Location', '"Date"'];
    const rows = youtubeQuotes.map(q => [
      this.escapeCsvField(q.quote || ''),
      this.escapeCsvField(q.bookTitle || 'YouTube Video'),
      this.escapeCsvField(q.bookAuthor || 'YouTube Channel'),
      this.escapeCsvField(q.video_url || ''),
      this.escapeCsvField(q.quote_original && q.quote_original !== q.quote ? `Original (${(q.quote_language || 'orig').toUpperCase()}): ${q.quote_original}` : ''),
      Math.floor(q.time || 0),
      `"${this.formatCsvDate(q.createdAt)}"`
    ]);

    const csvContent = '\ufeff' + [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const nowStr = new Date().toISOString().split('T')[0];
    const safeFilename = `YouTube_Quotes_Export_${nowStr}_Readwise.csv`;
    this.triggerDownload(blob, safeFilename);
  }

  /**
   * Exports an array of YouTube quotes into a clean JSON array file.
   * @param {Array} youtubeQuotes 
   */
  static exportYouTubeJson(youtubeQuotes) {
    const downloadData = youtubeQuotes.map(q => ({
      video_title: q.bookTitle || '',
      channel: q.bookAuthor || '',
      video_url: q.video_url || '',
      position_seconds: q.time || 0,
      position_label: this.formatTime(q.time),
      quote: q.quote || '',
      quote_original: q.quote_original || null,
      quote_language: q.quote_language || null,
      confidence: q.quote_confidence || 'low',
      created_at: q.createdAt ? new Date(q.createdAt).toISOString() : null
    }));

    const jsonString = JSON.stringify(downloadData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    const nowStr = new Date().toISOString().split('T')[0];
    const safeFilename = `YouTube_Quotes_Export_${nowStr}.json`;
    this.triggerDownload(blob, safeFilename);
  }
}
