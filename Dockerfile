FROM python:3.11-slim-buster

COPY . /app

WORKDIR /app

RUN python setup.py develop

ENTRYPOINT [ "forksearch" ]
