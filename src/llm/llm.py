import sys

import tiktoken
from typing import List, Tuple

from src.socket_instance import emit_agent
from .ollama_client import Ollama
from .claude_client import Claude
from .openai_client import OpenAi
from .gemini_client import Gemini
from .mistral_client import MistralAi
from .groq_client import Groq
from .lm_studio_client import LMStudio

from src.state import AgentState

from src.config import Config
from src.logger import Logger

TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")

ollama = None
logger = Logger()
agentState = AgentState()
config = Config()


def _is_configured_key(value: str) -> bool:
    if not value:
        return False
    val = str(value).strip()
    if not val:
        return False
    # Ignore sample placeholders like <YOUR_OPENAI_API_KEY>
    return not (val.startswith("<") and val.endswith(">"))


class LLM:
    def __init__(self, model_id: str = None):
        self.model_id = model_id
        self.log_prompts = config.get_logging_prompts()
        self.timeout_inference = config.get_timeout_inference()
        self.models = {}

        groq_only_mode = _is_configured_key(config.get_groq_api_key())
        if groq_only_mode:
            # User-requested behavior: route exclusively to Groq cloud models.
            self.models["CLAUDE"] = []
            self.models["GROQ"] = [
                ("Llama 3.3 70B", "llama-3.3-70b-versatile"),
                ("Llama 3.1 8B", "llama-3.1-8b-instant"),
                ("Qwen3 32B", "qwen/qwen3-32b"),
                ("Llama 4 Scout", "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("GPT OSS 120B", "openai/gpt-oss-120b"),
                ("GPT OSS 20B", "openai/gpt-oss-20b"),
            ]
            return

        self.models = {
            "OLLAMA": [],
            "LM_STUDIO": [
                ("LM Studio", "local-model"),
            ],
        }

        if _is_configured_key(config.get_claude_api_key()):
            self.models["CLAUDE"] = [
                ("Claude 3.7 Sonnet", "claude-3-7-sonnet-20250219"),
                ("Claude 3.5 Sonnet", "claude-3-5-sonnet-20241022"),
                ("Claude 3.5 Haiku", "claude-3-5-haiku-20241022"),
            ]

        if _is_configured_key(config.get_openai_api_key()):
            self.models["OPENAI"] = [
                ("GPT-4o-mini", "gpt-4o-mini"),
                ("GPT-4o", "gpt-4o"),
                ("GPT-4 Turbo", "gpt-4-turbo"),
                ("GPT-3.5 Turbo", "gpt-3.5-turbo-0125"),
            ]

        if _is_configured_key(config.get_gemini_api_key()):
            self.models["GOOGLE"] = [
                ("Gemini 1.0 Pro", "gemini-pro"),
                ("Gemini 1.5 Flash", "gemini-1.5-flash"),
                ("Gemini 1.5 Pro", "gemini-1.5-pro"),
                ("Gemini 2.5 Flash", "gemini-2.5-flash"),
                ("Gemini 2.5 Pro", "gemini-2.5-pro"),
            ]

        if _is_configured_key(config.get_mistral_api_key()):
            self.models["MISTRAL"] = [
                ("Mistral 7b", "open-mistral-7b"),
                ("Mistral 8x7b", "open-mixtral-8x7b"),
                ("Mistral Medium", "mistral-medium-latest"),
                ("Mistral Small", "mistral-small-latest"),
                ("Mistral Large", "mistral-large-latest"),
            ]

        if _is_configured_key(config.get_groq_api_key()):
            self.models["GROQ"] = [
                ("LLAMA3 8B", "llama3-8b-8192"),
                ("LLAMA3 70B", "llama3-70b-8192"),
                ("LLAMA2 70B", "llama2-70b-4096"),
                ("Mixtral", "mixtral-8x7b-32768"),
                ("GEMMA 7B", "gemma-7b-it"),
            ]

        global ollama
        if ollama is None:
            ollama = Ollama()

        if ollama.client:
            ollama_models = []
            for model in ollama.models:
                model_name = getattr(model, "name", None) or getattr(model, "model", None)
                if not model_name:
                    try:
                        model_name = model.get("name") or model.get("model")
                    except Exception:
                        model_name = None
                if model_name:
                    ollama_models.append((model_name, model_name))
            self.models["OLLAMA"] = ollama_models

    def list_models(self) -> dict:
        return self.models

    def model_enum(self, model_name: str) -> Tuple[str, str]:
        model_dict = {
            model[0]: (model_enum, model[1]) 
            for model_enum, models in self.models.items() 
            for model in models
        }
        if model_name in model_dict:
            return model_dict[model_name]

        legacy_name_map = {
            "Claude 3 Opus": "Claude 3.5 Sonnet",
            "Claude 3 Sonnet": "Claude 3.5 Sonnet",
            "Claude 3 Haiku": "Claude 3.5 Haiku",
            "LLAMA3 8B": "Llama 3.1 8B",
            "LLAMA3 70B": "Llama 3.3 70B",
            "LLAMA2 70B": "Llama 3.3 70B",
            "Mixtral": "Llama 3.3 70B",
            "GEMMA 7B": "Llama 3.1 8B",
            "qwen3.5:9b": "Qwen3 32B",
            "LM Studio": "Llama 3.3 70B",
        }
        mapped_name = legacy_name_map.get(model_name)
        if mapped_name:
            return model_dict.get(mapped_name, (None, None))

        return (None, None)

    @staticmethod
    def update_global_token_usage(string: str, project_name: str):
        token_usage = len(TIKTOKEN_ENC.encode(string))
        agentState.update_token_usage(project_name, token_usage)

        total = agentState.get_latest_token_usage(project_name) + token_usage
        emit_agent("tokens", {"token_usage": total})

    def inference(self, prompt: str, project_name: str) -> str:
        self.update_global_token_usage(prompt, project_name)

        model_enum, model_name = self.model_enum(self.model_id)
                
        print(f"Model: {self.model_id}, Enum: {model_enum}")
        if model_enum is None:
            raise ValueError(f"Model {self.model_id} not supported")

        def _get_ollama():
            global ollama
            if ollama is None:
                ollama = Ollama()
            return ollama

        model_builders = {
            "OLLAMA": _get_ollama,
            "CLAUDE": Claude,
            "OPENAI": OpenAi,
            "GOOGLE": Gemini,
            "MISTRAL": MistralAi,
            "GROQ": Groq,
            "LM_STUDIO": LMStudio,
        }

        try:
            import concurrent.futures
            import time

            start_time = time.time()
            model = model_builders[model_enum]()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(model.inference, model_name, prompt)
                try:
                    while True:
                        elapsed_time = time.time() - start_time
                        elapsed_seconds = format(elapsed_time, ".2f")
                        emit_agent("inference", {"type": "time", "elapsed_time": elapsed_seconds})
                        if int(elapsed_time) == 5:
                            emit_agent("inference", {"type": "warning", "message": "Inference is taking longer than expected"})
                        if elapsed_time > self.timeout_inference:
                            raise concurrent.futures.TimeoutError
                        if future.done():
                            break
                        time.sleep(0.5)

                    response = future.result(timeout=self.timeout_inference).strip()

                except concurrent.futures.TimeoutError:
                    logger.error(f"Inference failed. took too long. Model: {model_enum}, Model ID: {self.model_id}")
                    emit_agent("inference", {"type": "error", "message": "Inference took too long. Please try again."})
                    response = False
                    sys.exit()
                
                except Exception as e:
                    logger.error(str(e))
                    response = False
                    emit_agent("inference", {"type": "error", "message": str(e)})
                    sys.exit()


        except KeyError:
            raise ValueError(f"Model {model_enum} not supported")

        if self.log_prompts:
            logger.debug(f"Response ({model}): --> {response}")

        self.update_global_token_usage(response, project_name)

        return response
