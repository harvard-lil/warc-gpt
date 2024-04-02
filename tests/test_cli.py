import pytest
import os
from pathlib import Path


def test_ingest(runner):
    db = Path(os.environ["VECTOR_SEARCH_PATH"]) / "chroma.sqlite3"
    collections = Path(os.environ["VISUALIZATIONS_FOLDER_PATH"]) / "collection.html"

    assert os.environ["VISUALIZATIONS_FOLDER_PATH"] == "./tests/visualizations"
    
    os.environ["WARC_FOLDER_PATH"] = "./tests/no_such_folder"
    result = runner.invoke(args="ingest")
    assert result.exit_code == 1
    assert "No WARC files to ingest." in result.output
    assert not db.is_file()
        
    os.environ["WARC_FOLDER_PATH"] = "./tests/warc"
    result = runner.invoke(args="ingest")
    assert result.exit_code == 0
    assert "2 WARC files to ingest." in result.output
    assert db.is_file()

    result = runner.invoke(args="visualize")
    assert "You may not have enough input data" in result.output
    assert result.exit_code == 1
    
    result = runner.invoke(args=["visualize", "--perplexity", "2"])
    assert "./tests/visualizations/collection.html saved to disk." in result.output
    assert result.exit_code == 0
    assert collections.is_file()
