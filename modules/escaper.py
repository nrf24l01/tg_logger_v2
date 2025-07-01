import re

def escape_markdown_v2(text: str) -> str:
    # Characters to escape according to Telegram MarkdownV2 docs
    escape_chars = r'_*[]()~`>#+-=|{}.!\\'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)