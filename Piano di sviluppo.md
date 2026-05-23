# AudiobookNotes — Trascrizione automatica dei bookmark di Audiobookshelf

## Context

L'utente usa Audiobookshelf (ABS) per ascoltare audiolibri in italiano e inserisce bookmark quando incontra passaggi interessanti. Vuole un'app che, in modo continuo e automatico:

1. Rilevi i nuovi bookmark inseriti in ABS
2. Estragga una finestra audio configurabile attorno al timestamp del bookmark (default 30s prima / 30s dopo)
3. Trascriva il segmento con OpenAI Whisper API
4. Usi un LLM OpenAI (GPT-4/5) per identificare la **citazione verbatim** che probabilmente l'utente voleva salvare
5. Persista trascrizione + citazione in un file JSON per libro

L'obiettivo è trasformare l'atto rapido di "metto un bookmark" in una raccolta strutturata e ricercabile di citazioni dei propri audiolibri, senza dover riascoltare nulla.

## Architettura

Servizio Python in container Docker che gira accanto al container di ABS. Loop di polling che interroga periodicamente l'API ABS (`/api/me`) per leggere lo stato corrente dei bookmark dell'utente, confronta con uno stato locale persistente, e processa solo i bookmark nuovi o modificati.

```
┌──────────────────┐    poll     ┌─────────────────────┐
│   ABS server     │ ◀────────── │  audiobooknotes     │
│  /api/me         │             │  (container Docker) │
│  /api/items/:id  │             │                     │
│  /s/item/:id/... │ ── Range ──▶│  - poller           │
└──────────────────┘             │  - audio extractor  │
                                 │  - STT (Whisper API)│
                                 │  - LLM (OpenAI)     │
                                 │  - JSON store       │
                                 └─────────┬───────────┘
                                           │
                                           ▼
                                  /data/books/<book>.json
                                  /data/state.json
```

## API Audiobookshelf — endpoint usati

- `GET /api/me` → ritorna `user.bookmarks: [{ libraryItemId, title, time, createdAt }]`. Non c'è un ID stabile per bookmark: l'identità è la coppia `(libraryItemId, time)` — anche ABS usa questa coppia per `PATCH`/`DELETE`. `createdAt` è in **millisecondi** epoch. `time` è in **secondi** (float) rispetto all'inizio del libro.
- `GET /api/items/<libraryItemId>?expanded=1` → ritorna `media.tracks[]` con `index`, `startOffset` (secondi dall'inizio del libro), `duration`, `contentUrl` (URL completo da usare così com'è, non da costruire a mano), `mimeType`, `metadata.filename`. Anche `media.metadata.title`, `media.metadata.authorName`, `media.metadata.narratorName`.
- Audio: `GET <contentUrl>` con `Authorization: Bearer <token>`. ABS supporta HTTP Range nativamente.
- Auth: `Authorization: Bearer <token>`. Il token si recupera in ABS Web UI → Settings → Users → click sul proprio utente → campo "API Token", oppure tramite `POST /login` (campo `user.token` nella risposta).

Mapping `bookmark.time` (tempo totale del libro) → traccia: trovare la traccia `t` tale che `t.startOffset <= bookmark.time < t.startOffset + t.duration`; il tempo locale nella traccia è `bookmark.time - t.startOffset`.

## Estrazione audio — strategia

Per ogni bookmark da processare, finestra `[bookmark.time - PRE_SECONDS, bookmark.time + POST_SECONDS]` (default 30/30, configurabili). La finestra viene **clampata** ai bordi del libro (se `bookmark.time < PRE_SECONDS` o `bookmark.time + POST_SECONDS > durata_totale`). Se la finestra attraversa il bordo tra due tracce, scaricare entrambi i segmenti e concatenarli con ffmpeg (`concat` filter).

Tecnica scelta: **ffmpeg legge direttamente l'URL HTTP**, lasciando a lui la gestione di Range, seek e decoding. Whisper API accetta file fino a 25 MB — un mp3 da 60s mono 32 kbps pesa ~240 KB, ben sotto il limite.

Pipeline per ogni bookmark:

