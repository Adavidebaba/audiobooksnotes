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
const btnDownloadJson = document.getElementById('btn-download-json');
const deleteModal = document.getElementById('delete-modal');
const btnCancelDelete = document.getElementById('modal-btn-cancel');
const btnConfirmDelete = document.getElementById('modal-btn-confirm');
const btnReprocess = document.getElementById('btn-reprocess');
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
    filterBookSelect.addEventListener('change', () => {
      toggleDownloadButtonVisibility();
      renderQuotes();
    });
  }
  if (filterConfidenceSelect) filterConfidenceSelect.addEventListener('change', renderQuotes);
  if (filterDateStart) filterDateStart.addEventListener('change', renderQuotes);
  if (filterDateEnd) filterDateEnd.addEventListener('change', renderQuotes);
  if (btnDownloadJson) btnDownloadJson.addEventListener('click', downloadSelectedBookQuotes);
  
  if (btnCancelDelete) btnCancelDelete.addEventListener('click', closeDeleteModal);
  if (btnConfirmDelete) btnConfirmDelete.addEventListener('click', executeDeleteQuote);
  if (btnReprocess) btnReprocess.addEventListener('click', handleDatabaseReprocess);
  
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
    showToast(`Errore: ${error.message}`, 'danger');
    quotesContainer.innerHTML = `
      <div class="empty-state">
        <h3 style="color: var(--accent-danger)">Errore di Caricamento</h3>
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
  
  filterBookSelect.innerHTML = '<option value="all">Tutti i libri</option>';
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
        <h3>Nessuna citazione trovata</h3>
        <p>Prova a modificare i filtri inseriti.</p>
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
 * Shows or hides the download button based on selection.
 */
function toggleDownloadButtonVisibility() {
  const selectedBook = filterBookSelect.value;
  btnDownloadJson.style.display = selectedBook !== 'all' ? 'inline-flex' : 'none';
}

/**
 * Filters the active book quotes, maps them to quote + mm:ss position, and triggers download with check.
 */
function downloadSelectedBookQuotes() {
  const selectedBookId = filterBookSelect.value;
  if (selectedBookId === 'all') return;
  
  const bookQuotes = quotesState.filter(q => q.libraryItemId === selectedBookId);
  if (bookQuotes.length === 0) {
    showToast('Nessuna citazione disponibile per questo libro.', 'danger');
    return;
  }
  
  // 2. Controllo: se ci sono citazioni con voto diverso da "High"
  const nonHighQuotes = bookQuotes.filter(q => q.quote_confidence.toLowerCase() !== 'high');
  if (nonHighQuotes.length > 0) {
    const confirmDownload = confirm(`⚠️ ATTENZIONE: Ci sono ${nonHighQuotes.length} citazioni con voto inferiore a "High" (Medium o Low).\n\nSi raccomanda vivamente di controllarle e correggerle prima di scaricare il file.\n\nVuoi procedere comunque con il download?`);
    if (!confirmDownload) return;
  }
  
  const bookTitle = bookQuotes[0].bookTitle || 'Libro';
  const bookAuthor = bookQuotes[0].bookAuthor || 'Autore';
  
  const downloadData = bookQuotes.map(q => ({
    citazione: q.quote || '',
    posizione: QuotesUiManager.formatTime(q.time)
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
  
  showToast('Download del file JSON avviato!', 'success');
}

/**
 * Triggers database reprocess after double safety confirmation.
 */
async function handleDatabaseReprocess() {
  const confirm1 = confirm("⚠️ ATTENZIONE: Questa operazione cancellerà TUTTE le citazioni correnti in locale e le rielaborerà da zero leggendole nuovamente da Audiobookshelf.\n\nVuoi procedere?");
  if (!confirm1) return;
  
  const confirm2 = confirm("🔥 CONFERMA DI SICUREZZA: L'operazione richiederà tempo e consumerà crediti API per ri-trascrivere e ri-analizzare con l'AI tutti i bookmark. Sei ASSOLUTAMENTE sicuro di voler procedere?");
  if (!confirm2) return;
  
  try {
    quotesContainer.innerHTML = `
      <div class="empty-state">
        <h3>Rigenerazione del database avviata...</h3>
        <p>Il server sta riprocessando tutti i bookmark da Audiobookshelf in background. I dati riappariranno gradualmente.</p>
      </div>
    `;
    
    await QuotesApiManager.triggerDatabaseReprocess();
    showToast("Rigenerazione avviata con successo!", "success");
    
    quotesState = [];
    let pollCount = 0;
    const intervalId = setInterval(async () => {
      await loadQuotesFromServer();
      pollCount++;
      if (quotesState.length > 0 && pollCount > 2) {
        clearInterval(intervalId);
      }
      if (pollCount > 24) clearInterval(intervalId);
    }, 5000);
    
  } catch (error) {
    showToast(`Errore: ${error.message}`, "danger");
    await loadQuotesFromServer();
  }
}

// Window Globals for Inline DOM click events

window.toggleDetails = function(libraryItemId, createdAt, btn) {
  const details = document.getElementById(`details-${libraryItemId}-${createdAt}`);
  if (details.classList.contains('expanded')) {
    details.classList.remove('expanded');
    btn.textContent = 'Espandi dettagli';
  } else {
    details.classList.add('expanded');
    btn.textContent = 'Riduci dettagli';
  }
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
    btn.innerHTML = '✏️ Verifica';
    btn.title = 'Verifica o modifica questa citazione';
  } else {
    // Enter edit mode: sync textarea from blockquote
    const blockquote = readView.querySelector('.quote-blockquote');
    const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
    textarea.value = blockquote.textContent;
    card.classList.add('editing');
    btn.innerHTML = '✕ Chiudi';
    btn.title = 'Chiudi modifica';
    textarea.focus();
  }
};

window.saveQuoteUpdate = async function(libraryItemId, createdAt) {
  const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
  const selector = document.getElementById(`select-val-${libraryItemId}-${createdAt}`);
  const badge = document.getElementById(`badge-val-${libraryItemId}-${createdAt}`);
  
  const newQuote = textarea.value.trim();
  
  // 1. Assegna automaticamente "high" quando l'utente modifica e salva
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
    
    showToast('Citazione salvata con successo! Voto impostato ad High.', 'success');
  } catch (error) {
    showToast(`Errore: ${error.message}`, 'danger');
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
    showToast('Citazione eliminata con successo!', 'success');
  } catch (error) {
    showToast(`Errore: ${error.message}`, 'danger');
    closeDeleteModal();
  }
}

window.reprocessSingleQuote = async function(libraryItemId, createdAt, btn) {
  const card = document.getElementById(`quote-card-${libraryItemId}-${createdAt}`);
  if (!card) return;
  
  const confirmReprocess = confirm("Sei sicuro di voler ri-estrarre questa citazione?\n\nQuesto scaricherà una porzione di audio più ampia del 20% rispetto a quella attuale, rieseguirà Whisper e interrogherà nuovamente l'AI.");
  if (!confirmReprocess) return;
  
  card.classList.add('card-loading');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '🔄 Rielaborazione...';
  
  try {
    const updatedQuote = await QuotesApiManager.reprocessSingleQuote(libraryItemId, createdAt);
    
    const index = quotesState.findIndex(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
    if (index !== -1) {
      quotesState[index] = updatedQuote;
    }
    
    const newCard = QuotesUiManager.createQuoteCard(updatedQuote);
    card.parentNode.replaceChild(newCard, card);
    
    const newDetails = document.getElementById(`details-${libraryItemId}-${createdAt}`);
    const newBtn = newCard.querySelector('.btn-secondary');
    if (newDetails) {
      newDetails.classList.add('expanded');
      if (newBtn) newBtn.textContent = 'Riduci dettagli';
    }
    
    showToast('Citazione rielaborata e aggiornata con successo!', 'success');
  } catch (error) {
    showToast(`Errore: ${error.message}`, 'danger');
    card.classList.remove('card-loading');
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
};

// Kickstart
initApp();
