"""Text helpers shared by the HTML spiders."""
from parsel import SelectorList


def text_of(selector) -> str | None:
    """all descendant text of the first matched element, whitespace collapsed, None when empty"""
    nodes = selector if isinstance(selector, SelectorList) else SelectorList([selector])
    if not nodes:
        return None
    return ' '.join(' '.join(nodes[0].css('::text').getall()).split()) or None
