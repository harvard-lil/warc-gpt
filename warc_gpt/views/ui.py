"""
`views.ui` module: UI routes controller.
"""
import os

from flask import current_app, render_template

from warc_gpt.utils import list_available_models


@current_app.route("/")
def get_root():
    available_models = list_available_models()
    return (
        render_template(
            "index.html",
            available_models=available_models,
            rag_prompt=os.environ["RAG_PROMPT"],
        ),
        200,
    )
