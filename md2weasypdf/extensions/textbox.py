import re
from xml.etree import ElementTree as etree
from xml.etree.ElementTree import Element

from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


class TextboxInlineProcessor(InlineProcessor):
    def handleMatch(self, m: re.Match[str], data) -> tuple[Element, int, int] | tuple[None, None, None]:
        if m.group(3) == "textbox":
            el = etree.Element("textarea")

        else:
            el = etree.Element("input")

            if m.group(3) == "YYYY-MM-DD":
                el.attrib["type"] = "date"

            else:
                el.attrib["type"] = "text"

        if m.group(1):
            el.attrib["name"] = m.group(1)

        if m.group(4):
            el.attrib["placeholder"] = m.group(4)

        return el, m.start(0), m.end(0)


class TextboxExtension(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        md.inlinePatterns.register(
            TextboxInlineProcessor(r"\[>(\w+)?(\|([\w-]+))?\](?:\{([^\}]+)\})?"),
            "textbox",
            200,
        )
