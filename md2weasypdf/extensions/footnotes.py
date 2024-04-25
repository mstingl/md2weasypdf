import xml.etree.ElementTree as etree
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict

from markdown import Markdown
from markdown.extensions import footnotes
from markdown.inlinepatterns import InlineProcessor


@dataclass
class Footnote:
    text: str
    index: int
    inserted: bool = False


class FootnoteInlineProcessor(InlineProcessor):
    def __init__(self, pattern, footnotes):
        super().__init__(pattern)
        self.footnotes: FootnoteExtension = footnotes

    def handleMatch(self, m, data):
        note_id = m.group(1)
        try:
            footnote = self.footnotes.footnotes[note_id]

        except KeyError:
            return None, None, None

        else:
            if not footnote.inserted:
                el = etree.Element("span", attrib={"class": "footnote", "data-footnote-id": note_id})
                el.text = footnote.text
                footnote.inserted = True

            else:
                el = etree.Element("sup", attrib={"class": "footnote-ref", "data-footnote-id": note_id})
                el.text = str(footnote.index)

            return el, m.start(0), m.end(0)


class FootnoteExtension(footnotes.FootnoteExtension):
    def __init__(self):
        self.footnotes: OrderedDict[str, Footnote] = OrderedDict()
        self.unique_prefix = 0
        self.found_refs: dict[str, int] = {}
        self.used_refs: set[str] = set()

    def setFootnote(self, id, text):
        self.footnotes[id] = Footnote(text, len(self.footnotes) + 1)

    def extendMarkdown(self, md: Markdown):
        md.registerExtension(self)
        self.parser = md.parser
        self.md = md

        md.parser.blockprocessors.register(footnotes.FootnoteBlockProcessor(self), 'footnote', 17)
        FOOTNOTE_RE = r'\[\^([^\]]*)\]'  # blah blah [^1] blah
        md.inlinePatterns.register(FootnoteInlineProcessor(FOOTNOTE_RE, self), 'footnote', 170)
