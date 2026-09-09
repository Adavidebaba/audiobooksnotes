/**
 * AudiobookNotes Dashboard - Prompts Configuration
 * Handles fetching, editing, saving and resetting LLM prompts and model settings.
 */

class PromptsApiManager {
  /** Handles all network interactions with the /api/prompts endpoints. */

  async fetchPrompts() {
    const response = await fetch('/api/prompts');
    if (!response.ok) {
      throw new Error(`Errore durante il recupero dei prompt: ${response.statusText}`);
    }
    return await response.json();
  }

  async savePrompts(payload) {
    const response = await fetch('/api/prompts', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`Errore durante il salvataggio dei prompt: ${response.statusText}`);
    }
    return await response.json();
  }

  async resetPrompts(targetKey = null) {
    const response = await fetch('/api/prompts/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_key: targetKey })
    });
    if (!response.ok) {
      throw new Error(`Errore durante il ripristino: ${response.statusText}`);
    }
    return await response.json();
  }
}


class PromptsViewModel {
  /** Manages UI bindings, counters, validation, and user feedback. */

  constructor() {
    this.api = new PromptsApiManager();
    this.data = null;
    this.resetTargetKey = null;

    // DOM Elements
    this.modelInput = document.getElementById('input-model-name');
    this.audiobooksTextarea = document.getElementById('prompt-audiobooks');
    this.ytSingleTextarea = document.getElementById('prompt-yt-single');
    this.ytFullTextarea = document.getElementById('prompt-yt-full');

    this.charCountAudiobooks = document.getElementById('char-count-audiobooks');
    this.charCountYtSingle = document.getElementById('char-count-yt-single');
    this.charCountYtFull = document.getElementById('char-count-yt-full');

    this.btnSaveAll = document.getElementById('btn-save-all');
    this.btnSaveAllTop = document.getElementById('btn-save-all-top');
    this.btnResetAll = document.getElementById('btn-reset-all');
    this.resetModal = document.getElementById('reset-modal');
    this.resetModalDesc = document.getElementById('reset-modal-desc');
    this.btnModalConfirm = document.getElementById('btn-modal-confirm');
    this.btnModalCancel = document.getElementById('btn-modal-cancel');
    this.toastElement = document.getElementById('toast');
  }

  async init() {
    this._bindEvents();
    await this.loadData();
  }

