/**
 * AudiobookNotes Dashboard - AppCoordinator
 * Coordinates state, active tab, filtering, editing, and exports.
 */
import { QuotesApiManager } from './api.js';
import { QuotesUiManager } from './ui.js';
import { ExportManager } from './export_manager.js';

// State
let quotesState = [];
let activeTab = 'audiobooks'; // 'audiobooks' | 'youtube'
let selectedQuoteToDelete = null;

// DOM Elements
const quotesContainer = document.getElementById('quotes-container');
const tabBtnAudiobooks = document.getElementById('tab-btn-audiobooks');
const tabBtnYouTube = document.getElementById('tab-btn-youtube');
const countAudiobooks = document.getElementById('count-audiobooks');
const countYouTube = document.getElementById('count-youtube');
const labelFilterSource = document.getElementById('label-filter-source');
const filterSourceSelect = document.getElementById('filter-book');
const filterConfidenceSelect = document.getElementById('filter-confidence');
const filterDateStart = document.getElementById('filter-date-start');
const filterDateEnd = document.getElementById('filter-date-end');
const deleteModal = document.getElementById('delete-modal');
const btnCancelDelete = document.getElementById('modal-btn-cancel');
const btnConfirmDelete = document.getElementById('modal-btn-confirm');
const btnManualPoll = document.getElementById('btn-manual-poll');
const toastNotification = document.getElementById('toast');

/**
 * Initializes application coordinator.
 */
async function initApp() {
  bindEventListeners();
  await loadQuotesFromServer();
}

/**
 * Binds event listeners for tabs, filters, and modals.
 */
function bindEventListeners() {
  if (btnManualPoll) {
    btnManualPoll.addEventListener('click', handleManualPoll);
  }

  if (tabBtnAudiobooks) {
    tabBtnAudiobooks.addEventListener('click', () => switchTab('audiobooks'));
  }
  if (tabBtnYouTube) {
    tabBtnYouTube.addEventListener('click', () => switchTab('youtube'));
  }

  if (filterSourceSelect) filterSourceSelect.addEventListener('change', renderQuotes);
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

  // Close YouTube export dropdown when clicking outside
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('youtube-export-dropdown');
    const toggleBtn = document.getElementById('btn-export-youtube-toggle');
    if (dropdown && dropdown.classList.contains('show')) {
      if (!dropdown.contains(e.target) && (!toggleBtn || !toggleBtn.contains(e.target))) {
        dropdown.classList.remove('show');
      }
    }
  });
}

/**
 * Switches the active dashboard section between Audiobooks and YouTube.
 * @param {'audiobooks' | 'youtube'} tab 
 */
function switchTab(tab) {
  if (activeTab === tab) return;
  activeTab = tab;

  if (activeTab === 'audiobooks') {
    tabBtnAudiobooks.classList.add('active');
    tabBtnYouTube.classList.remove('active');
    if (labelFilterSource) labelFilterSource.textContent = 'Seleziona Libro';
  } else {
    tabBtnYouTube.classList.add('active');
    tabBtnAudiobooks.classList.remove('active');
    if (labelFilterSource) labelFilterSource.textContent = 'Seleziona Video / Canale';
  }

  populateSourceFilter();
  renderQuotes();
}

/**
 * Loads all quotes data from backend API.
 */
