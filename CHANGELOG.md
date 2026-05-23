# Changelog

Tutti i cambiamenti significativi a questo progetto saranno documentati in questo file.

## [2.0.0] - 2026-05-24

### Aggiunto
- **Esportazione Duale per Libro**:
  - Aggiunto il pulsante **"Scarica JSON"** per scaricare le citazioni strutturate per singolo libro.
  - Aggiunto il pulsante **"Scarica CSV Readwise"** conforme al 100% con i requisiti di importazione di Readwise (esclusione di URL/Note, location in secondi interi, date formattate in UTC e BOM UTF-8).
- **Nuova Pagina Istruzioni**: Creata una guida completa in inglese (`instructions.html`) con la spiegazione dei badge, del flusso e del sistema di esportazione.

### Modificato
- **Redesign Grafico Dashboard**:
  - Raggruppamento delle citazioni per libro in sezioni dedicate a timeline, eliminando la ripetizione di titolo e autore su ogni card.
  - Citazioni ordinate per posizione temporale crescente (`time asc`) invece di data di creazione (`createdAt desc`).
  - Rimosso lo stile corsivo predefinito dalle citazioni per migliorarne la leggibilità.
- **Fusione Dettagli e Modifica ("Verify")**:
  - Sostituito il vecchio tasto "Espandi dettagli" con un pulsante minimale ed elegante **"Verify"** che apre contestualmente sia il pannello di modifica che la griglia dei dettagli (trascrizione, ragionamento AI).
- **Traduzione in Inglese**: Localizzazione completa dell'interfaccia web (menu, filtri, dialoghi di conferma, modal di eliminazione e notifiche Toast).
- **Spostamento Danger Zone**: Trasferito il pulsante **"Regenerate Database"** dalla homepage al fondo della pagina delle istruzioni (Danger Zone) per evitare clic accidentali.
- **Configurazione .env.example**: Allineato il file di esempio alle reali variabili d'ambiente di OpenRouter utilizzate dall'app.

## [1.0.0] - 2026-05-22

### Aggiunto
- **Integrazione Audiobookshelf**: Client per connettersi ad un server Audiobookshelf, scaricare metadati ed elaborare i capitoli degli audiolibri.
- **Trascrizione Audio (STT)**: Elaborazione e trascrizione dei file audio estratti usando il modello `mistralai/voxtral-mini-transcribe` via OpenRouter.
- **Analisi e Sintesi (LLM)**: Generazione automatica di appunti strutturati, riassunti e concetti chiave dai capitoli trascritti utilizzando `openrouter/auto`.
- **Gestione dello Stato**: Sistema di persistenza locale per tracciare lo stato di avanzamento dell'ascolto e dell'elaborazione per ciascun libro.
- **Dockerizzazione**: Configurazione di Docker e `docker-compose.yml` con uno script helper (`restart_docker.command`) per avviare, arrestare e ricostruire facilmente l'applicazione su macOS.
- **Configurazione Dinamica**: Gestione delle chiavi API e dei parametri di connessione tramite variabili d'ambiente (`.env`).
