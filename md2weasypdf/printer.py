import hashlib
import os
import re
import warnings
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from glob import glob
from pathlib import Path
from subprocess import check_output
from typing import Callable, List, Optional, Tuple
from urllib.error import URLError
from urllib.parse import urlparse

import frontmatter
import yaml
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from markdown import Markdown
from weasyprint import HTML, default_url_fetcher

from . import extensions


class FileSystemWithFrontmatterLoader(FileSystemLoader):
    def __init__(self, *args, loaded_paths: set[Path] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.loaded_paths = loaded_paths

    def get_source(self, environment: Environment, template: str) -> Tuple[str, str, Callable[[], bool]]:
        contents, path, uptodate = super().get_source(environment, template)
        self.loaded_paths.add(Path(path))
        return frontmatter.loads(contents).content, path, uptodate


@dataclass
class Article:
    source: Path
    template_loader_searchpaths: list[str | Path] = field(default_factory=list)

    def __post_init__(self):
        self.loaded_paths: set[Path] = set()
        self.meta: dict[str, object] = {}

        if self.source.suffix == ".md":
            self._init_md()

        elif self.source.suffix == ".yaml":
            self._init_yaml()

        else:
            raise NotImplementedError(f"No handling for {self.source.suffix} files implemented")

    def _get_template_env(self):
        return Environment(
            autoescape=select_autoescape(),
            loader=FileSystemWithFrontmatterLoader(
                searchpath=[os.path.dirname(self.source), *self.template_loader_searchpaths, os.getcwd()],
                loaded_paths=self.loaded_paths,
            ),
        )

    def _init_md(self):
        with open(self.source, mode="r", encoding="utf-8") as file:
            article = frontmatter.load(file)

        article_template = self._get_template_env().from_string(article.content)

        self.meta = article.metadata
        self.content_md = article_template.render()

    @staticmethod
    @cache
    def _yaml_md_template(directory: Path, max_depth=2):
        depth = 0
        while depth < max_depth:
            depth += 1
            if (template_path := directory / "_template.md").exists() or (template_path := directory / "_template.md.j2").exists():
                with open(template_path, mode="r", encoding="utf-8") as file:
                    return frontmatter.load(file)

            directory = directory.parent

        raise FileNotFoundError(f"No _template.md file found in {directory} or parent directories (going up max. {max_depth} levels)")

    def _init_yaml(self):
        with open(self.source, mode="r", encoding="utf-8") as file:
            article = yaml.load(file, Loader=yaml.Loader)

        md_template = self._yaml_md_template(self.source.parent)
        article_template = self._get_template_env().from_string(md_template.content)

        self.meta = {**md_template.metadata, **getattr(article, "metadata", {})}
        self.content_md = article_template.render(article)

    @property
    def title(self) -> str:
        return re.sub(r"(\([^\)]+\))|(\[[^\]]+\])", "", self.source.name.removesuffix(self.source.suffix).replace("_", " ")).strip()

    @property
    def filename(self) -> str:
        return re.sub(r"\s+", " ", re.sub(r"\([^\)]+\)", "", self.source.name.removesuffix(self.source.suffix))).strip()

    @property
    def content(self) -> str:
        enabled_extensions = [
            extensions.FootnoteExtension(),
            extensions.TableExtension(),
            extensions.ToaExtension(),
            extensions.AbbrExtension(),
            extensions.TocExtension(id_prefix=self.source.name, toc_depth=self.meta.get("toc_depth", "2-6")),
            extensions.SubscriptExtension(),
            extensions.TextboxExtension(),
            extensions.CheckboxExtension(),
            extensions.FencedCodeExtension(),
            extensions.MermaidExtension(),
            extensions.TableCaptionExtension() if self.meta.get("table_caption", True) else None,
            extensions.GridTableExtension(),
            extensions.SaneListExtension(),
        ]

        md = Markdown(extensions=[e for e in enabled_extensions if e], tab_length=int(str(self.meta.get("tab_length", 2))))

        return md.convert(self.content_md)

    @property
    def has_custom_headline(self) -> bool:
        return self.content.strip(" \r\n").startswith("<h1")

    @property
    def hash(self):
        hashes = [check_output(["git", "hash-object", path]) for path in [self.source, *self.loaded_paths]]
        if not self.loaded_paths:
            return str(hashes[0], "utf-8")

        return hashlib.sha1(b"".join(hashes)).hexdigest()

    @property
    def modified_date(self):
        dates = [str(check_output(["git", "log", "-1", "--pretty=%cs", path]), "utf-8").strip() for path in [self.source, *self.loaded_paths]]
        return sorted(dates, reverse=True)[0]


@dataclass
class Document:
    title: str
    filename: str
    template: Template
    layout_dir: Path
    articles: List[Article]
    meta: dict[str, object]

    @staticmethod
    def get_commit():
        if commit_sha_env := os.getenv("CI_COMMIT_SHORT_SHA", None):
            return commit_sha_env

        return str(check_output(["git", "rev-parse", "HEAD"]), "utf-8")[:8] + ("-dirty" if check_output(["git", "status", "-s"]) else "")

    def write_pdf(self, output_dir: Path, output_html: bool = False):
        html = self.template.render(
            date=date.today().isoformat(),
            commit=self.get_commit(),
            articles=self.articles,
            title=self.title,
            meta=self.meta,
        )

        if output_html:
            with open(output_dir / f"{self.filename}.html", "w", encoding="utf-8") as html_file:
                html_file.write(html)

        pdf_output_target = output_dir / f"{self.filename}.pdf"
        HTML(
            string=html,
            base_url=str(self.layout_dir),
            url_fetcher=self.url_fetcher,
        ).write_pdf(
            target=pdf_output_target,
            pdf_forms=True,
        )
        return pdf_output_target

    def url_fetcher(self, url: str, timeout=10, ssl_context=None):
        try:
            return default_url_fetcher(url, timeout=timeout, ssl_context=ssl_context)

        except URLError:
            if not url.startswith('file://'):
                raise

            local_relative_path = Path(urlparse(url).path.removeprefix('/')).relative_to(self.layout_dir)
            articles_source_directories = {a.source.parent for a in self.articles}
            for source_dir in articles_source_directories:
                try:
                    return default_url_fetcher((source_dir / local_relative_path).as_uri(), timeout=timeout, ssl_context=ssl_context)

                except URLError:
                    pass

            raise


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
        output_md: bool = False,
        filename_filter: Optional[str] = None,
        meta: Optional[dict[str, object]] = None,
    ):
        self.input = self._ensure_path(input)
        self.output_dir = self._ensure_path(output_dir, dir=True, create=True)
        self.layouts_dir = self._ensure_path(layouts_dir, dir=True)
        self.bundle = bundle
        self.title = title
        self.layout = layout
        self.output_html = output_html
        self.output_md = output_md
        self.filename_filter = re.compile(filename_filter) if filename_filter else None
        self.meta = meta or {}
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

    def _load_article(self, source: Path):
        return Article(source=source, template_loader_searchpaths=[self.input])

    def get_documents(self):
        return [
            Path(file)
            for file in sorted(
                glob(os.path.join(self.input, "**/*.md"), recursive=True) + glob(os.path.join(self.input, "**/*.yaml"), recursive=True)
            )
        ]

    def execute(self, documents: Optional[List[Path]] = None):
        self._load_template.cache_clear()
        articles: List[Article] = []
        if self.input.is_dir():
            if documents is None:
                documents = self.get_documents()

            for article_path in documents:
                if article_path.name.startswith("_"):
                    continue

                if self.filename_filter and not re.search(self.filename_filter, article_path.relative_to(self.input).as_posix()):
                    continue

                articles.append(self._load_article(article_path))

        else:
            articles.append(self._load_article(self.input))

        if self.output_md:
            for article in articles:
                try:
                    with open(self.output_dir / article.source.name, "w") as file:
                        file.write(article.content_md)

                except Exception as error:
                    raise ValueError(f"Could not output md for {article.source}: {error}") from error

        write_options = {"output_dir": self.output_dir, "output_html": self.output_html}

        if self.bundle:
            doc = Document(
                self.title,  # type: ignore  # title cannot be empty when bundle is set
                self.title.replace(" ", "_"),
                *self._load_template(self.layout),
                articles=articles,
                meta=self.meta,
            )
            yield doc, doc.write_pdf(**write_options)

        else:
            for article in articles:
                try:
                    doc = Document(
                        article.title,
                        article.filename,
                        *self._load_template(article.meta.get('layout', self.layout)),
                        articles=[article],
                        meta=self.meta | article.meta,
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

    @staticmethod
    def try_files(path: Path, filenames: List[str]):
        for filename in filenames:
            if (filepath := path / filename).exists():
                return filepath

        raise FileNotFoundError

    @cache
    def _load_template(self, layout):
        layout_dir = self._get_layout_dir(layout)
        with self.try_files(layout_dir, ["index.html.j2", "index.html"]).open(mode="rb") as file:
            template = self.jinja_env.from_string(str(file.read(), "utf-8"))

        return template, layout_dir
