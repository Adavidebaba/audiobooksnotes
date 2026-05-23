/**
 * AudiobookNotes Dashboard - Client-side state coordinator and UI controller.
 * Imports networking from api.js and templates/formatting from ui.js.
 */
import { QuotesApiManager } from './api.js';
import { QuotesUiManager } from './ui.js';

// Global State
let quotesState = [];
let selectedQuoteToDelete = null;

// DOM Elements
const quotesContainer = document.getElementById('quotes-container');
const filterBookSelect = document.getElementById('filter-book');
const filterConfidenceSelect = document.getElementById('filter-confidence');
const filterDateStart = document.getElementById('filter-date-start');
const filterDateEnd = document.getElementById('filter-date-end');
const deleteModal = document.getElementById('delete-modal');
const btnCancelDelete = document.getElementById('modal-btn-cancel');
const btnConfirmDelete = document.getElementById('modal-btn-confirm');
const toastNotification = document.getElementById('toast');

/**
 * Bootstraps the application by fetching data and binding event listeners.
 */
async function initApp() {
  bindEventListeners();
  await loadQuotesFromServer();
}

/**
 * Binds DOM event listeners for reactive filtering and interactions.
 */
function bindEventListeners() {
  if (filterBookSelect) {
    filterBookSelect.addEventListener('change', renderQuotes);
  }
  if (filterConfidenceSelect) filterConfidenceSelect.addEventListener('change', renderQuotes);
  if (filterDateStart) filterDateStart.addEventListener('change', renderQuotes);
  if (filterDateEnd) filterDateEnd.addEventListener('change', renderQuotes);
  
  if (btnCancelDelete) btnCancelDelete.addEventListener('click', closeDeleteModal);
  if (btnConfirmDelete) btnConfirmDelete.addEventListener('click', executeDeleteQuote);
  
  if (deleteModal) {
    deleteModal.addEventListener('click', (e) => {
      if (e.target === deleteModal) closeDeleteModal();
    });
  }
}

/**
 * Fetches quotes list from server and initialises dropdown filters.
 */
async function loadQuotesFromServer() {
  try {
    quotesState = await QuotesApiManager.fetchQuotes();
    populateBookFilter();
    renderQuotes();
  } catch (error) {
    showToast(`Error: ${error.message}`, 'danger');
    quotesContainer.innerHTML = `
      <div class="empty-state">
        <h3 style="color: var(--accent-danger)">Loading Error</h3>
        <p>${error.message}</p>
      </div>
    `;
  }
}

/**
 * Generates unique book choices based on returned quotes data.
 */
function populateBookFilter() {
  const booksMap = new Map();
  quotesState.forEach(quote => {
    booksMap.set(quote.libraryItemId, quote.bookTitle);
  });
  
  filterBookSelect.innerHTML = '<option value="all">All books</option>';
  booksMap.forEach((title, id) => {
    const option = document.createElement('option');
    option.value = id;
    option.textContent = title;
    filterBookSelect.appendChild(option);
  });
}

/**
 * Checks if a single quote passes active filter criteria.
 */
function passesFilters(quote) {
  const selectedBook = filterBookSelect.value;
  const selectedConfidence = filterConfidenceSelect.value;
  const startDateStr = filterDateStart.value;
  const endDateStr = filterDateEnd.value;
  
  if (selectedBook !== 'all' && quote.libraryItemId !== selectedBook) return false;
  if (selectedConfidence !== 'all' && quote.quote_confidence !== selectedConfidence) return false;
  
  if (quote.createdAt) {
    const quoteDate = new Date(quote.createdAt).toISOString().split('T')[0];
    if (startDateStr && quoteDate < startDateStr) return false;
    if (endDateStr && quoteDate > endDateStr) return false;
  }
  
  return true;
}

/**
 * Triggers re-rendering of active filter state.
 */
function renderQuotes() {
  const filtered = quotesState.filter(passesFilters);
  
  if (filtered.length === 0) {
    quotesContainer.innerHTML = `
      <div class="empty-state">
        <h3>No quotes found</h3>
        <p>Try adjusting the active filters.</p>
      </div>
    `;
    return;
  }
  
  // Group quotes by libraryItemId preserving backend sort (time asc)
  const bookGroups = new Map();
  filtered.forEach(quote => {
    const bookId = quote.libraryItemId;
    if (!bookGroups.has(bookId)) {
      bookGroups.set(bookId, {
        title: quote.bookTitle,
        author: quote.bookAuthor,
        quotes: []
      });
    }
    bookGroups.get(bookId).quotes.push(quote);
  });
  
  quotesContainer.innerHTML = '';
  bookGroups.forEach((bookGroup) => {
    const section = QuotesUiManager.createBookSection(
      bookGroup.title,
      bookGroup.author,
      bookGroup.quotes
    );
    quotesContainer.appendChild(section);
  });
}

