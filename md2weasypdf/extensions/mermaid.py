import base64
import os
from subprocess import CalledProcessError, check_call
from tempfile import TemporaryDirectory

from markdown import Markdown
from markdown.extensions import Extension
from markdown.extensions.fenced_code import FencedBlockPreprocessor


class MermaidExtension(Extension):
    def extendMarkdown(self, md: Markdown):
        md.registerExtension(self)
        self.parser = md.parser
        self.md = md

        md.preprocessors.register(MermaidPreprocessor(md, {}), 'mermaid', 30)


class MermaidPreprocessor(FencedBlockPreprocessor):
    def run(self, lines: list[str]) -> list[str]:
        """Match and store Fenced Code Blocks in the `HtmlStash`."""

        text = "\n".join(lines)
        while 1:
            m = self.FENCED_BLOCK_RE.search(text)
            if m and m.group('lang') == 'mermaid':
                with TemporaryDirectory() as tempdir:
                    input_path = os.path.join(tempdir, "in.svg")
                    with open(input_path, 'w') as input_file:
                        input_file.write(m.group('code'))

                    output_path = os.path.join(tempdir, "out.png")
                    try:
                        check_call(["mmdc", "-w", "2500", "-s", "2", "--input", input_path, "--output", output_path], shell=True)

                    except CalledProcessError as error:
                        raise ValueError("Cannot run mmdc to convert mermaid to image") from error

                    with open(output_path, "rb") as out_file:
                        file_content = ''.join(str(base64.b64encode(out_file.read()), 'utf-8').splitlines())

                placeholder = self.md.htmlStash.store(f'<img src="data:image/png;base64,{file_content}">')
                text = f'{text[:m.start()]}\n{placeholder}\n{text[m.end():]}'

            else:
                break

        return text.split("\n")
