# AudiobookNotes 🎧📝

**AudiobookNotes** è un'applicazione intelligente creata per aiutarti a catturare, organizzare e gestire le citazioni più importanti dei tuoi audiolibri preferiti. 

L'applicazione fa tutto da sola in background: monitora i segnalibri (bookmark) che inserisci mentre ascolti i tuoi libri su **Audiobookshelf**, ne estrae l'audio, lo trascrive e, grazie all'Intelligenza Artificiale, estrae l'esatta citazione testuale, mostrandoti poi tutto in una splendida dashboard web accessibile dal tuo browser.

---

## 🚀 Come Funziona (Il Flusso dei Dati)

Ogni volta che premi il pulsante "Bookmark" (Segnalibro) sulla tua app di ascolto:

```
[Audiobookshelf Bookmark] 
       │
       ▼ (L'app rileva il bookmark)
[Ritaglio Audio] ──► Taglia gli ultimi secondi (es. 20s prima e dopo il bookmark)
       │
       ▼
[Whisper API (OpenRouter)] ──► Converte la registrazione audio in testo
       │
       ▼
[AI / LLM (OpenRouter)] ──► Analizza il testo ed estrae l'esatta frase letterale
       │
       ▼
[Database Locale (JSON)] ──► Salva la citazione, il voto di precisione e la trascrizione
       │
       ▼
[Dashboard Web (Porta 7777)] ──► Visualizzi, filtri, modifichi o scarichi le note!
```

---

## ⚙️ Configurazione Facile (`.env`)

L'applicazione legge le sue impostazioni dal file nascosto chiamato `.env` situato nella cartella principale del progetto. Puoi aprirlo con qualsiasi editor di testo. I campi principali sono:

* `ABS_URL`: L'indirizzo del tuo server Audiobookshelf (es. `http://192.168.1.100:8080`).
* `ABS_TOKEN`: Il tuo token di sicurezza di Audiobookshelf (consente all'app di leggere i tuoi bookmark).
* `OPENROUTER_API_KEY`: La tua chiave API di OpenRouter (necessaria per far funzionare l'Intelligenza Artificiale).
* `OPENROUTER_LLM_MODEL`: Il modello AI per l'estrazione delle citazioni (impostato di default su `openrouter/auto`).
* `OPENROUTER_STT_MODEL`: Il modello per la trascrizione vocale (impostato su `mistralai/voxtral-mini-transcribe`).
* `POLL_INTERVAL_SECONDS`: Intervallo in secondi tra ogni controllo su Audiobookshelf (es. `60`).
* `PRE_SECONDS` / `POST_SECONDS`: Finestra audio da estrarre prima e dopo la marcatura del bookmark (es. `20`).

---

## 🛠️ Come Avviare l'Applicazione su Mac

Grazie alla tecnologia Docker, non devi installare linguaggi di programmazione o librerie sul tuo computer Mac. Tutto è già configurato all'interno di un contenitore isolato.

1. Assicurati che l'applicazione **Docker** sia aperta sul tuo Mac (l'icona con la balena nella barra dei menu in alto).
2. Apri la cartella del progetto e fai **doppio clic sul file `restart_docker.command`**.
3. Si aprirà una finestra del terminale che provvederà in automatico a:
   * Spegnere l'applicazione se era già attiva.
   * Aggiornare il codice e installare i componenti necessari.
   * Avviare l'applicazione in background.
4. Una volta terminata la procedura, puoi chiudere la finestra del terminale. L'applicazione continuerà a funzionare in background!

---

## 💻 Come Usare la Dashboard Web (Inglese)

Una volta avviata l'applicazione, apri il tuo browser web (Safari, Chrome o Firefox) e vai all'indirizzo:
👉 **[http://localhost:7777](http://localhost:7777)**

Ti troverai davanti a una dashboard moderna in modalità scura, con l'interfaccia interamente localizzata in lingua inglese:

### 1. Visualizzazione Strutturata a Timeline
* Le citazioni non sono più ripetitive: sono **raggruppate per libro** all'interno di eleganti schede di sezione.
* All'interno di ogni libro, le citazioni sono organizzate come una **timeline cronologica** ordinate sequenzialmente per posizione audio (`time`) crescente.
* Accanto a ogni citazione c'è un'etichetta colorata (*High, Medium, Low*) che indica quanto l'Intelligenza Artificiale è sicura della precisione di quella citazione.
* Il testo delle citazioni è visualizzato in caratteri normali nitidi e lineari (non in corsivo) per garantire la massima leggibilità.

### 2. Verifica In-Place & Dettagli Integrati ("Verify")
* Accanto alla posizione temporale di ogni citazione troverai il pulsante minimalista **"✏️ Verify"**.
* Cliccando su **"✏️ Verify"**, la card si espanderà all'istante rivelando:
  * Una casella di testo interattiva per **correggere manualmente** la citazione se contiene errori di trascrizione.
  * La sezione **"Original Transcription"** contenente il testo vocale grezzo estratto.
  * La sezione **"LLM Extraction Reasoning"** con la spiegazione logica elaborata dall'Intelligenza Artificiale.
  * Una scorciatoia per **ri-elaborare la singola citazione ("Reprocess +20% Audio")** allargando la finestra temporale.
* Cliccando sul pulsante **"💾 Save"** salverai le modifiche in tempo reale e il livello di precisione (confidence) verrà automaticamente promosso a **High**.
* Puoi richiudere la visualizzazione in qualsiasi momento premendo **"✕ Close"**.

### 3. Esportazione JSON Mirata ("Download")
* Non c'è più bisogno di applicare filtri di selezione per poter scaricare le note!
* Sulla destra dell'intestazione di ciascun libro è presente un pulsante pillola ultra-elegante **"📥 Download"**.
* Cliccandoci, scaricherai sul tuo Mac un file `.json` contenente **esclusivamente le citazioni di quel libro** ordinate per posizione, già formattate in modo pulito con le chiavi inglesi `quote` (citazione letterale) e `position` (minuti e secondi).
* Prima del download, l'app effettuerà un controllo automatico e ti avviserà se ci sono note non ancora verificate (con confidence inferiore a *High*) per consentirti di correggerle prima dell'esportazione.

### 4. Filtri Intelligenti in Tempo Reale
In alto è presente una barra dei filtri che lavora all'istante senza ricaricare la pagina:
* **Select Book**: Visualizza le citazioni di un solo audiolibro o di tutti ("All books").
* **Confidence Level**: Filtra le citazioni in base all'accuratezza AI (High, Medium, Low) o visualizzale tutte ("All levels").
* **Date Range**: Inserisci una data di inizio e di fine per vedere solo le citazioni prese in quel lasso temporale.

### 5. Rigenerazione Totale ("Regenerate Database")
* Se desideri rielaborare da zero l'intero database locale (ad esempio per caricare tutti i bookmark storici dopo aver aggiornato la lingua o le impostazioni nel file `.env`), clicca sul pulsante **"🔄 Regenerate Database"** in alto a destra nell'header.
* Ti verranno chieste due conferme di sicurezza consecutive per evitare azzeramenti involontari e avvisarti del potenziale consumo di crediti API OpenRouter.
* Una volta confermato, il database locale verrà ricostruito in background e la dashboard caricherà gradualmente le citazioni man mano che vengono processate.
