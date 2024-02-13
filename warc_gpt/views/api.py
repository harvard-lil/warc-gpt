"""
`views.api` module: API routes controller.
"""

import os
import traceback
import uuid

import chromadb
import litellm
from sentence_transformers import SentenceTransformer
from flask import current_app, jsonify, request, g

from warc_gpt.utils import list_available_models

litellm.telemetry = False

vector_store_cache = {
    "chroma_client": None,
    "embedding_model": None,
    "chroma_collection": None,
}
""" Module-level "caching" for vector store connection. """


@current_app.route("/api/models")
def get_models():
    return jsonify(list_available_models()), 200


@current_app.route("/api/completion", methods=["POST"])
def post_completion():
    """
    [POST] /api/completion

    Accepts JSON body with the following properties:
    - "model": One of the models /api/models lists (required)
    - "message": User prompt (required)
    - "temperature": Defaults to 0.0
    - "max_tokens": If provided, caps number of tokens that will be generated in response.
    - "no_rag": If set and true, the API will not try to retrieve context.
    - "history": A list of chat completion objects representing the chat history. Each object must contain "user" and "content".
    - "rag_prompt_override": If provided, will be used in replacement of the predefined RAG prompt. {context} and {question} placeholders will be automatically replaced.

    Example of a "history" list:
    ```
    [
        {"role": "user", "content": "Foo bar"},
        {"role": "assistant", "content": "Bar baz"}
    ]
    ```
    """
    environ = os.environ

    chroma_client = None
    chroma_collection = None
    embedding_model = None

    available_models = list_available_models()

    input = request.get_json()
    model = None
    message = None
    temperature = 0.0
    max_tokens = None
    no_rag = False
    rag_prompt_override = None

    vector_search_results = None
    prompt = ""
    context = ""

    history = []  # List of chat completion objects keeping track of exchanges (no RAG context)
    messages = []  # List of chat completion objects sent to LLM - last "user" entry has RAG context

    normalize_embeddings = environ["VECTOR_SEARCH_NORMALIZE_EMBEDDINGS"] == "true"
    query_prefix = environ["VECTOR_SEARCH_QUERY_PREFIX"]

    #
    # Check that "model" was provided and is available
    #
    if "model" not in input:
        return jsonify({"error": "No model provided."}), 400

    if input["model"] not in available_models:
        return jsonify({"error": "Requested model is invalid or not available."}), 400

    model = input["model"]

    #
    # Check that "message" was provided
    #
    if "message" not in input:
        return jsonify({"error": "No message provided."}), 400

    message = str(input["message"]).strip()

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    #
    # Validate "temperature" if provided
    #
    if "temperature" in input:
        try:
            temperature = float(input["temperature"])
            assert temperature >= 0.0
        except Exception:
            return (
                jsonify({"error": "temperature must be a float superior or equal to 0.0."}),
                400,
            )

    #
    # Validate "max_tokens" if provided
    #
    if "max_tokens" in input:
        try:
            max_tokens = int(input["max_tokens"])
            assert max_tokens > 0
        except Exception:
            return (jsonify({"error": "max_tokens must be an int superior to 0."}), 400)

    #
    # Validate "no_rag" if provided
    #
    if "no_rag" in input:
        try:
            assert isinstance(input["no_rag"], bool)
            no_rag = input["no_rag"]
        except Exception:
            current_app.logger.warn("no_rag parameter was passed but ignored as invalid.")

    #
    # Validate "rag_prompt_override" if provided
    #
    if "rag_prompt_override" in input:
        try:
            assert isinstance(input["rag_prompt_override"], str)
            rag_prompt_override = str(input["rag_prompt_override"]).strip()
        except Exception:
            current_app.logger.warn(
                "rag_prompt_override parameter was passed but ignored as invalid."
            )

    #
    # Validate "history" if provided
    #
    if "history" in input:
        try:
            for past_message in input["history"]:
                assert past_message["role"]
                assert past_message["content"]
                history.append(past_message)

        except Exception:
            return (
                jsonify({"error": "past_messages must be an array of chat completion objects."}),
                400,
            )

    #
    # Load vector store (from "cache" if available)
    #
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
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load embedding model."}), 500

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
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load ChromaDB client."}), 500

    try:
        if vector_store_cache.get("chroma_collection", None) is None:
            chroma_collection = chroma_client.get_collection(
                name=os.environ["VECTOR_SEARCH_COLLECTION_NAME"],
            )
            vector_store_cache["chroma_collection"] = chroma_collection
        else:
            chroma_collection = vector_store_cache["chroma_collection"]

        assert chroma_collection
    except Exception:
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not load ChromaDB collection."}), 500

    #
    # Retrieve context - unless in no_rag mode
    #

    # Retrieve context chunks
    try:
        assert not no_rag

        message_embedding = embedding_model.encode(
            sentences=f"{query_prefix}{message}",
            normalize_embeddings=normalize_embeddings,
        ).tolist()

        vector_search_results = chroma_collection.query(
            query_embeddings=message_embedding,
            n_results=int(environ["VECTOR_SEARCH_SEARCH_N_RESULTS"]),
        )
    except AssertionError:
        pass  # no_rag mode
    except Exception:
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not retrieve context from vector store."}), 500

    #
    # Prepare prompt
    #

    # Prepare text version of context that was retrieved
    if vector_search_results:
        for vector in vector_search_results["metadatas"][0]:
            warc = vector["warc_filename"]
            uri = vector["warc_record_target_uri"]
            date = vector["warc_record_date"]
            text = vector["warc_record_text"]

            context += f"Excerpt from web content {uri} captured on {date} as part of the web archive saved in {warc}:\n{text}\n\n"  # noqa

    if no_rag:
        prompt = message
    else:
        prompt = rag_prompt_override if rag_prompt_override else environ["RAG_PROMPT"]
        prompt = prompt.replace("{context}", context)
        prompt = prompt.replace("{question}", message)
        prompt = prompt.strip()

    #
    # Query LLM
    #
    try:
        messages = list(history)
        messages.append({"content": prompt, "role": "user"})

        # Try adjust messages list to context length (buggy)
        try:
            new_messages = litellm.utils.trim_messages(messages, model=model)
            assert new_messages
            messages = new_messages
        except Exception:
            current_app.logger.warn(f"litellm could not trim messages for {model}")

        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_base=os.environ["OLLAMA_API_URL"] if model.startswith("ollama") else None,
        )

        history.append({"content": message, "role": "user"})

        history.append(
            {
                "content": response["choices"][0]["message"]["content"],
                "role": "assistant",
            }
        )

        output = {
            "id_exchange": str(uuid.uuid4()),
            "response": response["choices"][0]["message"]["content"],
            "request_info": {
                "model": model,
                "message": message,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "no_rag": no_rag,
                "message_plus_prompt": prompt,
            },
            "response_info": {
                "prompt_tokens": response["usage"]["prompt_tokens"],
                "completion_tokens": response["usage"]["completion_tokens"],
                "total_tokens": response["usage"]["total_tokens"],
            },
            "context": vector_search_results["metadatas"][0] if vector_search_results else [],
            "history": history,
        }

        return (jsonify(output), 200)
    except Exception:
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Could not query LLM."}), 500
