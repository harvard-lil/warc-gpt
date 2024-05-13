"""
`warc_gpt` module: REST API and CLI commands for the `warc-gpt` pipeline.
"""

import os

from dotenv import load_dotenv
from flask import Flask

from warc_gpt import utils

load_dotenv()

WARC_RECORD_DATA = {
    "warc_filename": "",
    "warc_record_id": "",
    "warc_record_date": None,
    "warc_record_target_uri": None,
    "warc_record_content_type": None,
    "warc_record_text": "",
}
""" Shape of the data we extract and store from WARC records. """


def create_app():
    """
    App factory (https://flask.palletsprojects.com/en/2.3.x/patterns/appfactories/)
    """
    app = Flask(__name__)

    # Note: Every module in this app assumes the app context is available and initialized.
    with app.app_context():
        utils.check_env()

        os.makedirs(os.environ["WARC_FOLDER_PATH"], exist_ok=True)
        os.makedirs(os.environ["VISUALIZATIONS_FOLDER_PATH"], exist_ok=True)
        os.makedirs(os.environ["VECTOR_SEARCH_PATH"], exist_ok=True)

        from warc_gpt import commands
        from warc_gpt import views

        return app