1. Recupera metadata del libro (`/api/items/<id>?expanded=1`), trova la/le traccia/e coinvolte.
2. Per ogni traccia coinvolta, invoca `ffmpeg -headers "Authorization: Bearer <token>\r\n" -ss <start_locale> -to <end_locale> -i <contentUrl> -vn -ac 1 -ar 16000 -b:a 32k -f mp3 <segment>.mp3`.
   - Mettere `-ss`/`-to` **prima** di `-i` abilita il seek veloce via Range (input seeking). Per gli mp3 può essere lievemente impreciso al sample; per i nostri scopi va benissimo.
3. Se serve concatenare 2 segmenti (bookmark a cavallo di tracce), usare `ffmpeg -i a.mp3 -i b.mp3 -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1" out.mp3`.
4. Il file finale `/tmp/<libraryItemId>_<time>.mp3` viene caricato a Whisper e poi rimosso.

ffmpeg parla nativamente HTTP/HTTPS e supporta `-headers` per passare il bearer token, quindi non serve scaricare manualmente con httpx. Ridurre a mono 16 kHz 32 kbps riduce la dimensione senza degradare la qualità STT (Whisper internamente lavora a 16 kHz mono).

## Gestione errori e robustezza

- **Errori transienti** (timeout, 5xx, rete): retry con backoff esponenziale (1s, 2s, 4s, max 3 tentativi). Se fallisce, il bookmark **non** viene marcato come processato e verrà ritentato al poll successivo.
- **Errori permanenti** (404 sul libro, 401 token scaduto): log a livello ERROR, bookmark marcato con `status: "failed"` e `error: "..."` nello state per evitare loop infiniti. L'utente può rimuovere manualmente l'entry dallo state per ri-tentare.
- **ffmpeg fallisce**: log dell'stderr completo, bookmark in stato `failed`.
- **Whisper restituisce trascrizione vuota** (silenzio): comunque salvata, ma LLM step saltato e `quote = null`.
- **LLM restituisce JSON malformato**: un retry con prompt di correzione, poi fallback a `quote = null, quote_reasoning = "LLM parse failed"`.
- **Salvataggio atomico**: scrivere su `<file>.tmp` e poi `os.replace` per evitare corruzione del JSON in caso di crash a metà scrittura. Stessa cosa per `state.json`.
- **Concorrenza**: nessuna (un solo loop, un bookmark alla volta). Niente lock necessari.

## Identificazione dei bookmark da processare

Stato persistente in `/data/state.json`. La **chiave** è `<libraryItemId>:<time>` (con `time` arrotondato a 3 decimali per stabilità float):

```json
{
  "version": 1,
  "bookmarks": {
    "<libraryItemId>:<time>": {
      "libraryItemId": "...",
      "time": 1234.5,
      "title": "...",
      "createdAt": 1716200000000,
      "processed_at": "2026-05-21T10:30:00Z",
      "audio_window": {"pre": 30, "post": 30},
      "status": "ok"
    }
  }
}
```

Al poll, l'app legge `/api/me`, costruisce il set di chiavi correnti, e processa solo le chiavi **non presenti** nello stato (o con `status: "failed"` se decidiamo di permettere il retry manuale rimuovendole).

- **Bookmark spostato** (`time` cambiato in ABS): chiave nuova → trattato come bookmark nuovo. Il record vecchio resta sia nello state che nel JSON del libro (storico).
- **Bookmark eliminato** in ABS: la chiave sparisce da `/api/me` ma resta nello state e nel JSON locale (non sincronizziamo le delete, come richiesto).
- **Solo `title` cambiato**: la chiave non cambia (è basata su id+time) → nessun re-process; il titolo originale resta nel JSON. Accettabile per ora.

## File JSON di output — un file per libro

Path: `/data/books/<libraryItemId>__<slug_titolo>.json`

```json
{
  "libraryItemId": "li_8gch9ve09orgn4fdz8",
  "title": "Il nome della rosa",
  "author": "Umberto Eco",
  "narrator": "...",
  "updated_at": "2026-05-21T10:30:00Z",
  "bookmarks": [
    {
      "time": 1234.5,
      "title": "passo sul labirinto",
      "createdAt": 1716200000000,
      "processed_at": "2026-05-21T10:30:00Z",
      "audio_window": {"pre": 30, "post": 30},
      "transcript": "...trascrizione completa dei ~60s in italiano...",
      "quote": "la citazione verbatim individuata dall'LLM, parole esatte dalla trascrizione",
      "quote_confidence": "high|medium|low",
      "quote_reasoning": "breve spiegazione del perché l'LLM ha scelto questa frase"
    }
  ]
}
```