async function loadQuotesFromServer() {
  try {
    quotesState = await QuotesApiManager.fetchQuotes();
    updateTabCounters();
    populateSourceFilter();
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
 * Updates badge counters in tabs.
 */
function updateTabCounters() {
  const audiobookQuotes = quotesState.filter(q => q.source_type !== 'youtube');
  const youtubeQuotes = quotesState.filter(q => q.source_type === 'youtube');

  if (countAudiobooks) countAudiobooks.textContent = audiobookQuotes.length;
  if (countYouTube) countYouTube.textContent = youtubeQuotes.length;
}

/**
 * Populates source dropdown depending on the active tab.
 */
function populateSourceFilter() {
  if (!filterSourceSelect) return;

  const currentSelection = filterSourceSelect.value;
  const isAudiobooks = activeTab === 'audiobooks';
  const filteredPool = quotesState.filter(q => isAudiobooks ? q.source_type !== 'youtube' : q.source_type === 'youtube');

  const sourcesMap = new Map();
  filteredPool.forEach(q => {
    sourcesMap.set(q.libraryItemId, q.bookTitle);
  });

  filterSourceSelect.innerHTML = isAudiobooks
    ? '<option value="all">Tutti i libri</option>'
    : '<option value="all">Tutti i video</option>';

  sourcesMap.forEach((title, id) => {
    const option = document.createElement('option');
    option.value = id;
    option.textContent = title;
    filterSourceSelect.appendChild(option);
  });

  if (sourcesMap.has(currentSelection)) {
    filterSourceSelect.value = currentSelection;
  } else {
    filterSourceSelect.value = 'all';
  }
}

/**
 * Evaluates filter criteria for an individual quote.
 * @param {Object} quote 
 * @returns {boolean}
 */
function passesFilters(quote) {
  const isAudiobooks = activeTab === 'audiobooks';
  const isQuoteAudiobook = quote.source_type !== 'youtube';

  // Tab filter match
  if (isAudiobooks !== isQuoteAudiobook) return false;

  const selectedSource = filterSourceSelect ? filterSourceSelect.value : 'all';
  const selectedConfidence = filterConfidenceSelect ? filterConfidenceSelect.value : 'all';
  const startDateStr = filterDateStart ? filterDateStart.value : '';
  const endDateStr = filterDateEnd ? filterDateEnd.value : '';

  if (selectedSource !== 'all' && quote.libraryItemId !== selectedSource) return false;
  if (selectedConfidence !== 'all' && (quote.quote_confidence || '').toLowerCase() !== selectedConfidence) return false;

  if (quote.createdAt) {
    const quoteDate = new Date(quote.createdAt).toISOString().split('T')[0];
    if (startDateStr && quoteDate < startDateStr) return false;
    if (endDateStr && quoteDate > endDateStr) return false;
  }

  return true;
}

/**
 * Renders active quotes based on the current tab and filter settings.
 */
function renderQuotes() {
  const filtered = quotesState.filter(passesFilters);

  if (filtered.length === 0) {
    quotesContainer.innerHTML = `
      <div class="empty-state">
        <h3>Nessuna citazione trovata</h3>
        <p>Prova a modificare i filtri attivi o seleziona un'altra categoria.</p>
      </div>
    `;
    return;
  }

  quotesContainer.innerHTML = '';

  if (activeTab === 'audiobooks') {
    // Group quotes by book preserving audio position order
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

    bookGroups.forEach(bookGroup => {
      quotesContainer.appendChild(
        QuotesUiManager.createBookSection(bookGroup.title, bookGroup.author, bookGroup.quotes)
      );
    });
  } else {
    // Pure chronological order for YouTube stream (most recent first)
    const sortedYouTubeQuotes = [...filtered].sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
    quotesContainer.appendChild(QuotesUiManager.createYouTubeFeed(sortedYouTubeQuotes));
  }
}

/**
 * Displays toast notification message.
 */
function showToast(message, type = 'success') {
  if (!toastNotification) return;
  toastNotification.textContent = message;

  if (type === 'danger') {
    toastNotification.style.background = 'linear-gradient(135deg, var(--accent-danger), #b91c1c)';
    toastNotification.style.boxShadow = '0 10px 25px rgba(239, 68, 68, 0.3)';
  } else {
    toastNotification.style.background = 'linear-gradient(135deg, var(--accent-success), #059669)';
    toastNotification.style.boxShadow = '0 10px 25px rgba(16, 185, 129, 0.3)';
  }

  toastNotification.classList.add('active');
  setTimeout(() => toastNotification.classList.remove('active'), 3000);
}

/**
 * Handles manual poll button click.
 */
async function handleManualPoll() {
  if (!btnManualPoll) return;
  const originalContent = btnManualPoll.innerHTML;
  btnManualPoll.disabled = true;
  btnManualPoll.innerHTML = '🔄 Sincronizzazione...';

  try {
    await QuotesApiManager.triggerManualPoll();
    showToast('Sincronizzazione avviata in background...', 'success');

    // Wait briefly for the background task to fetch items, then reload state
    setTimeout(async () => {
      await loadQuotesFromServer();
      btnManualPoll.disabled = false;
      btnManualPoll.innerHTML = originalContent;
      showToast('Citazioni aggiornate!', 'success');
    }, 3000);
  } catch (error) {
    showToast(`Errore: ${error.message}`, 'danger');
    btnManualPoll.disabled = false;
    btnManualPoll.innerHTML = originalContent;
  }
}

// ═══════════════════════════════════════════════════
//  Window-Exposed Global Actions
// ═══════════════════════════════════════════════════

window.toggleYouTubeExportMenu = function(event) {
  if (event) event.stopPropagation();
  const dropdown = document.getElementById('youtube-export-dropdown');
  if (dropdown) dropdown.classList.toggle('show');
};

window.exportAllYouTubeQuotes = function(format) {
  const dropdown = document.getElementById('youtube-export-dropdown');
  if (dropdown) dropdown.classList.remove('show');

  const youtubeQuotes = quotesState.filter(passesFilters);
  if (youtubeQuotes.length === 0) {
    showToast('Nessuna citazione YouTube disponibile per l\'esportazione.', 'danger');
    return;
  }

  const nonHighQuotes = youtubeQuotes.filter(q => (q.quote_confidence || '').toLowerCase() !== 'high');
  if (nonHighQuotes.length > 0) {
    const confirmDownload = confirm(`⚠️ ATTENZIONE: Ci sono ${nonHighQuotes.length} citazioni con livello di confidenza inferiore ad "Alta" (Media o Bassa).\n\nSi consiglia di verificarle prima di esportarle.\n\nVuoi procedere comunque?`);
    if (!confirmDownload) return;
  }

  if (format === 'readwise') {
    ExportManager.exportYouTubeReadwiseCsv(youtubeQuotes);
    showToast('Download CSV Readwise avviato!', 'success');
  } else {
    ExportManager.exportYouTubeJson(youtubeQuotes);
    showToast('Download JSON avviato!', 'success');
  }
};

window.downloadBookQuotes = function(libraryItemId) {
  const bookQuotes = quotesState.filter(q => q.libraryItemId === libraryItemId);
  if (bookQuotes.length === 0) return;
  ExportManager.exportBookJson(bookQuotes, bookQuotes[0].bookTitle, bookQuotes[0].bookAuthor);
  showToast('Download file JSON avviato!', 'success');
};

window.downloadBookReadwiseCsv = function(libraryItemId) {
  const bookQuotes = quotesState.filter(q => q.libraryItemId === libraryItemId);
  if (bookQuotes.length === 0) return;
  ExportManager.exportBookReadwiseCsv(bookQuotes, bookQuotes[0].bookTitle, bookQuotes[0].bookAuthor);
  showToast('Download CSV Readwise avviato!', 'success');
};

window.toggleEditMode = function(libraryItemId, createdAt, btn) {
  const card = document.getElementById(`quote-card-${libraryItemId}-${createdAt}`);
  if (!card) return;
  const isEditing = card.classList.contains('editing');
  const readView = document.getElementById(`read-view-${libraryItemId}-${createdAt}`);
  const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);

  if (isEditing) {
    const blockquote = readView.querySelector('.quote-blockquote');
    blockquote.textContent = textarea.value;
    card.classList.remove('editing');
    btn.innerHTML = '✏️ Verifica';
  } else {
    const blockquote = readView.querySelector('.quote-blockquote');
    textarea.value = blockquote.textContent;
    card.classList.add('editing');
    btn.innerHTML = '✕ Chiudi';
    textarea.focus();
  }
};

window.saveQuoteUpdate = async function(libraryItemId, createdAt) {
  const textarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
  const selector = document.getElementById(`select-val-${libraryItemId}-${createdAt}`);
  const badge = document.getElementById(`badge-val-${libraryItemId}-${createdAt}`);
  const newQuote = textarea.value.trim();

  selector.value = 'high';
  const newConfidence = 'high';

  try {
    await QuotesApiManager.updateQuote(libraryItemId, createdAt, newQuote, newConfidence);
    const index = quotesState.findIndex(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
    if (index !== -1) {
      quotesState[index].quote = newQuote;
      quotesState[index].quote_confidence = newConfidence;
    }
    badge.textContent = 'high';
    badge.className = 'badge badge-high';
    showToast('Citazione salvata con successo! Confidenza impostata su Alta.', 'success');
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
    updateTabCounters();
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

  const confirmReprocess = confirm("Sei sicuro di voler riestrarre questa citazione?\n\nVerrà scaricata una finestra audio più ampia del 20%, rieseguito Whisper e interrogato l'LLM.");
  if (!confirmReprocess) return;

  card.classList.add('card-loading');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '🔄 Riprocessamento...';

  try {
    const updatedQuote = await QuotesApiManager.reprocessSingleQuote(libraryItemId, createdAt);
    const index = quotesState.findIndex(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
    if (index !== -1) quotesState[index] = updatedQuote;

    const newCard = QuotesUiManager.createQuoteCard(updatedQuote);
    card.parentNode.replaceChild(newCard, card);
    newCard.classList.add('editing');
    const newBtn = newCard.querySelector('.btn-edit-toggle');
    if (newBtn) newBtn.innerHTML = '✕ Chiudi';

    showToast('Citazione riestratta con successo!', 'success');
  } catch (error) {
    showToast(`Errore: ${error.message}`, 'danger');
    card.classList.remove('card-loading');
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
};

// Start
initApp();
