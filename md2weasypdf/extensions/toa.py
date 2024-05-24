import xml.etree.ElementTree as etree
from typing import Dict

from markdown import Markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class ToaExtension(Extension):
    """Table of Abbreviations Extension for Python-Markdown."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        """Insert after AbbrPreprocessor."""
        md.treeprocessors.register(ToaProcessor(md, self), 'toa', 5)


class ToaProcessor(Treeprocessor):
    def __init__(self, md: Markdown, toa: ToaExtension) -> None:
        self.marker = "[TOA]"
        self.toa = toa
        super().__init__(md)

    def iterparent(self, node):
        '''Iterator wrapper to get allowed parent and child all at once.'''

        for child in node:
            if child.tag not in ['pre', 'code']:
                yield node, child
                yield from self.iterparent(child)

    def replace_marker(self, root, elem):
        for p, c in self.iterparent(root):
            text = ''.join(c.itertext()).strip()
            if not text:
                continue

            if c.text and c.text.strip() == self.marker and len(c) == 0:
                for i in range(len(p)):
                    if p[i] == c:
                        p[i] = elem
                        break

    def build_toa_table(self, abbreviations: Dict[str, str]) -> etree.Element:
        table = etree.Element("table", attrib={"class": "toa"})
        tbody = etree.SubElement(table, "tr")
        for title, text in abbreviations.items():
            tr = etree.SubElement(tbody, "tr")
            td = etree.SubElement(tr, "td")
            td.text = title
            td = etree.SubElement(tr, "td")
            td.text = text

        return table

    def run(self, doc: etree.Element) -> None:
        abbreviations = {}
        for el in doc.iter("abbr"):
            abbreviations[el.text] = el.get("title")

        self.replace_marker(doc, self.build_toa_table(abbreviations))
