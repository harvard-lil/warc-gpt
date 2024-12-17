"""
`commands.ingest` module: Controller for the `ingest` CLI command.
"""

import os
import glob
import traceback
import io
from shutil import rmtree

import click
import chromadb
from bs4 import BeautifulSoup
from bs4 import Comment as HTMLComment
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from warcio.archiveiterator import ArchiveIterator
from langchain.text_splitter import SentenceTransformersTokenTextSplitter
from flask import current_app
from time import perf_counter
from statistics import mean

from warc_gpt import WARC_RECORD_DATA


@current_app.cli.command("ingest")
@click.option(
    "--batch-size",
    default=2,
    type=int,
    help="Batch size for encoding",
    show_default=True,
)
def ingest(batch_size) -> None:
    """
    Generates sentence embeddings and metadata for a set of WARCs and saves them in a vector store.

    See: options in .env.example
    """
    environ = os.environ

    chunk_prefix = environ["VECTOR_SEARCH_CHUNK_PREFIX"]

    warc_files = []
    embedding_model = None
    chroma_client = None
    chroma_collection = None
    total_records = 0
    total_embeddings = 0

    if batch_size == 1:
        multi_chunk_mode = False
    elif batch_size > 1:
        multi_chunk_mode = True
    else:
        raise click.UsageError("Batch size must be a positive integer, preferably a power of 2")
    encoding_timings = []

    # Cleanup
    rmtree(environ["VECTOR_SEARCH_PATH"], ignore_errors=True)
    os.makedirs(environ["VECTOR_SEARCH_PATH"], exist_ok=True)

    # List WARC files to process
    warc_files += glob.glob(environ["WARC_FOLDER_PATH"] + "/*.warc", recursive=True)
    warc_files += glob.glob(environ["WARC_FOLDER_PATH"] + "/*.warc.gz", recursive=True)
    warc_files.sort()

    if not warc_files:
        click.echo("No WARC files to ingest.")
        exit(1)

    click.echo(f"{len(warc_files)} WARC files to ingest.")

    # Init embedding model
    embedding_model = SentenceTransformer(
        environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_MODEL"],
        device=environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_DEVICE"],
    )

    # Init text splitter function
    text_splitter = SentenceTransformersTokenTextSplitter(
        model_name=environ["VECTOR_SEARCH_SENTENCE_TRANSFORMER_MODEL"],
        chunk_overlap=int(environ["VECTOR_SEARCH_TEXT_SPLITTER_CHUNK_OVERLAP"]),
        tokens_per_chunk=embedding_model[0].max_seq_length,
    )  # Note: The text splitter adjusts its cut-off based on the models' max_seq_length

    # Init vector store
    chroma_client = chromadb.PersistentClient(
        path=environ["VECTOR_SEARCH_PATH"],
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    chroma_collection = chroma_client.create_collection(
        name=environ["VECTOR_SEARCH_COLLECTION_NAME"],
        metadata={"hnsw:space": environ["VECTOR_SEARCH_DISTANCE_FUNCTION"]},
    )

    #
    # For each WARC:
    # - Extract text from text/html and application/pdf records
    # - Split and generate embeddings for said text
    # - Save in vector store
    #
    for warc_file in warc_files:
        click.echo(f"🗜️ Ingesting HTML and PDF records from {warc_file}")

        with open(warc_file, "rb") as stream:
            for record in ArchiveIterator(stream):
                record_data = dict(WARC_RECORD_DATA)

                if record.rec_type != "response":
                    continue

                # Extract metadata
                rec_headers = record.rec_headers
                http_headers = record.http_headers

                if not rec_headers or not http_headers:
                    continue

                record_data["warc_filename"] = os.path.basename(warc_file)
                record_data["warc_record_id"] = rec_headers.get_header("WARC-Record-ID")
                record_data["warc_record_date"] = rec_headers.get_header("WARC-Date")
                record_data["warc_record_target_uri"] = rec_headers.get_header("WARC-Target-URI")
                record_data["warc_record_content_type"] = http_headers.get_header("Content-Type")
                record_data["warc_record_text"] = ""

                # Skip incomplete records
                if (
                    not record_data["warc_record_id"]
                    or not record_data["warc_record_date"]
                    or not record_data["warc_record_target_uri"]
                    or not record_data["warc_record_content_type"]
                ):
                    continue

                # Skip records that are not HTTP 2XX
                if http_headers.get_statuscode().startswith("2") is not True:
                    continue

                #
                # Extract text from text/html
                #
                if record_data["warc_record_content_type"].startswith("text/html"):
                    try:
                        response_as_text = record.content_stream().read().decode("utf-8")

                        soup = BeautifulSoup(response_as_text, "html.parser")

                        # Skip documents with no body tag
                        if not soup.body or len(soup.body) < 1:
                            continue

                        all_text = soup.body.findAll(string=True)

                        for text in all_text:
                            if text.parent.name in ["script", "style"]:  # No <script> or <style>
                                continue

                            if isinstance(text, HTMLComment):  # No HTML comments
                                continue

                            record_data["warc_record_text"] += f"{text} "

                        record_data["warc_record_text"] = record_data["warc_record_text"].strip()
                    except Exception:
                        click.echo(
                            f"- Could not extract text from {record_data['warc_record_target_uri']}"
                        )
                        click.echo(traceback.format_exc())

                #
                # Extract text from PDF
                #
                if record_data["warc_record_content_type"].startswith("application/pdf"):
                    raw = io.BytesIO(record.raw_stream.read())
                    try:
                        pdf = PdfReader(raw)
                        for page in pdf.pages:
                            record_data["warc_record_text"] += page.extract_text()
                    except Exception as exc:
                        print(f"- Could not extract text from {record_data['warc_record_target_uri']}")
                        continue

                #
                # Stop here if we don't have text, or text contains less than 5 words
                #
                if not record_data["warc_record_text"]:
                    continue

                if len(record_data["warc_record_text"].split()) < 5:
                    continue

                record_data["warc_record_text"] = record_data["warc_record_text"].strip()
                total_records += 1

                # Split text into chunks
                text_chunks = text_splitter.split_text(record_data["warc_record_text"])
                click.echo(f"{record_data['warc_record_target_uri']} = {len(text_chunks)} chunks.")

                if not text_chunks:
                    continue

                # Add VECTOR_SEARCH_CHUNK_PREFIX to every chunk
                text_chunks = [chunk_prefix + chunk for chunk in text_chunks]

                # Generate embeddings and metadata for each chunk
                (
                    documents,
                    ids,
                    metadatas,
                    embeddings,
                    multi_chunk_mode,
                    encoding_timings
                ) = chunk_objects(
                    record_data,
                    text_chunks,
                    embedding_model,
                    multi_chunk_mode,
                    encoding_timings,
                    batch_size
                )
                total_embeddings += len(embeddings)

                # Store embeddings and metadata
                chroma_collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )

    click.echo(f"Total: {total_embeddings} embeddings from {total_records} HTML/PDF records.")


