import { QuotesApiManager } from './api.js?v=3.6.0';

/**
 * ReadwiseSyncManager - Coordinates Readwise synchronization logic and visual feedback.
 */
export class ReadwiseSyncManager {
  /**
   * Triggers batch sync of all unsynced quotes to Readwise.
   * @param {HTMLElement} btn 
   * @param {Function} showToast 
   * @param {Function} onReloadQuotes 
   */
  static async handleBatchSync(btn, showToast, onReloadQuotes) {
    if (!btn) return;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ Invio a Readwise...';

    try {
      const result = await QuotesApiManager.syncAllReadwise();
      if (result.status === 'success') {
        showToast(result.message, 'success');
        if (onReloadQuotes) {
          await onReloadQuotes();
        }
      } else {
        showToast(result.message || 'Errore nella sincronizzazione.', 'danger');
      }
    } catch (err) {
      showToast(`Errore: ${err.message}`, 'danger');
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }

  /**
   * Syncs a single quote to Readwise and updates UI badge.
   * @param {string} libraryItemId 
   * @param {number} createdAt 
   * @param {HTMLElement} btn 
   * @param {Array} quotesState 
   * @param {Function} showToast 
   */
  static async handleSingleQuoteSync(libraryItemId, createdAt, btn, quotesState, showToast) {
    if (!btn) return;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ Sync...';

    try {
      const result = await QuotesApiManager.syncSingleReadwise(libraryItemId, createdAt);
      if (result.status === 'success') {
        const quoteObj = quotesState.find(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
        if (quoteObj) {
          quoteObj.readwise_synced = true;
          quoteObj.readwise_synced_at = new Date().toISOString();
        }
        // Update badge if present
        const badgeElem = document.getElementById(`readwise-badge-${libraryItemId}-${createdAt}`);
        if (badgeElem) {
          badgeElem.style.display = 'inline-block';
        }
        showToast(result.message, 'success');
      } else {
        showToast(result.message || 'Errore durante la sincronizzazione.', 'danger');
      }
    } catch (err) {
      showToast(`Errore: ${err.message}`, 'danger');
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
}
