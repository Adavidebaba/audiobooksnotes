import json
from openai import OpenAI
from typing import Dict, Any, Optional

class LlmManager:
    """Manager responsible for extracting verbatim quotes from audio transcriptions using OpenAI Chat API."""

    def __init__(self, api_key: str, model_name: str = "openrouter/auto") -> None:
        """Initializes the LlmManager with OpenRouter credentials and target model."""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model_name = model_name

    def _get_system_prompt(self) -> str:
        """Returns the system instructions for quote extraction."""
        return (
            "Sei un assistente specializzato nell'analisi di trascrizioni di audiolibri.\n"
            "Il tuo compito è identificare e isolare l'esatta citazione letterale (verbatim) che l'utente intendeva salvare "
            "quando ha inserito un bookmark.\n\n"
            "Istruzioni cruciali:\n"
            "1. Identifica una sola frase saliente e significativa.\n"
            "2. La citazione deve essere riportata LETTERALMENTE (verbatim) come appare nella trascrizione. Non fare parafrasi, "
            "non correggere la grammatica, non aggiungere punteggiatura se non è presente nel testo trascritto. Deve essere un drop-in match.\n"
            "3. Euristica: l'utente solitamente inserisce il bookmark SUBITO DOPO aver ascoltato il passaggio interessante. Di conseguenza, "
            "il punto centrale del bookmark è a metà del segmento da 60s. Favorisci frasi nei 10-20 secondi precedenti il punto centrale (ovvero nella prima metà della trascrizione), "
            "ma se la citazione completa prosegue o inizia poco dopo, prendila interamente.\n"
            "4. Se l'utente ha inserito una nota (bookmark_title), usala come indizio fondamentale per capire quale frase salvare.\n"
            "5. Se nella trascrizione c'è solo silenzio, rumore o frasi incoerenti prive di senso letterario/narrativo, "
            "ritorna la quote come null e imposta confidence a 'low'.\n\n"
            "Devi rispondere esclusivamente in formato JSON con la seguente struttura:\n"
            "{\n"
            "  \"quote\": \"testo verbatim della citazione oppure null\",\n"
            "  \"confidence\": \"high|medium|low\",\n"
            "  \"reasoning\": \"una singola frase sintetica in italiano che spiega la scelta\"\n"
            "}"
        )

    def _get_user_prompt(
        self, 
        transcript: str, 
        book_title: str, 
        author: str, 
        bookmark_title: Optional[str]
    ) -> str:
        """Constructs the user message string with context details."""
        prompt = (
            f"Dettagli Audiolibro:\n"
            f"- Titolo: {book_title}\n"
            f"- Autore: {author}\n\n"
            f"Nota del bookmark inserita dall'utente: '{bookmark_title or ''}'\n\n"
            f"Trascrizione completa dei 60 secondi (il bookmark è al secondo 30, ovvero a metà di questa trascrizione):\n"
            f"\"\"\"\n{transcript}\n\"\"\"\n"
        )
        return prompt

    def extract_verbatim_quote(
        self, 
        transcript: str, 
        book_title: str, 
        author: str, 
        bookmark_title: Optional[str]
    ) -> Dict[str, Any]:
        """Calls the OpenAI Chat API to extract the verbatim quote.
        
        Returns:
            A dictionary containing 'quote' (str or None), 'confidence' (str), and 'reasoning' (str).
        """
        if not transcript.strip():
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": "La trascrizione è vuota."
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": self._get_user_prompt(transcript, book_title, author, bookmark_title)}
                ],
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content
            return json.loads(result_text)
            
        except Exception as e:
            # Fallback in case of API failure or parsing errors
            return {
                "quote": None,
                "confidence": "low",
                "reasoning": f"Errore nell'estrazione LLM: {str(e)}"
            }
