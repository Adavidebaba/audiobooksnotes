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
   * Generates DOM tree for a single Quote Card.
   * @param {Object} quote 
   * @returns {HTMLElement}
   */
  static createQuoteCard(quote) {
    const card = document.createElement('article');
    card.className = 'quote-card';
    card.id = `quote-card-${quote.libraryItemId}-${quote.createdAt}`;
    
    const formattedDate = this.formatDate(quote.createdAt);
    const badgeClass = `badge-${quote.quote_confidence.toLowerCase()}`;
    
    card.innerHTML = `
      <div class="card-header">
        <div class="book-info">
          <h3>${this.escapeHtml(quote.bookTitle)}</h3>
          <p>${this.escapeHtml(quote.bookAuthor)} • Pos: ${this.formatTime(quote.time)}</p>
        </div>
        <div class="card-meta">
          <span class="quote-date">${formattedDate}</span>
          <span class="badge ${badgeClass}" id="badge-val-${quote.libraryItemId}-${quote.createdAt}">${quote.quote_confidence}</span>
        </div>
      </div>
      
      <div class="quote-text-container">
        <textarea class="quote-textarea" id="quote-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Testo della citazione">${this.escapeHtml(quote.quote || '')}</textarea>
      </div>
      
      <div class="card-actions">
        <div class="left-actions">
          <select class="confidence-selector" id="select-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Modifica confidence">
            <option value="high" ${quote.quote_confidence === 'high' ? 'selected' : ''}>High</option>
            <option value="medium" ${quote.quote_confidence === 'medium' ? 'selected' : ''}>Medium</option>
            <option value="low" ${quote.quote_confidence === 'low' ? 'selected' : ''}>Low</option>
          </select>
          
          <button class="btn btn-primary" onclick="saveQuoteUpdate('${quote.libraryItemId}', ${quote.createdAt})">
            Salva
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
        <div style="margin-top: 1.25rem; display: flex; justify-content: flex-end; gap: 0.5rem; border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 1rem;">
          <span class="quote-date" style="align-self: center; margin-right: auto; display: flex; align-items: center; gap: 0.25rem;" title="Porzione audio estratta in totale (pre e post secondi dal bookmark)">
            ⏱️ Finestra: -${quote.audio_window ? quote.audio_window.pre : 30}s / +${quote.audio_window ? quote.audio_window.post : 30}s
          </span>
          <button class="btn btn-secondary" onclick="reprocessSingleQuote('${quote.libraryItemId}', ${quote.createdAt}, this)" style="gap: 0.5rem; font-size: 0.85rem;" title="Riprova ad estrarre la citazione allungando la finestra audio di circa il 20% sia prima che dopo il bookmark">
            🔄 Ripeti Estrazione (+20% Audio)
          </button>
        </div>
      </div>
    `;
    
    return card;
  }
}
