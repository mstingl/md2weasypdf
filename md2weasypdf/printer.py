import os
import re
import warnings
from dataclasses import dataclass
from datetime import date
from functools import cache
from glob import iglob
from pathlib import Path
from subprocess import check_output
from typing import List, NamedTuple, Optional

import frontmatter
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from markdown import Markdown
from markdown_grid_tables import GridTableExtension
from weasyprint import HTML

from . import extensions


class Article(NamedTuple):
    source: Path
    title: str
    content: str
    meta: dict[str, object]
    has_custom_headline: bool
    hash: str


@dataclass
class Document:
    title: str
    template: Template
    layout_dir: Path
    articles: List[Article]

    def write_pdf(self, output_dir: Path, output_html: bool = False):
        html = self.template.render(
            date=date.today().isoformat(),
            commit=os.getenv("CI_COMMIT_SHORT_SHA", "00000000"),
            articles=self.articles,
            title=self.title,
        )

        output_filename = self.title.replace(" ", "_")
        if output_html:
            with open(output_dir / f"{output_filename}.html", "w", encoding="utf-8") as html_file:
                html_file.write(html)

        pdf_output_target = output_dir / f"{output_filename}.pdf"
        HTML(string=html, base_url=str(self.layout_dir)).write_pdf(target=pdf_output_target)
        return pdf_output_target


class Printer:
    @staticmethod
    def _ensure_path(path: Path, dir: Optional[bool] = None, create: Optional[bool] = None):
        if not path.is_absolute():
            path = Path(os.path.join(os.getcwd(), path))

        if not path.exists():
            if create and dir:
                path.mkdir(parents=True)

            else:
                raise FileNotFoundError("Path does not exist")

        if dir is True and not path.is_dir():
            raise ValueError(f"{path} is not a directory")

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
        self.output_dir = self._ensure_path(output_dir, dir=True, create=True)
        self.layouts_dir = self._ensure_path(layouts_dir, dir=True)
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

    def _load_article(self, source: Path | str):
        if isinstance(source, str):
            source = Path(source)

        with open(source, mode="r", encoding="utf-8") as file:
            article = frontmatter.load(file)

        md = Markdown(
            extensions=[
                extensions.FootnoteExtension(),
                extensions.TableExtension(),
                extensions.ToaExtension(),
                extensions.AbbrExtension(),
                extensions.TocExtension(id_prefix=source.name, toc_depth="2-6"),
                extensions.SubscriptExtension(),
                extensions.TextboxExtension(),
                extensions.CheckboxExtension(),
                GridTableExtension(),
            ],
        )

        content = (
            Environment(
                autoescape=select_autoescape(),
                loader=FileSystemLoader(searchpath=[os.path.dirname(source), self.input, os.getcwd()]),
            )
            .from_string(article.content)
            .render()
        )

        return Article(
            source=source,
            title=source.name.removesuffix(".md").replace("_", " "),
            content=md.convert(content),
            meta=article.metadata,
            has_custom_headline=content.startswith("# "),
            hash=str(check_output(["git", "hash-object", source]), "utf-8"),
        )

    def execute(self):
        self._load_template.cache_clear()
        articles: List[Article] = []
        if self.input.is_dir():
            for article_path in sorted(iglob(os.path.join(self.input, "**/*.md"), recursive=True)):
                if os.path.basename(article_path).startswith("_"):
                    continue

                if self.filename_filter and not re.search(self.filename_filter, article_path):
                    continue

                articles.append(self._load_article(article_path))

        else:
            articles.append(self._load_article(self.input))

        write_options = {"output_dir": self.output_dir, "output_html": self.output_html}

        if self.bundle:
            doc = Document(
                self.title,
                *self._load_template(self.layout),
                articles,
            )
            yield doc, doc.write_pdf(**write_options)

        else:
            for article in articles:
                try:
                    doc = Document(
                        article.title,
                        *self._load_template(article.meta.get('layout', self.layout)),
                        [article],
                    )

                except ValueError as error:
                    raise ValueError(f"Could not create document for {article.source}: {error}") from error

                yield doc, doc.write_pdf(**write_options)

    def _get_layout_dir(self, layout: str):
        if not layout:
            raise ValueError("No layout defined")

        if os.path.isdir(layout_dir := self.layouts_dir / layout):
            return layout_dir

        raise ValueError("Layout \"{layout}\" could not be found")

    @cache
    def _load_template(self, layout):
        layout_dir = self._get_layout_dir(layout)
        with open(layout_dir / "index.html", mode="rb") as file:
            template = self.jinja_env.from_string(str(file.read(), "utf-8"))

        return template, layout_dir
