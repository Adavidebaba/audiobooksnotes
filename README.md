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
[Ritaglio Audio] ──► Taglia gli ultimi secondi (es. 30s prima e dopo il bookmark)
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

* `ABS_URL`: L'indirizzo del tuo server Audiobookshelf (es. `http://192.168.1.100:8189`).
* `ABS_TOKEN`: Il tuo token di sicurezza di Audiobookshelf (consente all'app di leggere i tuoi bookmark).
* `OPENROUTER_API_KEY`: La tua chiave API di OpenRouter (necessaria per far funzionare l'Intelligenza Artificiale).
* `OPENROUTER_LLM_MODEL`: Il modello AI per l'estrazione delle citazioni (impostato di default su `openrouter/auto`).
* `OPENROUTER_STT_MODEL`: Il modello per la trascrizione vocale (impostato su `mistralai/voxtral-mini-transcribe` o Whisper).

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

## 💻 Come Usare la Dashboard Web

Una volta avviata l'applicazione, apri il tuo browser web (Safari, Chrome o Firefox) e vai all'indirizzo:
👉 **[http://localhost:7777](http://localhost:7777)**

Ti troverai davanti a una dashboard moderna in modalità scura dove potrai gestire le tue note:

### 1. Visualizzazione ed Espansione
* Nella pagina principale vedrai l'elenco di tutte le citazioni salvate, ordinate per data (le ultime in alto).
* Accanto a ogni citazione c'è un'etichetta colorata (*High, Medium, Low*) che indica quanto l'Intelligenza Artificiale è sicura della precisione di quella citazione.
* Clicca su **"Espandi dettagli"** per aprire una sezione in cui confrontare la citazione estratta con l'intera trascrizione audio originale e leggere la spiegazione/ragionamento fornito dall'AI.

### 2. Modifica In-Place (Correzione Rapida)
* Se la trascrizione automatica contiene parole errate, puoi **cliccare direttamente dentro la casella della citazione** e correggerla a mano.
* Puoi anche cambiare il livello di precisione (confidence) dal comodo menu a tendina.
* Clicca sul pulsante **"Salva"**: le modifiche verranno salvate all'istante all'interno dei file del tuo computer e un avviso verde a comparsa ti confermerà l'avvenuto salvataggio.

### 3. Filtri Intelligenti in Tempo Reale
In alto è presente una barra dei filtri che lavora all'istante senza ricaricare la pagina:
* **Seleziona Libro**: Mostra solo le citazioni di un audiolibro specifico.
* **Voto Confidence**: Filtra le citazioni in base alla loro accuratezza AI (es. vedi solo quelle con voto "Low" per correggerle rapidamente).
* **Intervallo Date**: Scegli una data di inizio e di fine per vedere solo le citazioni che hai preso in quel determinato periodo (es. solo quelle di oggi o di questa settimana).

### 4. Esportazione JSON (Pronta per Notion o Obsidian)
* Quando selezioni un libro specifico dal filtro in alto, apparirà un pulsante **"📥 Scarica"** accanto al menu.
* Cliccandoci, scaricherai sul tuo Mac un file `.json` pulito denominato con il titolo del libro e l'autore (es. `Gli insegnamenti segreti di Gesù - San Tommaso.json`).
* Il file conterrà l'elenco delle citazioni ordinate, con indicata solo la **citazione** e la **posizione temporale** esatta (es. `33:00` ovvero minuti e secondi dell'audiolibro). È perfetto da copiare su altre app o database personali!

### 5. Cancellazione Sicura
* Se un bookmark non ti serve più, clicca sul pulsante rosso **"Elimina"**.
* Ti apparirà una finestra di conferma per evitare cancellazioni accidentali. Cliccando su "Sì, Elimina", la nota verrà rimossa per sempre dal file del libro sul disco.

### 6. Rigenerazione Totale (Override del Bootstrap)
* Se desideri rielaborare da zero l'intero database (ad esempio dopo aver modificato i modelli AI o la lingua nel file `.env`), clicca sul pulsante rosso **"🔄 Rigenera Database"** in alto a destra nell'header.
* Per sicurezza, ti verrà chiesta una **doppia conferma** prima di procedere per evitare azzeramenti involontari e avvisarti del potenziale consumo di crediti API di OpenRouter.
* Una volta confermato, il database locale verrà azzerato e il server avvierà un riprocessamento completo in background di tutti i bookmark di Audiobookshelf. La dashboard mostrerà uno stato di attesa e caricherà dinamicamente le citazioni man mano che vengono elaborate!
