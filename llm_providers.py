import json
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str) -> str:
        pass

    @abstractmethod
    def generate_response_sync(self, prompt: str) -> str:
        pass

    @abstractmethod
    def close(self):
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            import httpx
            self.client = httpx.Client(timeout=300.0)
        except ImportError:
            logger.warning("httpx not available. Ollama provider will use mock responses.")

    async def generate_response(self, prompt: str) -> str:
        if not self.client:
            return self._mock_response(prompt)
        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 2048,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return self._mock_response(prompt, error=str(e))

    def generate_response_sync(self, prompt: str) -> str:
        if not self.client:
            return self._mock_response(prompt)
        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 2048,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return self._mock_response(prompt, error=str(e))

    def _mock_response(self, prompt: str, error: str | None = None) -> str:
        content = (
            f"Error occurred: {error}"
            if error
            else "This is a mock response - httpx not available"
        )
        return json.dumps(
            {
                "original_prompt": prompt,
                "sub_prompts": [
                    {
                        "id": 1,
                        "content": content,
                        "opaque_values": {},
                        "suggested_tools": ["file-operations.read_file"],
                    }
                ],
            }
        )

    def close(self):
        if self.client:
            self.client.close()

class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-2.0-flash-exp", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self.GenerationConfig = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            logger.warning("No Gemini API key provided. Provider will use mock responses.")
            return
        try:
            from google.generativeai.client import configure
            from google.generativeai.generative_models import GenerativeModel
            from google.generativeai.types import GenerationConfig
            configure(api_key=self.api_key)
            self.client = GenerativeModel(self.model)
            self.GenerationConfig = GenerationConfig
            logger.info(f"Initialized Gemini client with model: {self.model}")
        except ImportError:
            logger.warning("google-generativeai not available. Gemini provider will use mock responses.")
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")

    async def generate_response(self, prompt: str) -> str:
        if not self.client or not self.api_key or not self.GenerationConfig:
            return self._mock_response(prompt)
        try:
            config = self.GenerationConfig(
                temperature=0.1,
                top_p=0.9,
                max_output_tokens=2048,
            )
            response = self.client.generate_content(
                prompt,
                generation_config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return self._mock_response(prompt, error=str(e))

    def generate_response_sync(self, prompt: str) -> str:
        if not self.client or not self.api_key or not self.GenerationConfig:
            return self._mock_response(prompt)
        try:
            config = self.GenerationConfig(
                temperature=0.1,
                top_p=0.9,
                max_output_tokens=2048,
            )
            response = self.client.generate_content(
                prompt,
                generation_config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return self._mock_response(prompt, error=str(e))

    def _mock_response(self, prompt: str, error: str | None = None) -> str:
        content = (
            f"Error occurred: {error}"
            if error
            else "This is a mock response - Gemini API not available"
        )
        return json.dumps(
            {
                "original_prompt": prompt,
                "sub_prompts": [
                    {
                        "id": 1,
                        "content": content,
                        "opaque_values": {},
                        "suggested_tools": ["file-operations.read_file"],
                    }
                ],
            }
        )

    def close(self):
        pass 