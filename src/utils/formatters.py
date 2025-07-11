#!/usr/bin/env python3
"""
Formatting utilities for the Sunflower AI application.
"""

import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

def markdown_to_html(text: str) -> str:
    """
    Converts a Markdown string to HTML, with support for fenced code blocks
    and syntax highlighting.
    
    Args:
        text: The Markdown text to convert.
        
    Returns:
        The converted HTML string.
    """
    try:
        # Custom handling for code blocks to apply pygments
        class PygmentsFencedCodeExtension(FencedCodeExtension):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def fence_div_format(self, source, language, class_name, options, md, **kwargs):
                try:
                    lexer = get_lexer_by_name(language)
                except Exception:
                    try:
                        lexer = guess_lexer(source)
                    except Exception:
                        return f'<pre class="{class_name}"><code>{source}</code></pre>'

                formatter = HtmlFormatter(style='monokai', cssclass='highlight', noclasses=True)
                return highlight(source, lexer, formatter)

        # Using the 'fenced_code' extension enables syntax highlighting
        # when a language is specified, e.g., ```python ... ```
        html = markdown.markdown(
            text,
            extensions=[PygmentsFencedCodeExtension(), 'codehilite']
        )
        return html
    except Exception:
        # Fallback to plain text if markdown conversion fails
        return f"<p>{text}</p>"
