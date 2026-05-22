/**
 * QuotesUiManager - Handles all DOM elements generation, text formatting, and HTML escaping.
 */
export class QuotesUiManager {
  /**
   * Helper to translate epoch to beautiful formatted date string.
   * @param {number} epoch 
   * @returns {string}
   */
  static formatDate(epoch) {
    if (!epoch) return 'Data sconosciuta';
    const date = new Date(epoch);
    return date.toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Utility to parse audio window times (seconds) to human mm:ss.
   * @param {number} secs 
   * @returns {string}
   */
  static formatTime(secs) {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  /**
   * Utility to format seconds into a readable hh:mm:ss or mm:ss label.
   * @param {number} secs 
   * @returns {string}
   */
  static formatTimeLabel(secs) {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (h > 0) {
      return `${h}h ${m}m ${s < 10 ? '0' : ''}${s}s`;
    }
    return `${m}m ${s < 10 ? '0' : ''}${s}s`;
  }

  /**
   * Utility to escape raw HTML text and guard against XSS injection.
   * @param {string} text 
   * @returns {string}
   */
  static escapeHtml(text) {
    if (!text) return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Creates a complete book section with header and quote cards.
   * @param {string} bookTitle 
   * @param {string} bookAuthor 
   * @param {Array} quotes - Array of quote objects for this book
   * @returns {HTMLElement}
   */
  static createBookSection(bookTitle, bookAuthor, quotes) {
    const section = document.createElement('section');
    section.className = 'book-section';

    const highCount = quotes.filter(q => q.quote_confidence === 'high').length;
    const mediumCount = quotes.filter(q => q.quote_confidence === 'medium').length;
    const lowCount = quotes.filter(q => q.quote_confidence === 'low').length;

    const header = document.createElement('div');
    header.className = 'book-section-header';
    header.innerHTML = `
      <div class="book-section-info">
        <h2 class="book-section-title">${this.escapeHtml(bookTitle)}</h2>
        <p class="book-section-author">${this.escapeHtml(bookAuthor)}</p>
      </div>
      <div class="book-section-stats">
        <span class="stat-pill">${quotes.length} citazion${quotes.length === 1 ? 'e' : 'i'}</span>
        ${highCount > 0 ? `<span class="stat-pill stat-high">${highCount} high</span>` : ''}
        ${mediumCount > 0 ? `<span class="stat-pill stat-medium">${mediumCount} medium</span>` : ''}
        ${lowCount > 0 ? `<span class="stat-pill stat-low">${lowCount} low</span>` : ''}
      </div>
    `;
    section.appendChild(header);

    const quotesList = document.createElement('div');
    quotesList.className = 'book-quotes-list';
    quotes.forEach(quote => {
      quotesList.appendChild(this.createQuoteCard(quote));
    });
    section.appendChild(quotesList);
    return section;
  }

  /**
   * Generates a quote card with read-mode by default (no textarea, no buttons).
   * Edit mode is revealed on user click via toggleEditMode().
   * @param {Object} quote 
   * @returns {HTMLElement}
   */
  static createQuoteCard(quote) {
    const card = document.createElement('article');
    card.className = 'quote-card';
    card.id = `quote-card-${quote.libraryItemId}-${quote.createdAt}`;
    
    const badgeClass = `badge-${quote.quote_confidence.toLowerCase()}`;
    const quoteText = this.escapeHtml(quote.quote || '');
    
    card.innerHTML = `
      <div class="card-header">
        <div class="card-position">
          <span class="position-marker">⏱️ ${this.formatTimeLabel(quote.time)}</span>
          <span class="badge ${badgeClass}" id="badge-val-${quote.libraryItemId}-${quote.createdAt}">${quote.quote_confidence}</span>
        </div>
        <button class="btn-edit-toggle" onclick="toggleEditMode('${quote.libraryItemId}', ${quote.createdAt}, this)" title="Modifica citazione">
          ✏️
        </button>
      </div>
      
      <!-- READ MODE: beautiful readable text -->
      <div class="quote-read-view" id="read-view-${quote.libraryItemId}-${quote.createdAt}">
        <blockquote class="quote-blockquote">${quoteText}</blockquote>
      </div>
      
      <!-- EDIT MODE: hidden by default -->
      <div class="quote-edit-view" id="edit-view-${quote.libraryItemId}-${quote.createdAt}">
        <textarea class="quote-textarea" id="quote-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Testo della citazione">${quoteText}</textarea>
        
        <div class="card-actions">
          <div class="left-actions">
            <select class="confidence-selector" id="select-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Modifica confidence">
              <option value="high" ${quote.quote_confidence === 'high' ? 'selected' : ''}>High</option>
              <option value="medium" ${quote.quote_confidence === 'medium' ? 'selected' : ''}>Medium</option>
              <option value="low" ${quote.quote_confidence === 'low' ? 'selected' : ''}>Low</option>
            </select>
            
            <button class="btn btn-primary" onclick="saveQuoteUpdate('${quote.libraryItemId}', ${quote.createdAt})">
              💾 Salva
            </button>
            
            <button class="btn btn-secondary" onclick="toggleDetails('${quote.libraryItemId}', ${quote.createdAt}, this)">
              Espandi dettagli
            </button>
          </div>
          
          <button class="btn btn-danger" onclick="confirmDeleteQuote('${quote.libraryItemId}', ${quote.createdAt})">
            Elimina
          </button>
        </div>
        
        <div class="expandable-details" id="details-${quote.libraryItemId}-${quote.createdAt}">
          <div class="details-grid">
            <div class="detail-block">
              <h4>Trascrizione Originale</h4>
              <p>${this.escapeHtml(quote.transcript || 'Nessuna trascrizione estratta.')}</p>
            </div>
            <div class="detail-block">
              <h4>Ragionamento Estrattivo LLM</h4>
              <p>${this.escapeHtml(quote.quote_reasoning || 'Nessun ragionamento fornito.')}</p>
            </div>
          </div>
          <div class="details-footer">
            <span class="quote-date" title="Porzione audio estratta">
              ⏱️ Finestra: -${quote.audio_window ? quote.audio_window.pre : 30}s / +${quote.audio_window ? quote.audio_window.post : 30}s
            </span>
            <button class="btn btn-secondary" onclick="reprocessSingleQuote('${quote.libraryItemId}', ${quote.createdAt}, this)" title="Riprova ad estrarre la citazione allungando la finestra audio di circa il 20%">
              🔄 Ripeti Estrazione (+20% Audio)
            </button>
          </div>
        </div>
      </div>
    `;
    
    return card;
  }
}
