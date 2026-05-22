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
            "Sei un assistente specializzato nell'estrazione di citazioni (highlight) da trascrizioni testuali di audiolibri.\n"
            "Il tuo obiettivo è isolare l'esatta frase (verbatim) che l'utente ha voluto salvare con un bookmark.\n\n"
            "Istruzioni cruciali:\n"
            "1. CERCA L'AFORISMA O L'EPIFANIA: Gli utenti inseriscono bookmark per salvare frasi brevi, potenti, aforistiche o illuminanti (es. 'Ciò che è creativo deve creare se stesso'). Ignora il contesto discorsivo di contorno o la preparazione narrativa. Punta al fulcro assoluto del concetto.\n"
            "2. VERBATIM MA CON CONFINI LOGICI: Estrai il testo esattamente come appare. Fermati appena l'aforisma o il concetto principale è concluso, interrompendo l'estrazione anche in assenza di punteggiatura corretta nella trascrizione.\n"
            "3. POSIZIONE DEL BOOKMARK: Il punto centrale dell'epifania si trova di solito poco prima o esattamente a metà della trascrizione fornita.\n"
            "4. INDIZI ASSOLUTI: Se l'utente fornisce una nota (bookmark_title), è la chiave definitiva per scegliere il passaggio.\n"
            "5. CONFIDENCE AL RIBASSO (FORZATURA REVISIONE): Sei incoraggiato a usare 'medium' o 'low' molto frequentemente. Usa 'high' SOLO se c'è una singola frase inequivocabilmente memorabile e isolata. Se:\n"
            "   - Il testo è denso e contiene un aforisma breve ma anche una frase lunga di contesto altrettanto valida.\n"
            "   - Ci sono due potenziali citazioni distinte.\n"
            "   -> DEVI impostare 'confidence' a 'medium' per forzare una revisione umana.\n"
            "6. PROPOSTE ALTERNATIVE (OBBLIGATORIE CON MEDIUM/LOW): Quando imposti la confidence a 'medium' o 'low', metti nel campo 'quote' la frase più breve e aforistica. Successivamente, nel campo 'reasoning', DEVI proporre le alternative trascrivendole esattamente, ad esempio scrivendo: 'Alternativa di contesto più ampia: [inserisci frase]'.\n"
            "7. RUMORE: Se c'è solo silenzio o testo incoerente, quote=null e confidence=low.\n\n"
            "Devi rispondere ESCLUSIVAMENTE in formato JSON con la seguente struttura:\n"
            "{\n"
            "  \"quote\": \"testo verbatim isolato (la frase aforistica) oppure null\",\n"
            "  \"confidence\": \"high|medium|low\",\n"
            "  \"reasoning\": \"Spiega il motivo logico. SE confidence è medium/low, TRASCRIVI QUI l'alternativa esatta per facilitare la revisione dell'utente.\"\n"
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
