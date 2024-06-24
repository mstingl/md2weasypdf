FROM python:3.12.4-alpine3.20
RUN apk --update --upgrade --no-cache add git py3-pip gcc musl-dev python3-dev pango zlib-dev jpeg-dev openjpeg-dev g++ libffi-dev fontconfig ttf-freefont font-noto terminus-font

COPY ./ /md2weasypdf
RUN pip install /md2weasypdf
