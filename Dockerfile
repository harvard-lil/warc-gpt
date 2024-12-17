# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.12.4
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Copy the source code into the container.
COPY . .

# Install poetry app
RUN pip install poetry
RUN poetry env use 3.12 && poetry install

# Run the application on localhost:5000
#CMD ["poetry", "run", "flask", "run"]

# Uncomment to run the application on 0.0.0.0:5000
CMD ["poetry", "run", "flask", "run", "--host", "0.0.0.0"]