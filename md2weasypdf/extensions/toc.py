import xml.etree.ElementTree as etree
from typing import Any

from markdown import Markdown
from markdown.extensions import toc
from markdown.extensions.toc import get_name, nest_toc_tokens, slugify, stashedHTML2text, unescape, unique
from markdown.util import code_escape


class TocTreeprocessor(toc.TocTreeprocessor):
    def __init__(self, md: Markdown, config: dict[str, Any]) -> None:
        self.id_prefix = config.pop('id_prefix', '')
        super().__init__(md, config)

    def build_toc_div(self, toc_list: list) -> etree.Element:
        """Return a string div given a toc list."""
        div = etree.Element("div")
        div.attrib["class"] = self.toc_class

        # Add title to the div
        if self.title:
            header = etree.SubElement(div, "h2", attrib={"class": f"doctitle {self.title_class}"})
            header.text = self.title

        def build_etree_ul(toc_list: list, parent: etree.Element, level: int = 0) -> etree.Element:
            for item in toc_list:
                # List item link, to be inserted into the toc div
                li = etree.SubElement(parent, "li", attrib={"style": f"--level: {level}em"})
                link = etree.SubElement(li, "a")
                etree.SubElement(
                    link,
                    "span",
                    attrib={
                        "class": "toctitle",
                        "href": "#" + item.get('id', ''),
                    },
                )
                etree.SubElement(link, "div", attrib={"class": "tocspacer"})
                etree.SubElement(
                    link,
                    "span",
                    attrib={
                        "class": "tocpage",
                        "href": "#" + item.get('id', ''),
                    },
                )
                link.attrib["href"] = '#' + item.get('id', '')
                if item['children']:
                    build_etree_ul(item['children'], parent, level + 1)

        build_etree_ul(toc_list, etree.SubElement(div, "ol"))

        if 'prettify' in self.md.treeprocessors:
            self.md.treeprocessors['prettify'].run(div)

        return div

    def run(self, doc: etree.Element) -> None:
        # Get a list of id attributes
        used_ids = set()
        for el in doc.iter():
            if "id" in el.attrib:
                used_ids.add(el.attrib["id"])

        toc_tokens = []
        for el in doc.iter():
            if isinstance(el.tag, str) and self.header_rgx.match(el.tag):
                self.set_level(el)
                text = get_name(el)

                # Do not override pre-existing ids
                if "id" not in el.attrib:
                    innertext = unescape(stashedHTML2text(text, self.md))
                    el.attrib["id"] = unique(self.id_prefix + self.sep + self.slugify(innertext, self.sep), used_ids)

                if int(el.tag[-1]) >= self.toc_top and int(el.tag[-1]) <= self.toc_bottom:
                    toc_tokens.append(
                        {
                            'level': int(el.tag[-1]),
                            'id': el.attrib["id"],
                            'name': unescape(stashedHTML2text(code_escape(el.attrib.get('data-toc-label', text)), self.md, strip_entities=False)),
                        }
                    )

                # Remove the data-toc-label attribute as it is no longer needed
                if 'data-toc-label' in el.attrib:
                    del el.attrib['data-toc-label']

                if self.use_anchors:
                    self.add_anchor(el, el.attrib["id"])
                if self.use_permalinks not in [False, None]:
                    self.add_permalink(el, el.attrib["id"])

        toc_tokens = nest_toc_tokens(toc_tokens)
        div = self.build_toc_div(toc_tokens)
        if self.marker:
            self.replace_marker(doc, div)

        # serialize and attach to markdown instance.
        toc = self.md.serializer(div)
        for pp in self.md.postprocessors:
            toc = pp.run(toc)
        self.md.toc_tokens = toc_tokens
        self.md.toc = toc


class TocExtension(toc.TocExtension):
    TreeProcessorClass = TocTreeprocessor

    def __init__(self, **kwargs):
        id_prefix = kwargs.pop('id_prefix', '')
        super().__init__(**kwargs)

        self.config['id_prefix'] = [id_prefix, '']