Una entry per bookmark; in caso di ri-trascrizione, viene aggiunta una nuova entry (storico preservato).

## Prompt LLM per estrazione citazione

L'LLM riceve la trascrizione completa dei ~60s, il titolo del libro/autore e (se disponibile) il `title` del bookmark scritto dall'utente. Istruzioni:

- Identificare **una sola frase**, riportata **letteralmente (verbatim)** come appare nella trascrizione — niente parafrasi, niente correzioni grammaticali, niente aggiunte di punteggiatura non presente.
- Euristica: il bookmark è tipicamente posto **subito dopo** aver sentito qualcosa di notevole → favorire frasi nei ~10s precedenti il punto centrale, ma se la trascrizione è chiaramente sbilanciata verso la fine (es. una citazione completa solo dopo il punto centrale) prendere quella.
- Preferire frasi complete e auto-contenute. Se il segmento contiene una citazione esplicita (es. "...e Eco scrisse: ..."), preferire il contenuto della citazione.
- Se il `title` del bookmark è informativo (l'utente ha scritto una nota), usarlo come hint.
- Output JSON strutturato (con `response_format={"type": "json_object"}` o equivalente):

```json
{
  "quote": "testo verbatim",
  "confidence": "high|medium|low",
  "reasoning": "una frase breve"
}
```

Se nessuna frase saliente esiste (silenzio, parlato non coerente), `quote: null, confidence: "low"`.

## File del progetto da creare

```
audiobooksnotes/
├── docker-compose.yml          # servizio audiobooknotes (+ riferimento opzionale ad abs esistente)
├── Dockerfile                  # python:3.12-slim + ffmpeg
├── requirements.txt            # httpx, openai, python-dotenv, pydantic
├── .env.example                # ABS_URL, ABS_TOKEN, OPENAI_API_KEY, POLL_INTERVAL, PRE_SECONDS, POST_SECONDS, DATA_DIR
├── src/
│   ├── main.py                 # entrypoint, loop di polling
│   ├── abs_client.py           # client API ABS (auth, /api/me, /api/items, audio Range)
│   ├── state.py                # carica/salva /data/state.json, diff bookmark
│   ├── audio.py                # mapping time→traccia, download Range, ffmpeg cut
│   ├── stt.py                  # wrapper OpenAI Whisper API
│   ├── llm.py                  # wrapper OpenAI Chat → estrazione quote (response_format json)
│   └── store.py                # legge/scrive /data/books/<id>__<slug>.json
└── data/                       # volume montato, contiene state.json e books/
```

## Configurazione (.env)

```
ABS_URL=http://audiobookshelf:80
ABS_TOKEN=<api token>
OPENAI_API_KEY=sk-...
OPENAI_STT_MODEL=whisper-1
OPENAI_LLM_MODEL=gpt-4o
POLL_INTERVAL_SECONDS=60
PRE_SECONDS=30
POST_SECONDS=30
LANGUAGE=it
DATA_DIR=/data
LOG_LEVEL=INFO
```

Note di sicurezza: `.env` non va committato (aggiungere `.env` e `data/` a `.gitignore`). Il token ABS dà accesso completo all'account, trattarlo come password.

## Bootstrap iniziale (primo avvio)

Al primissimo avvio `state.json` non esiste. Comportamento di default: **tutti** i bookmark esistenti in ABS verranno trattati come nuovi e processati uno alla volta. Se l'utente ne ha molti, questo può costare in chiamate STT/LLM.

Mitigazione: flag `BOOTSTRAP_MODE` in `.env`:
- `all` (default): processa tutto lo storico.
- `skip`: marca tutti i bookmark esistenti come già processati senza trascriverli (utile per partire pulito da oggi in poi).
- `since=<timestamp_iso>`: processa solo i bookmark con `createdAt` successivo a una data.

## Costi indicativi (per riferimento)

- Whisper API: ~$0.006/minuto. 60s → ~$0.006 a bookmark.
- gpt-4o input: ~$2.50/M token. 60s di parlato in italiano ≈ 150-200 token, prompt+istruzioni ≈ 300 token, output ≈ 100 token → ~$0.002 a bookmark.
- Totale: ~$0.01 a bookmark. 100 bookmark al mese = ~$1.

## Verifica end-to-end

1. **Bootstrap**: `cp .env.example .env` e compilare ABS_TOKEN + OPENAI_API_KEY. `docker compose up --build`.
2. **Smoke test API ABS**: log all'avvio deve mostrare `GET /api/me OK, bookmarks=<N>`. Se 401 → token sbagliato.
3. **Test bookmark nuovo**: in ABS app, ascoltare un audiolibro italiano, mettere un bookmark in un punto noto (es. una frase che ricordi a mente). Entro `POLL_INTERVAL_SECONDS` secondi:
   - Log: `nuovo bookmark <id> time=<t> → estrazione audio`
   - Log: `STT completato, <N> caratteri`
   - Log: `quote estratta: "..."`
   - File `/data/books/<id>__<slug>.json` aggiornato.
4. **Verifica accuratezza**: la `quote` nel JSON deve corrispondere (verbatim, modulo piccoli errori STT) alla frase ricordata. La `transcript` deve coprire ~60s di parlato.
5. **Test ri-trascrizione**: in ABS spostare il `time` del bookmark di +20s. Al successivo poll, deve apparire una seconda entry nel JSON con audio_window centrata sul nuovo tempo.
6. **Test edge bordo traccia**: mettere un bookmark vicino all'inizio/fine di una traccia (cap. multipli). Verificare che la finestra venga ricostruita correttamente da entrambe le tracce.
7. **Test persistenza**: `docker compose restart` → al riavvio non deve ri-processare bookmark già in `state.json`.

## Ordine di implementazione

1. Scheletro progetto: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.env.example`
2. `abs_client.py`: auth + `/api/me` + `/api/items` + download Range
3. `state.py`: load/save `state.json`, diff per `libraryItemId:time`
4. `audio.py`: mapping time→traccia, Range fetch, ffmpeg cut, gestione bordo tracce
5. `stt.py`: wrapper OpenAI Whisper (lingua=`it`)
6. `llm.py`: wrapper OpenAI Chat con response_format JSON
7. `store.py`: load/append/save `/data/books/<id>__<slug>.json`
8. `main.py`: loop di polling che orchestra il tutto
9. Test end-to-end con un libro reale e bookmark vero

## Da verificare prima/durante l'implementazione

La documentazione ufficiale di ABS dichiara di essere "out-of-date". Prima di scrivere `abs_client.py` conviene fare alcuni controlli rapidi contro l'istanza reale dell'utente con `curl`:

1. `curl -H "Authorization: Bearer $ABS_TOKEN" $ABS_URL/api/me | jq .bookmarks` → verificare shape effettiva di un bookmark (campi `libraryItemId`, `title`, `time`, `createdAt`).
2. `curl -H "Authorization: Bearer $ABS_TOKEN" "$ABS_URL/api/items/<id>?expanded=1" | jq .media.tracks` → confermare presenza di `startOffset`, `duration`, `contentUrl`, `mimeType`.
3. `curl -I -H "Authorization: Bearer $ABS_TOKEN" "<contentUrl>"` → confermare `Accept-Ranges: bytes` e `Content-Length`.
4. `ffmpeg -headers "Authorization: Bearer $ABS_TOKEN" -ss 60 -to 70 -i "<contentUrl>" -ac 1 -ar 16000 -f mp3 /tmp/test.mp3` → confermare che ffmpeg sa parlare con ABS via header bearer e estrarre un segmento.

Se uno di questi step fallisce o ritorna shape diverse dalle attese, aggiornare il piano prima di scrivere codice.

## Punti aperti / decisioni rimandate

- **UI**: non prevista in questa prima versione (CLI/servizio); il consumo è via file JSON.
- **Notifiche** (es. push quando una nuova citazione è pronta): non richiesta ora.
- **Multi-utente ABS**: l'app usa il token di un singolo utente; per più utenti, replicare il container o estendere la config.
- **Sync delete**: bookmark eliminati in ABS restano nei JSON locali come storico.
- **Update del titolo del bookmark**: cambi al solo `title` non triggerano re-process (per design — la chiave è id+time).
- **Webhook ABS**: ABS al momento (versioni recenti) supporta WebSocket per eventi; sostituire il polling con WS è un upgrade futuro che ridurrebbe latenza e carico.
- **Lingua**: hardcoded `it` nella config. L'app gestisce solo italiano in questa versione; per multi-lingua leggere `media.metadata.language` se presente.
