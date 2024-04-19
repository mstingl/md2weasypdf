import os
import re
import warnings
from datetime import date
from functools import cache
from glob import iglob
from pathlib import Path
from subprocess import check_output
from typing import NamedTuple, Optional

import frontmatter
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import Markdown
from markdown_grid_tables import GridTableExtension
from weasyprint import HTML

from . import extensions


class Document(NamedTuple):
    filename: str
    title: str
    content: str
    meta: dict[str, object]
    has_custom_headline: bool
    hash: str


class Printer:
    @staticmethod
    def _ensure_path(path: Path):
        if not path.is_absolute():
            path = Path(os.path.join(os.getcwd(), path))

        if not path.exists():
            raise FileNotFoundError("Path does not exist")

        return path

    def __init__(
        self,
        input: Path,
        output_dir: Path,
        layouts_dir: Path = Path("layouts"),
        bundle: bool = False,
        title: Optional[str] = None,
        layout: Optional[str] = None,
        output_html: bool = False,
        filename_filter: Optional[str] = None,
    ):
        self.input = self._ensure_path(input)
        self.output_dir = self._ensure_path(output_dir)
        self.layouts_dir = self._ensure_path(layouts_dir)
        self.bundle = bundle
        self.title = title
        self.layout = layout
        self.output_html = output_html
        self.filename_filter = re.compile(filename_filter) if filename_filter else None
        self.jinja_env = Environment(
            autoescape=select_autoescape(),
            loader=FileSystemLoader(searchpath=[self.layouts_dir]),
        )

        if self.bundle:
            if not self.layout or not self.title:
                raise ValueError("A layout and title must be specified when using bundle.")

            if not os.path.isdir(self.input):
                warnings.warn("Option bundle has no effect when using a single file as input")

        elif not self.bundle:
            if self.title:
                raise ValueError("A title cannot be specified when not using bundle.")

    def _load_document(self, document_path):
        with open(document_path, mode="r", encoding="utf-8") as file:
            filename = os.path.basename(document_path)
            if filename.startswith("_"):
                return

            if self.filename_filter and not re.search(self.filename_filter, document_path):
                return

            md = Markdown(
                extensions=[
                    extensions.TocExtension(id_prefix=filename, toc_depth="2-6"),
                    extensions.SubscriptExtension(),
                    extensions.TextboxExtension(),
                    extensions.CheckboxExtension(),
                    GridTableExtension(),
                ],
            )

            document = frontmatter.load(file)
            content = (
                Environment(
                    autoescape=select_autoescape(),
                    loader=FileSystemLoader(searchpath=[os.path.dirname(document_path), self.input, os.getcwd()]),
                )
                .from_string(document.content)
                .render()
            )

            return Document(
                filename=filename,
                title=filename.removesuffix(".md").replace("_", " "),
                content=md.convert(content),
                meta=document.metadata,
                has_custom_headline=content.startswith("# "),
                hash=str(check_output(["git", "hash-object", document_path]), "utf-8"),
            )

    def execute(self):
        documents = []
        if os.path.isdir(self.input):
            for document_path in sorted(iglob(os.path.join(self.input, "**/*.md"), recursive=True)):
                if document := self._load_document(document_path):
                    documents.append(document)

        else:
            documents.append(self._load_document(self.input))

        if self.bundle:
            self._render_and_output(documents)

        else:
            os.makedirs(self.output_dir, exist_ok=True)
            for doc in documents:
                self._render_and_output(doc)

    def _render_and_output(self, content: list[Document] | Document):
        template, layout_dir = self._load_template(self.layout if self.bundle else content.meta.get('layout', self.layout))
        html = template.render(
            date=date.today().isoformat(),
            commit=os.getenv("CI_COMMIT_SHORT_SHA", "00000000"),
            content_documents=content if self.bundle else [content],
            title=self.title if self.bundle else content.title or "",
        )

        target = os.path.join(
            self.output_dir,
            self.title.replace(" ", "_") if self.bundle else content.filename.removesuffix(".md"),
        )

        if self.output_html:
            with open(target + ".html", "w", encoding="utf-8") as html_file:
                html_file.write(html)

        HTML(string=html, base_url=layout_dir).write_pdf(target=target + ".pdf")

    def _get_layout_dir(self, layout: str):
        if os.path.isdir(layout_dir := os.path.join(self.layouts_dir, layout)):
            return layout_dir

        raise ValueError("Layout could not be found")

    @cache
    def _load_template(self, layout):
        layout_dir = self._get_layout_dir(layout)
        with open(os.path.join(layout_dir, "index.html"), mode="rb") as file:
            template = self.jinja_env.from_string(str(file.read(), "utf-8"))

        return template, layout_dir
