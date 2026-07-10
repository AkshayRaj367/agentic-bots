try:
    from keybert import KeyBERT
except Exception:
    KeyBERT = None

_BASIC_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "to", "of",
    "in", "on", "at", "by", "with", "from", "as", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it", "its", "we",
    "you", "your", "they", "their", "i", "me", "my", "our", "us"
}

class SentenceBert:
    def __init__(self, sentence: str):
        self.sentence = sentence
        self.kw_model = KeyBERT() if KeyBERT is not None else None

    def extract_keywords(self, top_n: int = 5) -> list:
        if self.kw_model is None:
            # Fallback: simple frequency-based keywords to avoid heavy ML deps.
            tokens = []
            for raw in self.sentence.split():
                token = "".join(ch for ch in raw.lower() if ch.isalnum())
                if not token or token in _BASIC_STOP_WORDS or len(token) < 3:
                    continue
                tokens.append(token)

            freq = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1

            ranked = sorted(freq.items(), key=lambda item: (-item[1], item[0]))
            return ranked[:top_n]

        return self.kw_model.extract_keywords(
            self.sentence,
            keyphrase_ngram_range=(1, 1),
            stop_words='english',
            top_n=top_n,
            use_mmr=True,
            diversity=0.7
        )
