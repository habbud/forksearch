FROM python:3.11-slim-buster

COPY . /.
COPY ./forksearch/. /.

WORKDIR /.

RUN python setup.py develop

ENTRYPOINT [ "forksearch" ]
