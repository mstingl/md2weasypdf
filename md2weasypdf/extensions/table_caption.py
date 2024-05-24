import xml.etree.ElementTree as etree
from typing import List

from markdown import Markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class TableCaptionExtension(Extension):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        """Insert after AbbrPreprocessor."""
        md.treeprocessors.register(TableCaptionProcessor(md, self), 'tablecaption', 5)


class TableCaptionProcessor(Treeprocessor):
    def __init__(self, md: Markdown, tablecaption: TableCaptionExtension) -> None:
        self.tablecaption = tablecaption
        self.tables: List[etree.Element] = []
        super().__init__(md)

    def run(self, doc: etree.Element) -> None:
        for table in doc.findall("table"):
            if table.find("caption"):
                continue

            if table not in self.tables:
                self.tables.append(table)

            caption = etree.Element("caption")
            caption.text = "Table %i" % (self.tables.index(table) + 1)
            table.append(caption)
