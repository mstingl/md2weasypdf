FROM rust:1.90-alpine3.22 AS mmdr
RUN apk --no-cache add musl-dev
RUN cargo install mermaid-rs-renderer --version 0.3.1 --locked

FROM python:3.13-alpine3.22
RUN apk --no-cache add git pango fontconfig font-dejavu font-noto ttf-freefont terminus-font

COPY --from=mmdr /usr/local/cargo/bin/mmdr /usr/local/bin/mmdr

COPY ./ /md2weasypdf
RUN pip install --no-cache-dir /md2weasypdf
