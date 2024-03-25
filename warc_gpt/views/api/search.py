import os
import traceback

import chromadb
from sentence_transformers import SentenceTransformer
from flask import current_app, jsonify, request

from warc_gpt import WARC_RECORD_DATA
from warc_gpt.utils import get_limiter

API_SEARCH_RATE_LIMIT = os.environ["API_SEARCH_RATE_LIMIT"]

vector_store_cache = {
    "chroma_client": None,
    "embedding_model": None,
    "chroma_collection": None,
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
    environ = os.environ

    chroma_client = None
    chroma_collection = None
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
        if vector_store_cache.get("chroma_client", None) is None:
            chroma_client = chromadb.PersistentClient(
                path=environ["VECTOR_SEARCH_PATH"],
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            vector_store_cache["chroma_client"] = chroma_client
        else:
            chroma_client = vector_store_cache["chroma_client"]

        assert chroma_client
    except Exception:
        current_app.logger.debug(traceback.format_exc())
        return jsonify({"error": "Could not load ChromaDB client."}), 500

    # Chroma collection
    try:
        if vector_store_cache.get("chroma_collection", None) is None:
            chroma_collection = chroma_client.get_collection(
                name=environ["VECTOR_SEARCH_COLLECTION_NAME"],
            )
            vector_store_cache["chroma_collection"] = chroma_collection
        else:
            chroma_collection = vector_store_cache["chroma_collection"]

        assert chroma_collection
    except Exception:
        current_app.logger.debug(traceback.format_exc())
        return jsonify({"error": "Could not load ChromaDB collection."}), 500

    #
    # Retrieve context chunks
    #
    try:
        message_embedding = embedding_model.encode(
            sentences=f"{query_prefix}{message}",
            normalize_embeddings=normalize_embeddings,
        ).tolist()

        vector_search_results = chroma_collection.query(
            query_embeddings=message_embedding,
            n_results=int(environ["VECTOR_SEARCH_SEARCH_N_RESULTS"]),
        )
    except Exception:
        current_app.logger.debug(traceback.format_exc())
        return jsonify({"error": "Could not retrieve context from vector store."}), 500

    #
    # Filter and return metadata
    #
    if vector_search_results:
        for vector in vector_search_results["metadatas"][0]:
            metadata = {}

            for key in WARC_RECORD_DATA.keys():
                metadata[key] = vector.get(key, None)

            filtered_output.append(metadata)

    return (jsonify(filtered_output), 200)
