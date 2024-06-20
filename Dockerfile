FROM python:3.12.4-alpine3.20
RUN apk add git py3-pip gcc musl-dev python3-dev pango zlib-dev jpeg-dev openjpeg-dev g++ libffi-dev
COPY ./ /md2weasypdf
RUN pip install /md2weasypdf