def chunk_objects(
    record_data: dict,
    text_chunks: list[str],
    embedding_model: SentenceTransformer,
    multi_chunk_mode: bool,
    encoding_timings: list[float],
    batch_size: int
):
    """
    Return one document, metadata, id, and embedding object per chunk; also return
    control variables multi_chunk_mode and encoding_timings

    """
    environ = os.environ
    normalize_embeddings = environ["VECTOR_SEARCH_NORMALIZE_EMBEDDINGS"] == "true"
    chunk_prefix = environ["VECTOR_SEARCH_CHUNK_PREFIX"]

    chunk_range = range(len(text_chunks))

    documents = [record_data["warc_filename"] for _ in chunk_range]

    ids = [f"{record_data['warc_record_id']}-{i+1}" for i in chunk_range]

    metadatas = [
        dict(record_data, **{"warc_record_text": text_chunks[i][len(chunk_prefix):]})
        for i in chunk_range
    ]

    # In some contexts, passing all the text chunks to embedding_model.encode() at once
    # takes advantage of parallelization, so we default to that, but stop doing it if
    # it is too slow.
    if multi_chunk_mode:
        start = perf_counter()
        embeddings = embedding_model.encode(
            text_chunks,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
        ).tolist()
        encoding_time = perf_counter() - start

        if len(text_chunks) == 1:
            encoding_timings.append(encoding_time)
        else:
            if len(encoding_timings) == 0:
                pass
            elif encoding_time > len(text_chunks) * mean(encoding_timings):
                multi_chunk_mode = False
                click.echo("Leaving multi-chunk mode")
    else:
        # we've left multi-chunk mode, and there's no need to capture timings anymore
        embeddings = [
            embedding_model.encode(
                [chunk],
                batch_size=1,
                normalize_embeddings=normalize_embeddings,
            ).tolist()[0]
            for chunk in text_chunks
        ]

    return documents, ids, metadatas, embeddings, multi_chunk_mode, encoding_timings
