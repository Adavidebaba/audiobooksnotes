# Changelog

Tutti i cambiamenti significativi a questo progetto saranno documentati in questo file.

## [3.3.0] - 2026-09-01

### Aggiunto
- **Sintesi ed Estrazione Insight Intero Video YouTube**: Supporto per link YouTube senza timestamp o con timestamp 0, con download integrale dei sottotitoli (`get_full_transcript`) e badge UI dedicato `🎬 Intero Video`.
- **Prompt Super-Cut Memorabile**: Prompt LLM ottimizzato per isolare solo i concetti cardine e le epifanie memorabili, con fedeltà alle formulazioni potenti/aforistiche, eliminazione dei preamboli narrativi prolissi e chiusura incisiva.

### Modificato
- **UI Card YouTube**: Rimozione dei blocchi ridondanti e gestione differenziata del link timestamp per video interi vs timestamp specifici.

### Aggiunto
- **Ricerca Full-Text in Tempo Reale (Live Search)**: Barra di ricerca nella dashboard con scorciatoia `⌘+K` / `Esc`, ricerca multi-parola istantanea su citazioni, trascrizioni, titoli e autori/canali.
- **Modulo FilterManager (OOP)**: Separazione della logica di filtro e ricerca in `filter_manager.js` (rispetto del limite <500 righe per file).
- **Titoli e Canali Video YouTube Reali**: Recupero automatico dei metadati dei video (titolo e canale) tramite endpoint ufficiale oEmbed di YouTube.
- **Supporto YouTube Shorts**: Supporto nativo per i link formato `/shorts/VIDEO_ID`.
- **Automazione Condivisione (Apple Shortcuts & Google Apps Script)**: Webhook serverless per inserire automaticamente righe nel foglio da iPhone/Mac con minutaggio e pulizia automatica dell'URL.

### Corretto
- **Polling Indipendente per YouTube**: Il controllo del Google Sheet viene ora eseguito regolarmente a ogni ciclo di polling anche in assenza di nuovi bookmark Audiobookshelf.
- **Compatibilità youtube-transcript-api**: Aggiornati i metodi di recupero sottotitoli con supporto ai metodi `fetch()` e `list()`.
- **Cache-Busting Asset Statici**: Aggiunto versionamento `v2.3.0` agli import ES Modules per prevenire problemi di caching nel browser.

## [3.1.0] - 2026-08-30

### Aggiunto
- **Navigazione a Tab nella Dashboard**: Switcher in alto tra sezioni dedicate per `🎧 Audiolibri` e `🎬 YouTube Video` con contatori in tempo reale.
- **Flusso Cronologico per YouTube**: Visualizzazione continua senza sezioni divisorie per titolo; card compatte con canale, titolo video, link diretto al timestamp (`▶️ mm:ss`), data e citazione.
- **Pulsante Unico di Esportazione YouTube**: Toolbar dedicata con pulsante unico per esportare tutte le citazioni YouTube filtrate in CSV Readwise (RFC 4180) o JSON.
- **Pulsante Sincronizzazione Manuale**: Tasto `🔄 Sincronizza Ora` nell'header e nuovo endpoint `POST /api/poll` per avviare il controllo immediato dei nuovi bookmark ABS e link YouTube.
- **Modularizzazione Frontend (OOP)**: Nuovi moduli `export_manager.js` e `tabs.css`; codice organizzato e mantenuto rigorosamente sotto il limite di 500 righe per file.

## [3.0.0] - 2026-08-30

### Aggiunto
- **Citazioni YouTube via Google Sheets**: Nuova pipeline per catturare citazioni da video YouTube.
  - Incolli i link YouTube (con timestamp) in un Google Sheet condiviso.
  - L'app fa polling sul foglio (stesso ciclo di ABS) e processa i nuovi link automaticamente.
  - Sottotitoli scaricati via `youtube-transcript-api` (gratuito, nessun credito API per la trascrizione).
  - LLM estrae la citazione dalla finestra di sottotitoli (120s configurabile).
  - **Traduzione automatica**: citazioni in inglese tradotte in italiano dall'LLM; originale conservato.
  - **Graceful degradation**: se i sottotitoli non sono disponibili, la citazione viene salvata con `confidence: low` per la revisione manuale tramite il pulsante "Verify" esistente.
  - Tracking dei link processati in `state.json` (sezione `youtube_processed`).
- **Badge sorgente nella dashboard**: Icona 🎬 per citazioni YouTube, 🎧 per audiolibri.
- **Link cliccabile al video**: Il timestamp delle citazioni YouTube è un link che apre il video al punto esatto.
- **Citazione originale**: Per le citazioni tradotte, la versione originale in inglese è visibile nei dettagli espansi.
- **Nuovi moduli**: `youtube_sheet_client.py` (lettura Google Sheet) e `youtube_transcript.py` (sottotitoli YouTube).
- **Nuove variabili .env**: `GOOGLE_SHEETS_API_KEY`, `YOUTUBE_SHEET_ID`, `YOUTUBE_PRE_SECONDS`, `YOUTUBE_POST_SECONDS`.

### Modificato
- **Feature opzionale e retrocompatibile**: Se le variabili YouTube non sono configurate, l'app funziona esattamente come prima.
- **StoreManager**: Nuovo metodo `append_youtube_quote()` e campo `source_type` in tutte le citazioni (default `"audiobook"`).
- **StateManager**: Nuova sezione `youtube_processed` con backward compatibility automatica.
- **LlmManager**: Nuovo metodo `extract_youtube_quote()` con prompt ottimizzato per video e traduzione.
- **Dashboard UI**: Badge sorgente, link cliccabili, citazione originale, pulsante "Reprocess" nascosto per YouTube.

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
