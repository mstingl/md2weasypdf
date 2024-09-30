import json
import os
import time
import warnings
from functools import partial
from hashlib import sha1
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, check_call, check_output
from threading import Timer
from typing import Callable, List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .printer import Printer

console = Console()

warnings.showwarning = lambda message, category, filename, lineno, file, line: console.print("Warning:", message, style="bold yellow")


def debounce(wait):
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
    def __init__(self, render: Callable[[Optional[Path]], None]) -> None:
        self._render = render

    @debounce(1)
    def render(self, event: FileSystemEvent):
        path = None
        if not event.is_directory and event.event_type in ('modified'):
            path = Path(event.src_path)
            if path.suffix != '.md':
                path = None

        self._render(path)
        console.log("Render complete")

    def on_created(self, event: FileSystemEvent):
        console.log("Rerender")
        try:
            self.render(event)

        except Exception:
            console.print_exception()

    def on_modified(self, event: FileSystemEvent):
        self.on_created(event)


def main(
    input: Annotated[Path, typer.Argument(help="Folder or file used as input")],
    output_dir: Annotated[Path, typer.Argument(help="Folder where resulting files are written to")] = Path(os.getenv('OUTPUT_PATH', ".")),
    *,
    bundle: Annotated[bool, typer.Option(help="Bundle all input documents into a single output file")] = False,
    title: Annotated[Optional[str], typer.Option(help="Title of the resulting document. Can only be used in conjunction with bundle.")] = None,
    alt_title: Annotated[
        Optional[str], typer.Option(help="Alt-Title of the resulting document. Can only be used in conjunction with bundle.")
    ] = None,
    layouts_dir: Annotated[
        str,
        typer.Option(
            help="Base folder containing the available layouts, alternatively also a remote git url can be provided from which the latest version is used"
        ),
    ] = "./layouts",
    layout: Annotated[Optional[str], typer.Option(help="Default layout to use")] = None,
    output_html: Annotated[bool, typer.Option(help="Additionally output the raw HTML file which is used to create the pdf")] = False,
    output_md: Annotated[bool, typer.Option(help="Additionally output the raw Markdown which is used to create the HTML for the pdf")] = False,
    filename_filter: Annotated[
        Optional[str],
        typer.Option(help="Regular expression to filter files in input directory by subpath and/or filename"),
    ] = None,
    meta: Annotated[
        Optional[str],
        typer.Option(help="Metadata for document generation passed to the layout, pass values using a JSON object"),
    ] = None,
    watch: Annotated[bool, typer.Option(help="Watch input directory for changes and re-run the conversion")] = False,
    only_modified_in_commit: Annotated[Optional[str], typer.Option(help="Only print documents which have been changed in the given commit")] = None,
):
    if layouts_dir.endswith(".git") and (layouts_dir.startswith("https://") or layouts_dir.startswith("ssh://") or layouts_dir.startswith("git@")):
        layouts_dir_path = Path(f"~/.cache/md2weasypdf/{sha1(layouts_dir.encode('utf-8')).hexdigest()}").expanduser()
        layouts_dir_path.mkdir(parents=True, exist_ok=True)
        try:
            if not (layouts_dir_path / ".git").exists():
                console.print("Pulling layouts repository", style="cyan")
                try:
                    check_call(["git", "clone", layouts_dir, layouts_dir_path], stdout=DEVNULL)

                except CalledProcessError:
                    layouts_dir_path.unlink(missing_ok=True)
                    raise

            else:
                console.print("Updating layouts repository", style="cyan")
                check_call(["git", "-C", layouts_dir_path, "pull"], stdout=DEVNULL)

        except CalledProcessError as error:
            console.print(f"Error while fetching layouts repository: {error}", style="bold red")
            raise typer.Exit(9) from error

    else:
        layouts_dir_path = Path(layouts_dir)

    try:
        printer = Printer(
            input=input,
            output_dir=output_dir,
            layouts_dir=layouts_dir_path,
            bundle=bundle,
            title=title,
            alt_title=alt_title,
            layout=layout,
            output_html=output_html,
            output_md=output_md,
            filename_filter=filename_filter,
            meta=json.loads(meta) if meta else None,
        )

    except ValueError as error:
        console.print("Error:", error, style="bold red")
        raise typer.Exit(1)

    modified_files: List[Path] = []
    if only_modified_in_commit:
        modified_files = [
            Path(file).absolute()
            for file in str(check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", only_modified_in_commit]), "utf-8").splitlines()
        ]

    def execute(path: Optional[Path] = None):
        documents = [path] if path else printer.get_documents()
        if only_modified_in_commit:
            documents = [file for file in documents if file in modified_files]

        try:
            for document, output_path in printer.execute(documents=documents):
                console.log(
                    "Created PDF",
                    f'"{document.title}"',
                    f"(out of {len(document.articles)})" if len(document.articles) > 1 else f"(from {document.articles[0].source})",
                    "->",
                    output_path,
                )

            console.log("Completed document creation")

        except ValueError as error:
            console.log("Error:", error, style="bold red")

        except Exception:
            console.print_exception()

    if watch:
        observer = Observer()
        add_watch_directory = partial(observer.schedule, FileChangeHandler(execute), recursive=True)
        add_watch_directory(input.parent if input.is_file() else input)
        add_watch_directory(layouts_dir)

        observer.start()

        execute()

        try:
            while True:
                time.sleep(1)

        finally:
            observer.stop()
            observer.join()

            return

    execute()


if __name__ == "__main__":
    typer.run(main)
