import os

from flask import current_app, jsonify, make_response

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_limiter():
    """
    Returns instance of the rate limiter.
    """
    return Limiter(
        get_remote_address,
        app=current_app,
        default_limits=["120 per hour"],
        storage_uri=os.environ["RATE_LIMIT_STORAGE_URI"],
        strategy="moving-window",
    )
