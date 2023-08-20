from __future__ import annotations

import re

from enum import Enum

import emoji
from PIL import ImageFont

from typing import Final, List, NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import FontT

# This is actually way faster than it seems
_UNICODE_EMOJI_REGEX = '|'.join(map(re.escape, sorted(emoji.get_emoji_unicode_dict('en').values(), key=len, reverse=True)))
_DISCORD_EMOJI_REGEX = '<a?:[a-zA-Z0-9_]{2,32}:[0-9]{17,22}>'
_FEDI_EMOJI_REGEX = ':[a-zA-Z0-9_]+:'

EMOJI_REGEX: Final[re.Pattern[str]] = re.compile(f'({_UNICODE_EMOJI_REGEX}|{_DISCORD_EMOJI_REGEX}|{_FEDI_EMOJI_REGEX})')

__all__ = (
    'EMOJI_REGEX',
    'Node',
    'NodeType',
    'to_nodes',
    'getsize'
)


class NodeType(Enum):
    """|enum|

    Represents the type of a :class:`~.Node`.

    Attributes
    ----------
    text
        This node is a raw text node.
    emoji
        This node is a unicode emoji.
    discord_emoji
        This node is a Discord emoji.
    fedi_emoji
        This node is a Fediverse emoji.
    """

    text          = 0
    emoji         = 1
    discord_emoji = 2
    fedi_emoji    = 3


class Node(NamedTuple):
    """Represents a parsed node inside of a string.

    Attributes
    ----------
    type: :class:`~.NodeType`
        The type of this node.
    content: str
        The contents of this node.
    """

    type: NodeType
    content: str

    def __repr__(self) -> str:
        return f'<Node type={self.type.name!r} content={self.content!r}>'


def _parse_line(line: str, /, emojis: list = []) -> List[Node]:
    nodes = []

    for i, chunk in enumerate(EMOJI_REGEX.split(line)):
        print(i, chunk)
        if not chunk:
            continue

        if not i % 2:
            nodes.append(Node(NodeType.text, chunk))
            continue
        print(chunk)
        # fedi emojiであるかどうかチェックする
        if chunk.startswith(':') and chunk.endswith(':'):
            emoji_name = chunk.replace(':', '')
            for e in emojis:
                if e['name'] == emoji_name:
                    # 存在するならノード変換
                    node = Node(NodeType.fedi_emoji, e['url'])
                    break
            else:
                # 存在しない場合テキスト扱い
                node = Node(NodeType.text, chunk)
        elif len(chunk) > 18:  # This is guaranteed to be a Discord emoji
            node = Node(NodeType.discord_emoji, chunk.split(':')[-1][:-1])
        else:
            node = Node(NodeType.emoji, chunk)

        nodes.append(node)

    return nodes


def to_nodes(text: str, /, emojis: list = []) -> List[List[Node]]:
    """Parses a string of text into :class:`~.Node`s.

    This method will return a nested list, each element of the list
    being a list of :class:`~.Node`s and representing a line in the string.

    The string ``'Hello\nworld'`` would return something similar to
    ``[[Node('Hello')], [Node('world')]]``.

    Parameters
    ----------
    text: str
        The text to parse into nodes.

    Returns
    -------
    List[List[:class:`~.Node`]]
    """
    return [_parse_line(line, emojis=emojis) for line in text.splitlines()]

def PILF_getsize(font: ImageFont.FreeTypeFont, text):
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def getsize(
    text: str,
    font: FontT = None,
    *,
    spacing: int = 4,
    emoji_scale_factor: float = 1
) -> Tuple[int, int]:
    """Return the width and height of the text when rendered.
    This method supports multiline text.

    Parameters
    ----------
    text: str
        The text to use.
    font
        The font of the text.
    spacing: int
        The spacing between lines, in pixels.
        Defaults to `4`.
    emoji_scale_factor: float
        The rescaling factor for emojis.
        Defaults to `1`.
    """
    if font is None:
        font = ImageFont.load_default()

    x, y = 0, 0
    nodes = to_nodes(text)

    for line in nodes:
        this_x = 0
        for node in line:
            content = node.content

            if node.type is not NodeType.text:
                width = int(emoji_scale_factor * font.size)
            else:
                try:
                    width, _ = font.getsize(content)
                except:
                    # Pillow 10 compat
                    width, _ = PILF_getsize(font=font, text=content)

            this_x += width

        y += spacing + font.size

        if this_x > x:
            x = this_x

    return x, y - spacing
