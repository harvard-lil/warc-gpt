"""
`commands.visualize` module: Controller for the `visualize` CLI command.
"""
import os
from textwrap import wrap

import click
import chromadb
import pandas as pd
from sklearn.manifold import TSNE
import plotly.express as px
from sentence_transformers import SentenceTransformer
from flask import current_app


@current_app.cli.command("visualize")
@click.option(
    "--questions",
    required=False,
    default="",
    type=str,
    help="Can be used to place questions on the plot, to visualize their nearest neighbors. Use ; as a separator.",  # noqa
)
@click.option(
    "--perplexity",
    default=30.0,
    type=float,
    help="TSNE default setting; reduce for small input sets.",
    show_default=True
)
def visualize(questions: str, perplexity: float) -> None:
    """
    Generates an interactive T-SNE 2D plot for the vector store created via the `ingest` command.

    See: options in .env.example
    """
    environ = os.environ

    normalize_embeddings = environ["VECTOR_SEARCH_NORMALIZE_EMBEDDINGS"] == "true"
    query_prefix = environ["VECTOR_SEARCH_QUERY_PREFIX"]

    output_filename = os.path.join(
        environ["VISUALIZATIONS_FOLDER_PATH"],
        environ["VECTOR_SEARCH_COLLECTION_NAME"] + ".html",
    )

    # Init embedding model
    embedding_model = SentenceTransformer(
        environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_MODEL"],
        device=environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_DEVICE"],
    )

    # Init vector store
    chroma_client = chromadb.PersistentClient(
        path=environ["VECTOR_SEARCH_PATH"],
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    chroma_collection = chroma_client.get_collection(name=environ["VECTOR_SEARCH_COLLECTION_NAME"])

    # Pull everything out of the vector store
    all_vectors = chroma_collection.get(include=["metadatas", "documents", "embeddings"])

    #
    # If a question was provided, generate embeddings for it so it can be placed on the plot
    #
    questions_embeddings = []

    if questions:
        questions_embeddings = embedding_model.encode(
            sentences=[f"{query_prefix}{question}" for question in questions.split(";")],
            normalize_embeddings=normalize_embeddings,
        ).tolist()

    #
    # Apply T-SNE dimensions reduction to all vectors
    #
    if questions_embeddings:
        scatter_plot_data = pd.DataFrame(all_vectors["embeddings"] + questions_embeddings)
    else:
        scatter_plot_data = pd.DataFrame(all_vectors["embeddings"])

    try:
        scatter_plot_data = TSNE(perplexity=perplexity).fit_transform(scatter_plot_data)
    except ValueError as e:
        if f'{e}' == "perplexity must be less than n_samples":
            click.echo("You may not have enough input data; add some or reduce perplexity to less than n_samples.")  # noqa
            return 1
        else:
            raise

    scatter_plot_data = pd.DataFrame(scatter_plot_data)
    scatter_plot_data = scatter_plot_data.rename(columns={0: "x", 1: "y"})

    #
    # Compile plot metadata
    #
    all_warcs = []
    all_record_dates = []
    all_record_ids = []
    all_urls = []
    all_texts = []

    # WARC record embeddings metadata
    for metadata in all_vectors["metadatas"]:
        all_warcs.append(metadata["warc_filename"])
        all_record_dates.append(metadata["warc_record_date"])
        all_record_ids.append(metadata["warc_record_id"])
        all_urls.append("<br>".join(wrap(metadata["warc_record_target_uri"], 60)))
        all_texts.append("<br>".join(wrap(metadata["warc_record_text"], 60)))

    # QUESTION embeddings metadata (if applicable)
    if questions_embeddings:
        for question in questions.split(";"):
            all_warcs.append("QUESTIONS")
            all_record_dates.append("")
            all_record_ids.append("")
            all_urls.append("")
            all_texts.append(question)

    scatter_plot_data = scatter_plot_data.assign(warc=all_warcs)
    scatter_plot_data = scatter_plot_data.assign(record_date=all_record_dates)
    scatter_plot_data = scatter_plot_data.assign(record_id=all_record_ids)
    scatter_plot_data = scatter_plot_data.assign(url=all_urls)
    scatter_plot_data = scatter_plot_data.assign(text=all_texts)

    #
    # Generate plot
    #
    plot_title = f"Web Archive Collection Embeddings ({len(all_vectors['embeddings'])}) "

    if questions_embeddings:
        plot_title += "+ Questions "

    plot_title += "- " + environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_MODEL"]

    plot = px.scatter(
        scatter_plot_data,
        x="x",
        y="y",
        color="warc",
        labels={"color": "warc"},
        hover_data=["url", "text", "record_id", "record_date"],
        title=plot_title,
    )

    plot.write_html(os.path.join(output_filename))

    click.echo(f"{output_filename} saved to disk.")
