import time
import warnings
from functools import partial
from pathlib import Path
from threading import Timer
from typing import Callable, Optional

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
    input: Annotated[Path, typer.Argument(help="Folder or file used as input")],
    output_dir: Annotated[Path, typer.Argument(help="Folder where resulting files are written to")] = Path("."),
    *,
    bundle: Annotated[bool, typer.Option(help="Bundle all input documents into a single output file")] = False,
    title: Annotated[Optional[str], typer.Option(help="Title of the resulting document. Can only be used in conjunction with bundle.")] = None,
    layouts_dir: Annotated[Path, typer.Option(help="Base folder containing the available layouts")] = "layouts",
    layout: Annotated[Optional[str], typer.Option(help="Default layout to use")] = None,
    output_html: Annotated[bool, typer.Option(help="Additionally output the raw HTML file which is used to create the pdf")] = False,
    filename_filter: Annotated[
        Optional[str],
        typer.Option(help="Regular expression to filter files in input directory by subpath and/or filename"),
    ] = None,
    watch: Annotated[bool, typer.Option(help="Watch input directory for changes and re-run the conversion")] = False,
):
    try:
        printer = Printer(
            input=input,
            output_dir=output_dir,
            layouts_dir=layouts_dir,
            bundle=bundle,
            title=title,
            layout=layout,
            output_html=output_html,
            filename_filter=filename_filter,
        )

    except ValueError as error:
        console.print("Error:", error, style="bold red")
        raise typer.Exit(1)

    if watch:

        def execute():
            try:
                for document, output_path in printer.execute():
                    console.log(
                        f"Created PDF",
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

        observer = Observer()
        add_watch_directory = partial(observer.schedule, FileChangeHandler(execute), recursive=True)
        add_watch_directory(input)
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

    printer.execute()


if __name__ == "__main__":
    typer.run(main)
