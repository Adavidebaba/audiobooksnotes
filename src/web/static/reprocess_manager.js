/**
 * ReprocessManager - Handles audio re-extraction and instant LLM re-prompting for quotes.
 */
import { QuotesApiManager } from './api.js?v=2.4.0';
import { QuotesUiManager } from './ui.js?v=2.4.0';

export class ReprocessManager {
  /**
   * Re-extracts audio window (+20%), re-transcribes, and updates the quote.
   */
  static async handleAudioReprocess(libraryItemId, createdAt, btn, quotesState, updateTabCounters) {
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

      if (updateTabCounters) updateTabCounters();
      return { success: true, message: 'Citazione riestratta con successo!' };
    } catch (error) {
      card.classList.remove('card-loading');
      btn.disabled = false;
      btn.innerHTML = originalText;
      return { success: false, message: `Errore: ${error.message}` };
    }
  }

  /**
   * Re-evaluates existing transcript using current active LLM prompt without downloading audio.
   */
  static async handleLlmReprompt(libraryItemId, createdAt, btn, quotesState) {
    const card = document.getElementById(`quote-card-${libraryItemId}-${createdAt}`);
    if (!card) return;

    const banner = document.getElementById(`reprompt-banner-${libraryItemId}-${createdAt}`);
    const quoteTextarea = document.getElementById(`quote-val-${libraryItemId}-${createdAt}`);
    const confidenceSelect = document.getElementById(`select-val-${libraryItemId}-${createdAt}`);
    const reasoningElem = document.getElementById(`reasoning-val-${libraryItemId}-${createdAt}`);
    const badgeElem = document.getElementById(`badge-val-${libraryItemId}-${createdAt}`);

    const originalBtnText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ Elaborazione...';

    if (banner) {
      banner.className = 'reprompt-status-banner';
      banner.innerHTML = '<span>⏳ <strong>Elaborazione LLM in corso con il prompt attivo...</strong> Attendere, non ricaricare la pagina.</span>';
      banner.style.display = 'flex';
    }

    try {
      const updated = await QuotesApiManager.reExtractQuoteLlm(libraryItemId, createdAt);
      const index = quotesState.findIndex(q => q.libraryItemId === libraryItemId && q.createdAt === createdAt);
      if (index !== -1) quotesState[index] = { ...quotesState[index], ...updated };

      if (quoteTextarea) quoteTextarea.value = updated.quote || '';
      if (confidenceSelect) confidenceSelect.value = updated.quote_confidence || 'low';
      if (reasoningElem) reasoningElem.textContent = updated.quote_reasoning || 'Nessuna motivazione fornita.';
      if (badgeElem) {
        badgeElem.textContent = updated.quote_confidence;
        badgeElem.className = `badge badge-${(updated.quote_confidence || 'low').toLowerCase()}`;
      }

      if (banner) {
        banner.className = 'reprompt-status-banner success';
        banner.innerHTML = '<span>✅ <strong>Nuova citazione estratta con successo!</strong> Puoi modificarla o salvarla.</span>';
        setTimeout(() => { if (banner) banner.style.display = 'none'; }, 5000);
      }
      return { success: true, message: 'Nuova citazione generata con successo!' };
    } catch (error) {
      if (banner) {
        banner.className = 'reprompt-status-banner error';
        banner.innerHTML = `<span>❌ <strong>Errore LLM:</strong> ${error.message}</span>`;
      }
      return { success: false, message: `Errore: ${error.message}` };
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalBtnText;
    }
  }
}
