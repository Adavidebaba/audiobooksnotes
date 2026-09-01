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
   * Utility to format seconds into mm:ss.
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
   * Creates an Audiobook section with book header, stats, and quote cards.
   * @param {string} bookTitle 
   * @param {string} bookAuthor 
   * @param {Array} quotes 
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
        <p class="book-section-author">di ${this.escapeHtml(bookAuthor)}</p>
      </div>
      <div class="book-section-actions">
        <button class="btn-download-book" onclick="window.downloadBookQuotes('${quotes[0].libraryItemId}')" title="Scarica citazioni in formato JSON">
          📥 Scarica JSON
        </button>
        <button class="btn-download-book btn-download-readwise" onclick="window.downloadBookReadwiseCsv('${quotes[0].libraryItemId}')" title="Scarica citazioni in formato Readwise CSV">
          📥 Scarica CSV Readwise
        </button>
        <div class="book-section-stats">
          <span class="stat-pill">${quotes.length} ${quotes.length === 1 ? 'citazione' : 'citazioni'}</span>
          ${highCount > 0 ? `<span class="stat-pill stat-high">${highCount} high</span>` : ''}
          ${mediumCount > 0 ? `<span class="stat-pill stat-medium">${mediumCount} medium</span>` : ''}
          ${lowCount > 0 ? `<span class="stat-pill stat-low">${lowCount} low</span>` : ''}
        </div>
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
   * Creates the unified feed for YouTube quotes with top toolbar and continuous cards.
   * @param {Array} quotes 
   * @returns {HTMLElement}
   */
  static createYouTubeFeed(quotes) {
    const container = document.createElement('div');
    container.className = 'youtube-stream-container';

    // Toolbar with single export button and stats
    const toolbar = document.createElement('div');
    toolbar.className = 'youtube-stream-toolbar';
    toolbar.innerHTML = `
      <div class="youtube-stream-info">
        <span class="youtube-stream-title">🎬 Flusso Citazioni YouTube</span>
        <span class="stat-pill">${quotes.length} ${quotes.length === 1 ? 'citazione' : 'citazioni'}</span>
      </div>
      <div class="youtube-stream-actions">
        <div class="export-menu-container">
          <button class="btn-export-primary" id="btn-export-youtube-toggle" onclick="window.toggleYouTubeExportMenu(event)">
            📥 Esporta Citazioni YouTube ▾
          </button>
          <div class="export-dropdown-menu" id="youtube-export-dropdown">
            <button class="export-menu-item" onclick="window.exportAllYouTubeQuotes('readwise')">
              📊 Scarica CSV Readwise
            </button>
            <button class="export-menu-item" onclick="window.exportAllYouTubeQuotes('json')">
              📄 Scarica File JSON
            </button>
          </div>
        </div>
      </div>
    `;
    container.appendChild(toolbar);

    // Continuous Chronological Feed
    const feed = document.createElement('div');
    feed.className = 'youtube-stream-feed';
    quotes.forEach(quote => {
      feed.appendChild(this.createYouTubeCard(quote));
    });
    container.appendChild(feed);

    return container;
  }

  /**
   * Generates an individual YouTube quote card optimized for chronological feed.
   * @param {Object} quote 
   * @returns {HTMLElement}
   */
  static createYouTubeCard(quote) {
    const card = document.createElement('article');
    card.className = 'youtube-card quote-card';
    card.id = `quote-card-${quote.libraryItemId}-${quote.createdAt}`;

    const badgeClass = `badge-${(quote.quote_confidence || 'low').toLowerCase()}`;
    const quoteText = this.escapeHtml(quote.quote || '');
    const videoUrl = quote.video_url || '#';
    const videoTitle = this.escapeHtml(quote.bookTitle || 'Video YouTube');
    const channelName = this.escapeHtml(quote.bookAuthor || 'Canale YouTube');
    const isFullVideo = (quote.time === 0 || quote.time === undefined || quote.time === null || quote.time < 0);
    const timeLabel = isFullVideo ? '🎬 Intero Video' : `▶️ ${this.formatTimeLabel(quote.time || 0)}`;
    const timeTooltip = isFullVideo ? 'Apri il video su YouTube' : 'Apri il video su YouTube a questo minuto';
    const dateFormatted = this.formatDate(quote.createdAt);

    card.innerHTML = `
      <div class="youtube-card-header">
        <div class="youtube-meta-info">
          <span class="youtube-channel-tag">📺 ${channelName} • 📅 ${dateFormatted}</span>
          <h3 class="youtube-video-title">${videoTitle}</h3>
        </div>
        <div class="youtube-header-badges">
          <a href="${this.escapeHtml(videoUrl)}" target="_blank" rel="noopener" class="youtube-time-link" title="${timeTooltip}">
            ${timeLabel}
          </a>
          <span class="badge ${badgeClass}" id="badge-val-${quote.libraryItemId}-${quote.createdAt}">${quote.quote_confidence || 'low'}</span>
          <button class="btn-edit-toggle" onclick="window.toggleEditMode('${quote.libraryItemId}', ${quote.createdAt}, this)" title="Verifica o modifica la citazione">
            ✏️ Verifica
          </button>
        </div>
      </div>

      <!-- READ MODE -->
      <div class="quote-read-view" id="read-view-${quote.libraryItemId}-${quote.createdAt}">
        <blockquote class="quote-blockquote quote-blockquote-youtube">${quoteText}</blockquote>
      </div>

      <!-- EDIT MODE -->
      <div class="quote-edit-view" id="edit-view-${quote.libraryItemId}-${quote.createdAt}">
        <textarea class="quote-textarea" id="quote-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Testo citazione">${quoteText}</textarea>
        
        <div class="card-actions">
          <div class="left-actions">
            <select class="confidence-selector" id="select-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Modifica confidenza">
              <option value="high" ${quote.quote_confidence === 'high' ? 'selected' : ''}>Alta</option>
              <option value="medium" ${quote.quote_confidence === 'medium' ? 'selected' : ''}>Media</option>
              <option value="low" ${quote.quote_confidence === 'low' ? 'selected' : ''}>Bassa</option>
            </select>
            
            <button class="btn btn-primary" onclick="window.saveQuoteUpdate('${quote.libraryItemId}', ${quote.createdAt})">
              💾 Salva
            </button>
          </div>
          
          <button class="btn btn-danger" onclick="window.confirmDeleteQuote('${quote.libraryItemId}', ${quote.createdAt})">
            Elimina
          </button>
        </div>
        
        <div class="details-grid" style="margin-top: 1.25rem;">
          <div class="detail-block">
            <h4>Trascrizione Originale</h4>
            <p>${this.escapeHtml(quote.transcript || 'Nessuna trascrizione estratta.')}</p>
          </div>
          <div class="detail-block">
            <h4>Ragionamento LLM</h4>
            <p>${this.escapeHtml(quote.quote_reasoning || 'Nessuna motivazione fornita.')}</p>
          </div>
        </div>
      </div>
    `;

    return card;
  }

  /**
   * Generates a standard audiobook quote card with read/edit dual view.
   * @param {Object} quote 
   * @returns {HTMLElement}
   */
  static createQuoteCard(quote) {
    const card = document.createElement('article');
    card.className = 'quote-card';
    card.id = `quote-card-${quote.libraryItemId}-${quote.createdAt}`;

    const badgeClass = `badge-${(quote.quote_confidence || 'low').toLowerCase()}`;
    const quoteText = this.escapeHtml(quote.quote || '');
    const timeLabel = this.formatTimeLabel(quote.time || 0);

    card.innerHTML = `
      <div class="card-header">
        <div class="card-position">
          <span class="position-marker">⏱️ ${timeLabel}</span>
          <span class="badge ${badgeClass}" id="badge-val-${quote.libraryItemId}-${quote.createdAt}">${quote.quote_confidence}</span>
        </div>
        <button class="btn-edit-toggle" onclick="window.toggleEditMode('${quote.libraryItemId}', ${quote.createdAt}, this)" title="Verifica o modifica la citazione">
          ✏️ Verifica
        </button>
      </div>
      
      <!-- READ MODE -->
      <div class="quote-read-view" id="read-view-${quote.libraryItemId}-${quote.createdAt}">
        <blockquote class="quote-blockquote">${quoteText}</blockquote>
      </div>
      
      <!-- EDIT MODE -->
      <div class="quote-edit-view" id="edit-view-${quote.libraryItemId}-${quote.createdAt}">
        <textarea class="quote-textarea" id="quote-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Testo citazione">${quoteText}</textarea>
        
        <div class="card-actions">
          <div class="left-actions">
            <select class="confidence-selector" id="select-val-${quote.libraryItemId}-${quote.createdAt}" aria-label="Modifica confidenza">
              <option value="high" ${quote.quote_confidence === 'high' ? 'selected' : ''}>Alta</option>
              <option value="medium" ${quote.quote_confidence === 'medium' ? 'selected' : ''}>Media</option>
              <option value="low" ${quote.quote_confidence === 'low' ? 'selected' : ''}>Bassa</option>
            </select>
            
            <button class="btn btn-primary" onclick="window.saveQuoteUpdate('${quote.libraryItemId}', ${quote.createdAt})">
              💾 Salva
            </button>
          </div>
          
          <button class="btn btn-danger" onclick="window.confirmDeleteQuote('${quote.libraryItemId}', ${quote.createdAt})">
            Elimina
          </button>
        </div>
        
        <div class="details-grid" style="margin-top: 1.25rem;">
          <div class="detail-block">
            <h4>Trascrizione Originale</h4>
            <p>${this.escapeHtml(quote.transcript || 'Nessuna trascrizione estratta.')}</p>
          </div>
          <div class="detail-block">
            <h4>Ragionamento LLM</h4>
            <p>${this.escapeHtml(quote.quote_reasoning || 'Nessuna motivazione fornita.')}</p>
          </div>
        </div>
        <div class="details-footer">
          <span class="quote-date" title="Porzione audio estratta">
            ⏱️ Finestra: -${quote.audio_window ? quote.audio_window.pre : 30}s / +${quote.audio_window ? quote.audio_window.post : 30}s
          </span>
          <button class="btn btn-secondary" onclick="window.reprocessSingleQuote('${quote.libraryItemId}', ${quote.createdAt}, this)" title="Riprova l'estrazione espandendo la finestra audio del 20%">
            🔄 Riprocessa (+20% Audio)
          </button>
        </div>
      </div>
    `;

    return card;
  }
}
