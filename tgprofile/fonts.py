"""Unicode 花体字转换。

Telegram 本身不支持选字体，这里用 Unicode 数学字母数字符号区块（以及少数历史遗留的
Letterlike Symbols 码位）里长得像粗体/斜体/手写/哥特体/双线体等风格的字符，逐字替换
A-Z/a-z/0-9，视觉上就像换了字体。只处理 ASCII 字母数字，其它字符（emoji、中文、
标点）原样保留。
"""

_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_DIGIT = "0123456789"


def _seq(start, chars):
    """从 start 码位开始，按顺序给 chars 里每个字符分配一个码位。"""
    return {c: chr(start + i) for i, c in enumerate(chars)}


def _seq_with_holes(start, holes, chars):
    """同 _seq，但 holes={序号: 码位} 会覆盖掉那几个位置（历史遗留区块里的空洞）。"""
    return {c: chr(holes[i]) if i in holes else chr(start + i)
            for i, c in enumerate(chars)}


def _merge(*tables):
    merged = {}
    for t in tables:
        merged.update(t)
    return merged


_STYLE_TABLES = {
    "bold": _merge(
        _seq(0x1D400, _UPPER), _seq(0x1D41A, _LOWER), _seq(0x1D7CE, _DIGIT)),
    "italic": _merge(
        _seq(0x1D434, _UPPER),
        _seq_with_holes(0x1D44E, {7: 0x210E}, _LOWER)),          # h -> ℎ
    "bold_italic": _merge(
        _seq(0x1D468, _UPPER), _seq(0x1D482, _LOWER)),
    "script": _merge(
        _seq_with_holes(0x1D49C, {
            1: 0x212C, 4: 0x2130, 5: 0x2131, 7: 0x210B,
            8: 0x2110, 11: 0x2112, 12: 0x2133, 17: 0x211B,
        }, _UPPER),
        _seq_with_holes(0x1D4B6, {11: 0x2113}, _LOWER)),          # l -> ℓ
    "bold_script": _merge(
        _seq(0x1D4D0, _UPPER), _seq(0x1D4EA, _LOWER)),
    "fraktur": _merge(
        _seq_with_holes(0x1D504, {
            2: 0x212D, 7: 0x210C, 8: 0x2111, 17: 0x211C,
        }, _UPPER),
        _seq(0x1D51E, _LOWER)),
    "double_struck": _merge(
        _seq_with_holes(0x1D538, {
            2: 0x2102, 7: 0x210D, 13: 0x2115, 15: 0x2119,
            16: 0x211A, 17: 0x211D, 25: 0x2124,
        }, _UPPER),
        _seq(0x1D552, _LOWER),
        _seq(0x1D7D8, _DIGIT)),
    "sans_bold": _merge(
        _seq(0x1D5D4, _UPPER), _seq(0x1D5EE, _LOWER), _seq(0x1D7EC, _DIGIT)),
    "monospace": _merge(
        _seq(0x1D670, _UPPER), _seq(0x1D68A, _LOWER), _seq(0x1D7F6, _DIGIT)),
    "fullwidth": _merge(
        _seq(0xFF21, _UPPER), _seq(0xFF41, _LOWER), _seq(0xFF10, _DIGIT)),
    "circled": _merge(
        _seq(0x24B6, _UPPER), _seq(0x24D0, _LOWER),
        _seq(0x2460, "123456789"), {"0": chr(0x24EA)}),
}

_TRANSLATE_TABLES = {name: str.maketrans(table) for name, table in _STYLE_TABLES.items()}

STYLE_NAMES = sorted(_TRANSLATE_TABLES)


def apply_font(text, style):
    """按 style 转换 text；style 为空/'none'/未知值时原样返回。"""
    if not style or style in ("none", "plain"):
        return text
    table = _TRANSLATE_TABLES.get(style)
    return text.translate(table) if table else text


def preview(style, sample="ABCabc123 你好"):
    return apply_font(sample, style)
