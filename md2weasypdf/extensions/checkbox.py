import re
from xml.etree import ElementTree as etree
from xml.etree.ElementTree import Element

from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


class CheckboxInlineProcessor(InlineProcessor):
    def handleMatch(self, m: re.Match[str], data) -> tuple[Element, int, int] | tuple[None, None, None]:
        el = etree.Element("input")
        el.attrib["type"] = "checkbox"
        if m.group(1) == "x":
            el.attrib["checked"] = "checked"

        if m.group(2):
            el.attrib["name"] = m.group(2)

        return el, m.start(0), m.end(0)


class CheckboxExtension(Extension):
    def extendMarkdown(self, md: Markdown) -> None:
        md.inlinePatterns.register(
            CheckboxInlineProcessor(r"\[( |x)?\](\w+)?"),
            "checkbox",
            150,
        )
