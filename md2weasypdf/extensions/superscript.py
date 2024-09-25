from markdown import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor


class SuperscriptExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(SimpleTagInlineProcessor(r"(\^)([^\^]+)\^", "sup"), "superscript", 150)
