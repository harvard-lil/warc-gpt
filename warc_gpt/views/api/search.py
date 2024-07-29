import os
from os import environ
import traceback

from sentence_transformers import SentenceTransformer
from flask import current_app, jsonify, request

from warc_gpt import WARC_RECORD_DATA
from warc_gpt.utils import get_limiter
from warc_gpt.utils.vector_storage import VectorStorage

API_SEARCH_RATE_LIMIT = os.environ["API_SEARCH_RATE_LIMIT"]

vector_store_cache = {
    "vector_storage": None,
    "embedding_model": None,
}
""" Module-level "caching" for vector store connection. """


@current_app.route("/api/search", methods=["POST"])
@get_limiter().limit(API_SEARCH_RATE_LIMIT)
def post_search():
    """
    [POST] /api/search

    Accepts JSON body with the following properties:
    - "message": User prompt (required)

    Returns a JSON object of WARC_RECORD_DATA entries.
    """

    vector_storage = None
    embedding_model = None

    input = request.get_json()
    message = None

    normalize_embeddings = environ["VECTOR_SEARCH_NORMALIZE_EMBEDDINGS"] == "true"
    query_prefix = environ["VECTOR_SEARCH_QUERY_PREFIX"]

    vector_search_results = None
    filtered_output = []

    #
    # Check that "message" was provided
    #
    if "message" not in input:
        return jsonify({"error": "No message provided."}), 400

    message = str(input["message"]).strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    #
    # Load vector store (from "cache" if available)
    #
    # Embedding model
    try:
        if vector_store_cache.get("embedding_model", None) is None:
            embedding_model = SentenceTransformer(
                model_name_or_path=environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_MODEL"],
                device=environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_DEVICE"],
            )
            vector_store_cache["embedding_model"] = embedding_model
        else:
            embedding_model = vector_store_cache["embedding_model"]

        assert embedding_model
    except Exception:
        current_app.logger.debug(traceback.format_exc())
        return jsonify({"error": "Could not load embedding model."}), 500

    # Chroma client
    try:
        if vector_store_cache.get("vector_storage", None) is None:
            vector_storage = VectorStorage.make_storage(environ["VECTOR_SEARCH_DATABASE"])
            vector_store_cache["vector_storage"] = vector_storage
        else:
            vector_storage = vector_store_cache["vector_storage"]

        assert vector_storage
    except Exception:
        current_app.logger.debug(traceback.format_exc())
        return jsonify({"error": "Could not load vector storage."}), 500

    #
    # Retrieve context chunks
    #
    try:
        message_embedding = embedding_model.encode(
            sentences=f"{query_prefix}{message}",
            normalize_embeddings=normalize_embeddings,
        ).tolist()

        vector_search_results = vector_storage.search(
            query_embedding=message_embedding,
            limit=int(environ["VECTOR_SEARCH_SEARCH_N_RESULTS"]),
        )

    except Exception:
        current_app.logger.debug(traceback.format_exc())
        return jsonify({"error": "Could not retrieve context from vector store."}), 500
    #
    # Filter and return metadata
    #
    if vector_search_results:
        for vector in vector_search_results["metadatas"]:
            metadata = {}

            for key in WARC_RECORD_DATA.keys():
                metadata[key] = vector.get(key, None)

            filtered_output.append(metadata)

    return (jsonify(filtered_output), 200)
