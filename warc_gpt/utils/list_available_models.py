"""
`utils.list_available_models` module: Checks what models LiteLLM has access to.
"""
import os

import litellm
import requests


litellm.telemetry = False


def list_available_models() -> list:
    """
    Returns a list of the models LiteLLM can talk to based on current environment.
    More info:
    - https://docs.litellm.ai/docs/
    - https://github.com/jmorganca/ollama/blob/main/docs/api.md#list-local-models
    """
    models = []

    if os.environ.get("OPENAI_API_KEY"):
        for model in litellm.open_ai_chat_completion_models:
            if model.startswith("gpt"):
                models.append(model)

    if os.environ.get("ANTHROPIC_API_KEY"):
        for model in litellm.anthropic_models:
            models.append(model)

    if os.environ.get("COHERE_API_KEY"):
        for model in litellm.cohere_models:
            models.append(model)

    if os.environ.get("PERPLEXITYAI_API_KEY"):
        for model in litellm.perplexity_models:
            models.append(model)

    # List models available at Ollama endpoint if provided
    try:
        ollama_api_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11343")
        response = requests.get(f"{ollama_api_url}/api/tags", timeout=1).json()

        for model in response["models"]:
            models.append(f"ollama/{model['name']}")
    except Exception:
        pass

    return models