/**
 * Shows visual toast feedback.
 */
function showToast(message, type = 'success') {
  toastNotification.textContent = message;
  
  if (type === 'danger') {
    toastNotification.style.background = 'linear-gradient(135deg, var(--accent-danger), #b91c1c)';
    toastNotification.style.boxShadow = '0 10px 25px rgba(239, 68, 68, 0.3)';
  } else {
    toastNotification.style.background = 'linear-gradient(135deg, var(--accent-success), #059669)';
    toastNotification.style.boxShadow = '0 10px 25px rgba(16, 185, 129, 0.3)';
  }
  
  toastNotification.classList.add('active');
  setTimeout(() => {
    toastNotification.classList.remove('active');
  }, 3000);
}

/**
 * Filters the active book quotes by libraryItemId, maps them, and triggers download.
 */
window.downloadBookQuotes = function(libraryItemId) {
  const bookQuotes = quotesState.filter(q => q.libraryItemId === libraryItemId);
  if (bookQuotes.length === 0) {
    showToast('No quotes available for this book.', 'danger');
    return;
  }
  
  // Safety check: if there are quotes with confidence below "High"
  const nonHighQuotes = bookQuotes.filter(q => q.quote_confidence.toLowerCase() !== 'high');
  if (nonHighQuotes.length > 0) {
    const confirmDownload = confirm(`⚠️ WARNING: There are ${nonHighQuotes.length} quotes with confidence level below "High" (Medium or Low).\n\nIt is strongly recommended to verify and correct them before downloading.\n\nDo you want to proceed anyway?`);
    if (!confirmDownload) return;
  }
  
  const bookTitle = bookQuotes[0].bookTitle || 'Book';
  const bookAuthor = bookQuotes[0].bookAuthor || 'Author';
  
  const downloadData = bookQuotes.map(q => ({
    quote: q.quote || '',
    position: QuotesUiManager.formatTime(q.time)
  }));
  
  const jsonString = JSON.stringify(downloadData, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
  const safeFilename = `${bookTitle} - ${bookAuthor}`.replace(/[\\/:*?"<>|]/g, '_');
  
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', `${safeFilename}.json`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  showToast('JSON file download started!', 'success');
};

/**
 * Helper to escape quotes, commas, and newlines for robust RFC 4180 CSV compliance.
 */
function escapeCsvField(field) {
  if (field === null || field === undefined) return '';
  const stringVal = String(field);
  if (stringVal.includes('"') || stringVal.includes(',') || stringVal.includes('\n') || stringVal.includes('\r')) {
    return `"${stringVal.replace(/"/g, '""')}"`;
  }
  return stringVal;
}

/**
 * Helper to format timestamp to UTC YYYY-MM-DD HH:mm:ss for Readwise compatibility.
 */
function formatCsvDate(timestamp) {
  const d = new Date(timestamp);
  const year = d.getUTCFullYear();
  const month = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  const hour = String(d.getUTCHours()).padStart(2, '0');
  const minute = String(d.getUTCMinutes()).padStart(2, '0');
  const second = String(d.getUTCSeconds()).padStart(2, '0');
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

/**
 * Filters the active book quotes by libraryItemId and exports them as a Readwise-compliant CSV file.
 */
window.downloadBookReadwiseCsv = function(libraryItemId) {
  const bookQuotes = quotesState.filter(q => q.libraryItemId === libraryItemId);
  if (bookQuotes.length === 0) {
    showToast('No quotes available for this book.', 'danger');
    return;
  }
  
  // Safety check: if there are quotes with confidence below "High"
  const nonHighQuotes = bookQuotes.filter(q => q.quote_confidence.toLowerCase() !== 'high');
  if (nonHighQuotes.length > 0) {
    const confirmDownload = confirm(`⚠️ WARNING: There are ${nonHighQuotes.length} quotes with confidence level below "High" (Medium or Low).\n\nIt is strongly recommended to verify and correct them before importing to Readwise.\n\nDo you want to proceed anyway?`);
    if (!confirmDownload) return;
  }
  
  const bookTitle = bookQuotes[0].bookTitle || 'Book';
  const bookAuthor = bookQuotes[0].bookAuthor || 'Author';
  
  const headers = ['Highlight', 'Title', 'Author', 'URL', 'Note', 'Location', '"Date"'];
  const rows = bookQuotes.map(q => [
    escapeCsvField(q.quote || ''),
    escapeCsvField(q.bookTitle || ''),
    escapeCsvField(q.bookAuthor || ''),
    '""', // URL always empty
    '""', // Note always empty
    Math.floor(q.time || 0),
    `"${formatCsvDate(q.createdAt || Date.now())}"`
  ]);
  
  const csvContent = '\ufeff' + [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const safeFilename = `${bookTitle} - ${bookAuthor} - Readwise`.replace(/[\\/:*?"<>|]/g, '_');
  
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', `${safeFilename}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  showToast('Readwise CSV download started!', 'success');
};

window.toggleEditMode = function(libraryItemId, createdAt, btn) {
  const readView = document.getElementById(`read-view-${libraryItemId}-${createdAt}`);
  const editView = document.getElementById(`edit-view-${libraryItemId}-${createdAt}`);
  const card = document.getElementById(`quote-card-${libraryItemId}-${createdAt}`);
  
  const isEditing = card.classList.contains('editing');
  
  if (isEditing) {
    // Exit edit mode: update blockquote text from textarea
    const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
    const blockquote = readView.querySelector('.quote-blockquote');
    blockquote.textContent = textarea.value;
    card.classList.remove('editing');
    btn.innerHTML = '✏️ Verify';
    btn.title = 'Verify or edit this quote';
  } else {
    // Enter edit mode: sync textarea from blockquote
    const blockquote = readView.querySelector('.quote-blockquote');
    const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
    textarea.value = blockquote.textContent;
    card.classList.add('editing');
    btn.innerHTML = '✕ Close';
    btn.title = 'Close edit';
    textarea.focus();
  }
};

window.saveQuoteUpdate = async function(libraryItemId, createdAt) {
  const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
  const selector = document.getElementById(`select-val-${libraryItemId}-${createdAt}`);
  const badge = document.getElementById(`badge-val-${libraryItemId}-${createdAt}`);
  
  const newQuote = textarea.value.trim();
  
  // 1. Automatically assign "high" confidence upon manual verification
  selector.value = 'high';
  const newConfidence = 'high';
  
  try {
    await QuotesApiManager.updateQuote(libraryItemId, createdAt, newQuote, newConfidence);
    
    const index = quotesState.findIndex(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
    if (index !== -1) {
      quotesState[index].quote = newQuote;
      quotesState[index].quote_confidence = newConfidence;
    }
    
    badge.textContent = 'High';
    badge.className = 'badge badge-high';
    
    showToast('Quote saved successfully! Confidence set to High.', 'success');
  } catch (error) {
    showToast(`Error: ${error.message}`, 'danger');
  }
};

window.confirmDeleteQuote = function(libraryItemId, createdAt) {
  selectedQuoteToDelete = { libraryItemId, createdAt };
  deleteModal.classList.add('active');
};

function closeDeleteModal() {
  selectedQuoteToDelete = null;
  deleteModal.classList.remove('active');
}

async function executeDeleteQuote() {
  if (!selectedQuoteToDelete) return;
  const { libraryItemId, createdAt } = selectedQuoteToDelete;
  
  try {
    await QuotesApiManager.deleteQuote(libraryItemId, createdAt);
    quotesState = quotesState.filter(q => !(q.libraryItemId === libraryItemId && q.createdAt === createdAt));
    closeDeleteModal();
    renderQuotes();
    showToast('Quote deleted successfully!', 'success');
  } catch (error) {
    showToast(`Error: ${error.message}`, 'danger');
    closeDeleteModal();
  }
}

window.reprocessSingleQuote = async function(libraryItemId, createdAt, btn) {
  const card = document.getElementById(`quote-card-${libraryItemId}-${createdAt}`);
  if (!card) return;
  
  const confirmReprocess = confirm("Are you sure you want to re-extract this quote?\n\nThis will download an audio window that is 20% wider than the current one, rerun Whisper, and query the LLM again.");
  if (!confirmReprocess) return;
  
  card.classList.add('card-loading');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '🔄 Reprocessing...';
  
  try {
    const updatedQuote = await QuotesApiManager.reprocessSingleQuote(libraryItemId, createdAt);
    
    const index = quotesState.findIndex(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
    if (index !== -1) {
      quotesState[index] = updatedQuote;
    }
    
    const newCard = QuotesUiManager.createQuoteCard(updatedQuote);
    card.parentNode.replaceChild(newCard, card);
    
    // Automatically keep in edit/expanded state to show the updated quote details
    newCard.classList.add('editing');
    const newBtn = newCard.querySelector('.btn-edit-toggle');
    if (newBtn) {
      newBtn.innerHTML = '✕ Close';
    }
    
    showToast('Quote re-extracted and updated successfully!', 'success');
  } catch (error) {
    showToast(`Error: ${error.message}`, 'danger');
    card.classList.remove('card-loading');
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
};

// Kickstart
initApp();
