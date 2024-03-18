import os
import traceback

from flask import current_app
from openai import OpenAI
import ollama


def list_available_models() -> list:
    """
    Returns a list of the models the pipeline can talk to based on current environment.
    """
    models = []

    # Use case: Using OpenAI's client to interact with a non-OpenAI provider.
    # In that case, the model's name is provided via the environment.
    if os.environ.get("OPENAI_BASE_URL") and os.environ.get("OPENAI_COMPATIBLE_MODEL"):
        models.append(os.environ.get("OPENAI_COMPATIBLE_MODEL"))

    # Use case: OpenAI
    if os.environ.get("OPENAI_API_KEY") and not os.environ.get("OPENAI_BASE_URL"):
        try:
            openai_client = OpenAI()

            for model in openai_client.models.list().data:
                if model.id.startswith("gpt-4"):
                    models.append(f"openai/{model.id}")

        except Exception:
            current_app.logger.error("Could not list OpenAI models.")
            current_app.logger.error(traceback.format_exc())

    # Use case: Ollama
    if os.environ.get("OLLAMA_API_URL"):
        try:
            ollama_client = ollama.Client(
                host=os.environ["OLLAMA_API_URL"],
                timeout=5,
            )

            for model in ollama_client.list()["models"]:
                models.append(f"ollama/{model['name']}")

        except Exception:
            current_app.logger.error("Could not list Ollama models.")
            current_app.logger.error(traceback.format_exc())

    return models
