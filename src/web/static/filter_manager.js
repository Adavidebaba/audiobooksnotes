/**
 * FilterManager - Manages active filter state, full-text search matching, and source dropdowns.
 */
export class FilterManager {
  /**
   * Evaluates if a quote passes all active filter and search criteria.
   * @param {Object} quote 
   * @param {'audiobooks' | 'youtube'} activeTab 
   * @param {Object} filterElements 
   * @returns {boolean}
   */
  static passesFilters(quote, activeTab, filterElements) {
    const isAudiobooks = activeTab === 'audiobooks';
    const isQuoteAudiobook = quote.source_type !== 'youtube';

    // 1. Tab category match
    if (isAudiobooks !== isQuoteAudiobook) return false;

    const {
      sourceSelect,
      confidenceSelect,
      dateStartInput,
      dateEndInput,
      searchInput
    } = filterElements;

    const selectedSource = sourceSelect ? sourceSelect.value : 'all';
    const selectedConfidence = confidenceSelect ? confidenceSelect.value : 'all';
    const startDateStr = dateStartInput ? dateStartInput.value : '';
    const endDateStr = dateEndInput ? dateEndInput.value : '';

    // 2. Specific source (book / video) match
    if (selectedSource !== 'all' && quote.libraryItemId !== selectedSource) return false;

    // 3. Confidence level match
    if (selectedConfidence !== 'all' && (quote.quote_confidence || '').toLowerCase() !== selectedConfidence) {
      return false;
    }

    // 4. Date range match
    if (quote.createdAt) {
      const quoteDate = new Date(quote.createdAt).toISOString().split('T')[0];
      if (startDateStr && quoteDate < startDateStr) return false;
      if (endDateStr && quoteDate > endDateStr) return false;
    }

    // 5. Real-Time Search Query Filter (multi-term matching)
    const searchQuery = searchInput ? searchInput.value.trim().toLowerCase() : '';
    if (searchQuery) {
      const quoteText = quote.quote || '';
      const transcriptText = quote.transcript || '';
      const originalText = quote.quote_original || '';
      const titleText = quote.bookTitle || '';
      const authorText = quote.bookAuthor || '';
      const searchPool = `${quoteText} ${transcriptText} ${originalText} ${titleText} ${authorText}`.toLowerCase();

      // Every term in a multi-word search must match
      const terms = searchQuery.split(/\s+/).filter(Boolean);
      const matchesAllTerms = terms.every(term => searchPool.includes(term));
      if (!matchesAllTerms) return false;
    }

    return true;
  }

  /**
   * Populates the source selection dropdown based on current tab and available items.
   * @param {Array} quotesState 
   * @param {'audiobooks' | 'youtube'} activeTab 
   * @param {HTMLSelectElement} selectElement 
   */
  static populateSourceDropdown(quotesState, activeTab, selectElement) {
    if (!selectElement) return;

    const currentSelection = selectElement.value;
    const isAudiobooks = activeTab === 'audiobooks';
    const filteredPool = quotesState.filter(q => isAudiobooks ? q.source_type !== 'youtube' : q.source_type === 'youtube');

    const sourcesMap = new Map();
    filteredPool.forEach(q => {
      sourcesMap.set(q.libraryItemId, q.bookTitle);
    });

    selectElement.innerHTML = isAudiobooks
      ? '<option value="all">Tutti i libri</option>'
      : '<option value="all">Tutti i video</option>';

    sourcesMap.forEach((title, id) => {
      const option = document.createElement('option');
      option.value = id;
      option.textContent = title;
      selectElement.appendChild(option);
    });

    if (sourcesMap.has(currentSelection)) {
      selectElement.value = currentSelection;
    } else {
      selectElement.value = 'all';
    }
  }
}
