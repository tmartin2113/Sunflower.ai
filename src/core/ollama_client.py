import requests
import json
import logging

from src.utils.exceptions import OllamaConnectionError

logger = logging.getLogger(__name__)

class OllamaClient:
    """
    A client for interacting with the Ollama API.

    This class provides methods to send requests to the Ollama server,
    specifically for handling chat completions and managing models.
    It supports streaming responses to allow for real-time interaction.
    """

    def __init__(self, host='127.0.0.1', port=11434):
        """
        Initializes the OllamaClient.

        Args:
            host (str): The hostname or IP address of the Ollama server.
            port (int): The port number for the Ollama server.
        """
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        logger.info(f"Ollama client initialized for endpoint: {self.base_url}")

    def _get_endpoint(self, path):
        """Constructs the full API endpoint URL."""
        return f"{self.base_url}{path}"

    def stream_chat(self, model_name, messages):
        """
        Sends a chat request to the Ollama API and streams the response.

        Args:
            model_name (str): The name of the model to use for the chat.
            messages (list): A list of message dictionaries, following the
                             Ollama API format.

        Yields:
            dict: A dictionary representing a single JSON object from the
                  streaming response.

        Raises:
            OllamaConnectionError: If there is a problem connecting to the
                                   Ollama server.
        """
        endpoint = self._get_endpoint("/api/chat")
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True
        }

        try:
            logger.debug(f"Streaming chat with model '{model_name}'")
            with self.session.post(endpoint, json=payload, stream=True, timeout=120) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            yield chunk
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode JSON chunk: {line}")
                            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {e}")
            raise OllamaConnectionError(f"Failed to connect to Ollama at {self.base_url}. Is the service running?") from e

    def close(self):
        """Closes the underlying requests session."""
        self.session.close()
        logger.info("Ollama client session closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
