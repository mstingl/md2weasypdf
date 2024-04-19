from markdown import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor


class SubscriptExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(SimpleTagInlineProcessor(r"(\~)([^\~]+)\~", "sub"), "subscript", 150)
