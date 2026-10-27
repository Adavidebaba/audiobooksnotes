/**
 * QuotesApiManager - Responsible for all HTTP communications with the backend API.
 */
export class QuotesApiManager {
  /**
   * Fetches all quotes from the backend database.
   * @returns {Promise<Array>}
   */
  static async fetchQuotes() {
    const response = await fetch('/api/quotes');
    if (!response.ok) throw new Error('Impossibile caricare le citazioni dal server.');
    return await response.json();
  }

  /**
   * Updates an existing quote's text and confidence level.
   * @param {string} libraryItemId 
   * @param {number} createdAt 
   * @param {string} quote 
   * @param {string} confidence 
   */
  static async updateQuote(libraryItemId, createdAt, quote, confidence) {
    const response = await fetch('/api/quotes', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        libraryItemId,
        createdAt,
        quote,
        quote_confidence: confidence
      })
    });
    if (!response.ok) throw new Error("Errore durante il salvataggio sul server.");
    return await response.json();
  }

  /**
   * Deletes a specific quote from the book database.
   * @param {string} libraryItemId 
   * @param {number} createdAt 
   */
  static async deleteQuote(libraryItemId, createdAt) {
    const response = await fetch('/api/quotes', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ libraryItemId, createdAt })
    });
    if (!response.ok) throw new Error("Impossibile eliminare la citazione sul server.");
    return await response.json();
  }

  /**
   * Triggers an immediate manual polling check for new Audiobookshelf bookmarks and YouTube links.
   */
  static async triggerManualPoll() {
    const response = await fetch('/api/poll', { method: 'POST' });
    if (!response.ok) throw new Error("Impossibile avviare il controllo manuale.");
    return await response.json();
  }

  /**
   * Triggers a complete database regeneration from ABS bookmarks.
   */
  static async triggerDatabaseReprocess() {
    const response = await fetch('/api/reprocess', { method: 'POST' });
    if (!response.ok) throw new Error("Impossibile avviare il riprocessamento totale.");
    return await response.json();
  }

  /**
   * Triggers reprocessing for a single quote, extending the audio window by 20%.
   * @param {string} libraryItemId 
   * @param {number} createdAt 
   */
  static async reprocessSingleQuote(libraryItemId, createdAt) {
    const response = await fetch('/api/quotes/reprocess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ libraryItemId, createdAt })
    });
    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.detail || "Errore durante la rielaborazione sincrona.");
    }
    return await response.json();
  }

  /**
   * Re-runs only the LLM extraction for an existing quote using the current active prompt.
   * @param {string} libraryItemId 
   * @param {number} createdAt 
   */
  static async reExtractQuoteLlm(libraryItemId, createdAt) {
    const response = await fetch('/api/quotes/re-extract-llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ libraryItemId, createdAt })
    });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "Errore durante la ri-estrazione con LLM.");
    }
    return await response.json();
  }

  /**
   * Checks Readwise configuration and authentication status.
   * @returns {Promise<{configured: boolean, valid: boolean}>}
   */
  static async getReadwiseStatus() {
    const response = await fetch('/api/readwise/status');
    if (!response.ok) throw new Error('Impossibile verificare lo stato di Readwise.');
    return await response.json();
  }

  /**
   * Triggers a batch synchronization of all unsynced quotes to Readwise.
   * @returns {Promise<Object>}
   */
  static async syncAllReadwise() {
    const response = await fetch('/api/readwise/sync', { method: 'POST' });
    if (!response.ok) throw new Error('Errore durante la sincronizzazione con Readwise.');
    return await response.json();
  }

  /**
   * Syncs a single quote to Readwise.
   * @param {string} libraryItemId
   * @param {number} createdAt
   * @returns {Promise<Object>}
   */
  static async syncSingleReadwise(libraryItemId, createdAt) {
    const response = await fetch('/api/readwise/sync-single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ libraryItemId, createdAt })
    });
    if (!response.ok) throw new Error('Errore durante la sincronizzazione su Readwise.');
    return await response.json();
  }
}

