FROM python:3.12-slim as app

SHELL ["/bin/bash", "-c"]

RUN apt update

RUN apt-get install -y python3-pip

WORKDIR /opt/app

RUN python3 -m pip config set global.break-system-packages true && \
    pip3 install poetry==2.1.3 && \
    poetry config virtualenvs.create false

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-root

COPY . .
