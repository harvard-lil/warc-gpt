""" WSGI hook """

from warc_gpt import create_app

if __name__ == "__main__":
    create_app().run()
