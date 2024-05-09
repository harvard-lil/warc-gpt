import pytest
import tempfile
import shutil
from dotenv import find_dotenv, load_dotenv
from pathlib import Path
from warc_gpt import create_app


@pytest.fixture(scope='session', autouse=True)
def load_env():
    env_file = find_dotenv('tests/.test.env')
    load_dotenv(env_file)


@pytest.fixture()
def app():
    clean_test_directories()

    # move existing .env, if present; this is not the right way to
    # do this, I think
    dotenv = Path(".") / ".env"
    tempdir = Path(tempfile.mkdtemp())
    tempdotenv = tempdir / ".env"
    if dotenv.is_file():
        dotenv.rename(tempdotenv)

    app = create_app()

    yield app

    # clean up / reset resources here
    clean_test_directories()

    # replace existing .env
    if tempdotenv.is_file():
        tempdotenv.rename(dotenv)
    tempdir.rmdir()
        

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def clean_test_directories():
    for dir in ["chromadb", "visualizations"]:
        d = Path(".") / "tests" / "dir"
        if d.is_dir():
            shutil.rmtree(d)
    
