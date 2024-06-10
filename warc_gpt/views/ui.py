import os
import json

from flask import current_app, render_template

from warc_gpt.utils import list_available_models


@current_app.route("/")
def get_root():
    """
    [GET] /
    Renders the app's UI.
    """
    available_models = list_available_models()
    default_model = ""

    # Pick a default model
    if "openai/gpt-4o" in available_models:
        default_model = "openai/gpt-4o"

    if not default_model:
        for model in available_models:
            if model.startswith(("ollama/mixtral", "ollama/mistral")):
                default_model = model
                break

    if not default_model and available_models:
        default_model = available_models[0]

    if not default_model:
        return (
            "ERROR: No models available. Check your environment configuration in your .env file.",
            500,
        )

    app_consts = {
        "available_models": available_models,
        "default_model": default_model,
        "text_completion_base_prompt": os.environ["TEXT_COMPLETION_BASE_PROMPT"],
        "text_completion_rag_prompt": os.environ["TEXT_COMPLETION_RAG_PROMPT"],
        "text_completion_history_prompt": os.environ["TEXT_COMPLETION_HISTORY_PROMPT"],
    }

    return (
        render_template(
            "index.html",
            app_consts=json.dumps(app_consts),
        ),
        200,
    )
