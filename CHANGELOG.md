# Changelog

Tutti i cambiamenti significativi a questo progetto saranno documentati in questo file.

## [1.0.0] - 2026-05-22

### Aggiunto
- **Integrazione Audiobookshelf**: Client per connettersi ad un server Audiobookshelf, scaricare metadati ed elaborare i capitoli degli audiolibri.
- **Trascrizione Audio (STT)**: Elaborazione e trascrizione dei file audio estratti usando il modello `mistralai/voxtral-mini-transcribe` via OpenRouter.
- **Analisi e Sintesi (LLM)**: Generazione automatica di appunti strutturati, riassunti e concetti chiave dai capitoli trascritti utilizzando `openrouter/auto`.
- **Gestione dello Stato**: Sistema di persistenza locale per tracciare lo stato di avanzamento dell'ascolto e dell'elaborazione per ciascun libro.
- **Dockerizzazione**: Configurazione di Docker e `docker-compose.yml` con uno script helper (`restart_docker.command`) per avviare, arrestare e ricostruire facilmente l'applicazione su macOS.
- **Configurazione Dinamica**: Gestione delle chiavi API e dei parametri di connessione tramite variabili d'ambiente (`.env`).
