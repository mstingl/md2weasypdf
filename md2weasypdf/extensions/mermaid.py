import base64
from subprocess import CalledProcessError, check_output

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

        try:
            svg = check_output(["mmdr", "-e", "svg"], input=code.encode("utf-8"))

        except (CalledProcessError, FileNotFoundError) as error:
            raise ValueError("Cannot run mmdr to convert mermaid to image") from error

        self.__generated_file_contents_cache[code] = str(base64.b64encode(svg), "utf-8")
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
                placeholder = self.md.htmlStash.store(f'<img src="data:image/svg+xml;base64,{file_content}">')
                text = f'{text[:m.start()]}\n{placeholder}\n{text[m.end():]}'
                pos = m.start() + len(placeholder)

            else:
                break

        return text.split("\n")
