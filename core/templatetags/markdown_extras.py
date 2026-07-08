from django import template
from django.utils.safestring import mark_safe
from core.content_loader import inline_format, render_markdown

register = template.Library()

@register.filter
def markdown(value):
    """Full markdown rendering (headings, lists, code blocks, inline)."""
    if not value:
        return ""
    return mark_safe(render_markdown(value))

@register.filter
def markdown_inline(value):
    """Inline-only markdown (**bold**, *italic*, `code`) — no block elements."""
    if not value:
        return ""
    return mark_safe(inline_format(value))
