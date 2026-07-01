"""Unicode text styles for Telegram display names.

Telegram does not let userbots change a real font. These helpers convert
ASCII letters and digits to Unicode look-alike characters instead.
"""

from string import ascii_lowercase, ascii_uppercase, digits

STYLE_LABELS = {
    "plain": "普通 YourName 21:32",
    "bold": "粗体 𝐘𝐨𝐮𝐫𝐍𝐚𝐦𝐞 𝟐𝟏:𝟑𝟐",
    "bold_italic": "粗斜体 𝒀𝒐𝒖𝒓𝑵𝒂𝒎𝒆 𝟐𝟏:𝟑𝟐",
    "script": "花体 𝓨𝓸𝓾𝓻𝓝𝓪𝓶𝓮 𝟐𝟏:𝟑𝟐",
    "fraktur": "哥特 𝖄𝖔𝖚𝖗𝕹𝖆𝖒𝖊 𝟚𝟙:𝟛𝟚",
    "sans": "无衬线 𝖸𝗈𝗎𝗋𝖭𝖺𝗆𝖾 𝟤𝟣:𝟥𝟤",
    "monospace": "等宽 𝚈𝚘𝚞𝚛𝙽𝚊𝚖𝚎 𝟸𝟷:𝟹𝟸",
    "fullwidth": "全角 ＹｏｕｒＮａｍｅ　２１：３２",
}

STYLE_ORDER = tuple(STYLE_LABELS)

_ALIASES = {
    "": "plain",
    "none": "plain",
    "normal": "plain",
    "regular": "plain",
    "italic_bold": "bold_italic",
    "bolditalic": "bold_italic",
    "wide": "fullwidth",
    "mono": "monospace",
    "gothic": "fraktur",
}


def _range_map(upper_start, lower_start, digit_start=None):
    table = {}
    table.update({c: chr(upper_start + i) for i, c in enumerate(ascii_uppercase)})
    table.update({c: chr(lower_start + i) for i, c in enumerate(ascii_lowercase)})
    if digit_start is not None:
        table.update({c: chr(digit_start + i) for i, c in enumerate(digits)})
    return table


def _fullwidth_map():
    table = {chr(i): chr(i + 0xFEE0) for i in range(0x21, 0x7F)}
    table[" "] = "\u3000"
    return table


_TABLES = {
    "plain": {},
    "bold": _range_map(0x1D400, 0x1D41A, 0x1D7CE),
    "bold_italic": _range_map(0x1D468, 0x1D482, 0x1D7CE),
    "script": _range_map(0x1D4D0, 0x1D4EA, 0x1D7CE),
    "fraktur": _range_map(0x1D56C, 0x1D586, 0x1D7D8),
    "sans": _range_map(0x1D5A0, 0x1D5BA, 0x1D7E2),
    "monospace": _range_map(0x1D670, 0x1D68A, 0x1D7F6),
    "fullwidth": _fullwidth_map(),
}


def normalize_style(style):
    """Return a known style name, accepting a few friendly aliases."""
    key = str(style or "plain").strip().lower().replace("-", "_")
    key = _ALIASES.get(key, key)
    return key if key in _TABLES else "plain"


def is_known_style(style):
    key = str(style or "").strip().lower().replace("-", "_")
    return key in _TABLES or key in _ALIASES


def apply_style(text, style):
    table = _TABLES[normalize_style(style)]
    if not table:
        return str(text)
    return "".join(table.get(ch, ch) for ch in str(text))


def style_example(style, text="YourName 21:32"):
    return apply_style(text, style)
