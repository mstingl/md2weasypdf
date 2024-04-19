import os
import re
import time
from datetime import date
from functools import cache, partial
from glob import iglob
from subprocess import check_output
from threading import Timer
from typing import Callable, NamedTuple, Optional

import frontmatter
import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import Markdown
from markdown_grid_tables import GridTableExtension
from rich.console import Console
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from weasyprint import HTML

from . import extensions

BASE_DIR = os.path.dirname(__file__)

console = Console()


class Document(NamedTuple):
    filename: str
    title: str
    content: str
    meta: dict[str, object]
    has_custom_headline: bool
    hash: str


def debounce(wait):
    """Decorator that will postpone a functions
    execution until after wait seconds
    have elapsed since the last time it was invoked."""

    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)

            try:
                debounced.t.cancel()
            except AttributeError:
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()

        return debounced

    return decorator


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, render: Callable[[], None]) -> None:
        self._render = render

    @debounce(1)
    def render(self):
        self._render()
        console.log("Render complete")

    def on_created(self, event: FileSystemEvent):
        console.log("Rerender")
        try:
            self.render()

        except Exception:
            console.print_exception()

    def on_modified(self, event: FileSystemEvent):
        self.on_created(event)


def main(
    input: str = typer.Argument(help="Folder or file used as input"),
    output_folder: str = typer.Argument(),
    bundle: bool = False,
    title: Optional[str] = None,
    layout: str = "doc1",
    output_html: bool = False,
    filename_filter: Optional[str] = None,
    watch: bool = False,
):
    _main(input, output_folder, bundle, title, layout, output_html, filename_filter, watch)


def _main(
    input: str,
    output_folder: str,
    bundle: bool = False,
    title: Optional[str] = None,
    layout: str = "doc1",
    output_html: bool = False,
    filename_filter: Optional[str] = None,
    watch: bool = False,
    layout_dirs: Optional[set[str]] = None,
):
    input = input if os.path.isabs(input) else os.path.join(os.getcwd(), input)
    output_folder = output_folder if os.path.isabs(output_folder) else os.path.join(os.getcwd(), output_folder)
    filename_filter = filename_filter and re.compile(filename_filter)
    layout_dir = get_layout_dir(layout)

    if watch:
        layout_dirs = set()
        observer = Observer()
        execute_render = partial(
            _main,
            input,
            output_folder,
            bundle,
            title,
            layout,
            output_html,
            filename_filter,
            False,
            layout_dirs,
        )
        add_watch_directory = partial(observer.schedule, FileChangeHandler(execute_render), recursive=True)
        add_watch_directory(input)
        add_watch_directory(layout_dir)
        observer.start()

        prev_layout_dirs = layout_dirs.copy()
        try:
            execute_render()

        except Exception:
            console.print_exception()

        try:
            while True:
                time.sleep(1)
                if new_dirs := layout_dirs.difference(prev_layout_dirs):
                    for watch_dir in new_dirs:
                        print("Add watch directory", watch_dir)
                        add_watch_directory(watch_dir)

                prev_layout_dirs = layout_dirs.copy()

        finally:
            observer.stop()
            observer.join()

        return

    def load_document(document_path):
        with open(document_path, mode="r", encoding="utf-8") as file:
            filename = os.path.basename(document_path)
            if filename.startswith("_"):
                return

            if filename_filter and not re.search(filename_filter, document_path):
                return

            env = Environment(
                autoescape=select_autoescape(),
                loader=FileSystemLoader(searchpath=[os.path.dirname(document_path), os.getcwd()]),
            )

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
            content = env.from_string(document.content).render()

            return Document(
                filename=filename,
                title=filename.removesuffix(".md").replace("_", " "),
                content=md.convert(content),
                meta=document.metadata,
                has_custom_headline=content.startswith("# "),
                hash=str(check_output(["git", "hash-object", document_path]), "utf-8"),
            )

    documents = []
    if os.path.isdir(input):
        for document_path in sorted(iglob(os.path.join(input, "**/*.md"), recursive=True)):
            if document := load_document(document_path):
                documents.append(document)

    else:
        documents.append(load_document(input))

    env = Environment(
        autoescape=select_autoescape(),
        loader=FileSystemLoader(searchpath=os.path.abspath(os.path.join(layout_dir, os.pardir))),
    )

    def render(content: list[Document] | Document, doc_title: Optional[str], target: str):
        template, _layout_dir = load_template(
            (not isinstance(content, list) and content.meta.get('layout')) or layout,
            env,
        )
        html = template.render(
            date=date.today().isoformat(),
            commit=os.getenv("CI_COMMIT_SHORT_SHA", "00000000"),
            content_documents=content if isinstance(content, list) else [content],
            title=doc_title or "",
        )
        if output_html:
            with open(target.removesuffix(".pdf") + ".html", "w", encoding="utf-8") as html_file:
                html_file.write(html)

        if layout_dirs is not None:
            layout_dirs.add(_layout_dir)

        HTML(string=html, base_url=_layout_dir).write_pdf(target=target)

    if bundle:
        render(documents, title, output_folder)

    else:
        os.makedirs(output_folder, exist_ok=True)
        for doc in documents:
            render(doc, doc.title, os.path.join(output_folder, doc.filename.removesuffix(".md") + ".pdf"))


def get_layout_dir(layout):
    if os.path.isdir(local_layout := layout if os.path.isabs(layout) else os.path.join(os.getcwd(), layout)):
        return local_layout

    if os.path.isdir(included_layout := os.path.join(BASE_DIR, "layouts", layout)):
        return included_layout

    raise ValueError("Layout could not be found")


@cache
def load_template(layout, env):
    layout_dir = get_layout_dir(layout)
    with open(os.path.join(layout_dir, "index.html"), mode="rb") as file:
        template = env.from_string(str(file.read(), "utf-8"))

    return template, layout_dir


if __name__ == "__main__":
    typer.run(main)