  _bindEvents() {
    // Save buttons
    if (this.btnSaveAll) this.btnSaveAll.addEventListener('click', () => this.handleSave());
    if (this.btnSaveAllTop) this.btnSaveAllTop.addEventListener('click', () => this.handleSave());

    // Reset single prompts
    this._bindResetButton('btn-reset-model', 'model_name', 'il modello LLM');
    this._bindResetButton('btn-reset-audiobooks', 'audiobooks_system_prompt', 'il prompt Audiolibri');
    this._bindResetButton('btn-reset-yt-single', 'youtube_system_prompt', 'il prompt YouTube Singolo');
    this._bindResetButton('btn-reset-yt-full', 'youtube_full_video_system_prompt', 'il prompt YouTube Intero Video');

    // Reset all
    if (this.btnResetAll) {
      this.btnResetAll.addEventListener('click', () => {
        this.openResetModal(null, 'TUTTI i prompt e il modello LLM ai valori predefiniti di fabbrica');
      });
    }

    // Modal buttons
    if (this.btnModalCancel) this.btnModalCancel.addEventListener('click', () => this.closeResetModal());
    if (this.btnModalConfirm) this.btnModalConfirm.addEventListener('click', () => this.executeReset());
    if (this.resetModal) {
      this.resetModal.addEventListener('click', (e) => {
        if (e.target === this.resetModal) this.closeResetModal();
      });
    }

    // Presets
    document.querySelectorAll('.preset-pill').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const model = e.target.getAttribute('data-model');
        if (this.modelInput && model) {
          this.modelInput.value = model;
          this.showToast(`Modello impostato a: ${model}`);
        }
      });
    });

    // Character counters & auto-grow
    this._bindTextareaCounter(this.audiobooksTextarea, this.charCountAudiobooks);
    this._bindTextareaCounter(this.ytSingleTextarea, this.charCountYtSingle);
    this._bindTextareaCounter(this.ytFullTextarea, this.charCountYtFull);
  }

  _bindResetButton(buttonId, targetKey, label) {
    const btn = document.getElementById(buttonId);
    if (btn) {
      btn.addEventListener('click', () => this.openResetModal(targetKey, label));
    }
  }

  _bindTextareaCounter(textarea, counterElem) {
    if (!textarea || !counterElem) return;
    const update = () => {
      const len = textarea.value.length;
      counterElem.textContent = `${len.toLocaleString('it-IT')} caratteri (~${Math.round(len / 4)} token)`;
    };
    textarea.addEventListener('input', update);
  }

  async loadData() {
    try {
      this.data = await this.api.fetchPrompts();
      this.populateFields(this.data.current);
    } catch (error) {
      this.showToast(error.message, true);
    }
  }

  populateFields(current) {
    if (!current) return;
    if (this.modelInput) this.modelInput.value = current.model_name || '';
    if (this.audiobooksTextarea) this.audiobooksTextarea.value = current.audiobooks_system_prompt || '';
    if (this.ytSingleTextarea) this.ytSingleTextarea.value = current.youtube_system_prompt || '';
    if (this.ytFullTextarea) this.ytFullTextarea.value = current.youtube_full_video_system_prompt || '';

    this._triggerCounters();
  }

  _triggerCounters() {
    [this.audiobooksTextarea, this.ytSingleTextarea, this.ytFullTextarea].forEach(t => {
      if (t) t.dispatchEvent(new Event('input'));
    });
  }

  async handleSave() {
    const payload = {
      model_name: this.modelInput ? this.modelInput.value.trim() : undefined,
      audiobooks_system_prompt: this.audiobooksTextarea ? this.audiobooksTextarea.value.trim() : undefined,
      youtube_system_prompt: this.ytSingleTextarea ? this.ytSingleTextarea.value.trim() : undefined,
      youtube_full_video_system_prompt: this.ytFullTextarea ? this.ytFullTextarea.value.trim() : undefined,
    };

    try {
      const result = await this.api.savePrompts(payload);
      this.showToast(result.message || 'Prompt salvati con successo!');
      await this.loadData();
    } catch (error) {
      this.showToast(error.message, true);
    }
  }

  openResetModal(targetKey, description) {
    this.resetTargetKey = targetKey;
    if (this.resetModalDesc) {
      this.resetModalDesc.textContent = `Sei sicuro di voler ripristinare ${description}? Le modifiche correnti non salvate andranno perse.`;
    }
    if (this.resetModal) this.resetModal.classList.add('show');
  }

  closeResetModal() {
    if (this.resetModal) this.resetModal.classList.remove('show');
    this.resetTargetKey = null;
  }

  async executeReset() {
    try {
      const result = await this.api.resetPrompts(this.resetTargetKey);
      this.closeResetModal();
      this.showToast(result.message || 'Ripristino completato!');
      await this.loadData();
    } catch (error) {
      this.showToast(error.message, true);
    }
  }

  showToast(message, isError = false) {
    if (!this.toastElement) return;
    this.toastElement.textContent = message;
    this.toastElement.style.borderColor = isError ? 'var(--accent-danger)' : 'var(--accent-success)';
    this.toastElement.classList.add('show');
    setTimeout(() => {
      this.toastElement.classList.remove('show');
    }, 3500);
  }
}

// Instantiate on DOM load
document.addEventListener('DOMContentLoaded', () => {
  const viewModel = new PromptsViewModel();
  viewModel.init();
});
