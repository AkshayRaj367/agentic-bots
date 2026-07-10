try:
    import ollama
except Exception:
    ollama = None
from src.logger import Logger
from src.config import Config

log = Logger()


class Ollama:
    def __init__(self):
        if ollama is None:
            self.client = None
            self.models = []
            log.warning("Ollama package not installed; skipping Ollama models")
            return
        try:
            self.client = ollama.Client(Config().get_ollama_api_endpoint())
            self.models = self.client.list()["models"]
            log.info("Ollama available")
        except:
            self.client = None
            log.warning("Ollama not available")
            log.warning("run ollama server to use ollama models otherwise use API models")

    def inference(self, model_id: str, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("Ollama client not available")
        response = self.client.generate(
            model=model_id,
            prompt=prompt.strip(),
            options={"temperature": 0}
        )
        return response['response']
