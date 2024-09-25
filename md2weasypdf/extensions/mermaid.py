import base64
import os
from functools import cache
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
    __generated_file_contents_cache = {}

    def generate_file_content(self, code):
        if code in self.__generated_file_contents_cache:
            return self.__generated_file_contents_cache[code]

        with TemporaryDirectory() as tempdir:
            input_path = os.path.join(tempdir, "in.svg")
            with open(input_path, 'w') as input_file:
                input_file.write(code)

            output_path = os.path.join(tempdir, "out.png")
            try:
                check_call(["mmdc", "-w", "2500", "-s", "2", "--input", input_path, "--output", output_path], shell=True)

            except CalledProcessError as error:
                raise ValueError("Cannot run mmdc to convert mermaid to image") from error

            with open(output_path, "rb") as out_file:
                self.__generated_file_contents_cache[code] = ''.join(str(base64.b64encode(out_file.read()), 'utf-8').splitlines())

            return self.__generated_file_contents_cache[code]

    def run(self, lines: list[str]) -> list[str]:
        """Match and store Fenced Code Blocks in the `HtmlStash`."""

        text = "\n".join(lines)
        pos = 0
        while 1:
            m = self.FENCED_BLOCK_RE.search(text, pos)
            if m:
                pos = m.end()
                if not m.group('lang') == 'mermaid':
                    continue

                file_content = self.generate_file_content(m.group('code'))
                placeholder = self.md.htmlStash.store(f'<img src="data:image/png;base64,{file_content}">')
                text = f'{text[:m.start()]}\n{placeholder}\n{text[m.end():]}'
                pos = m.start() + len(placeholder)

            else:
                break

        return text.split("\n")
