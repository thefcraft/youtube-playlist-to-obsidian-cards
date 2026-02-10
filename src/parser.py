from urllib.parse import urlparse, parse_qs


class ParserError(ValueError):
    def __init__(self, msg: str) -> None:
        self.msg: str = msg
        super().__init__(msg)


def parser_url_and_get_playlist_id(url: str) -> str:
    parsed = urlparse(url)

    # Basic URL validation
    if parsed.scheme not in ("http", "https"):
        raise ParserError("URL must start with http:// or https://")

    # Check domain
    if parsed.netloc not in ("www.youtube.com", "youtube.com"):
        raise ParserError("URL must be a YouTube URL")

    # Check playlist
    query = parse_qs(parsed.query)
    if "list" not in query:
        raise ParserError("URL must be a YouTube playlist")
    if len(query["list"]) != 1:
        raise ParserError("Invalid playlist URL")

    playlist_id, *_ = query["list"]
    return playlist_id


def get_json_from_content(
    content: bytes, /, *, name: bytes, prefix: bytes = b"window.", postfix: bytes = b""
) -> bytes:
    needle: bytes = prefix + name + postfix
    start: int = content.find(needle)
    if start == -1:
        raise ParserError("Prefix + name not found")
    pos: int = start + len(needle)
    pos_str_start: int = content.find(b'"', pos)  # NOTE: may be -1
    pos_dict_start: int = content.find(b"{", pos)  # NOTE: may be -1
    pos_list_start: int = content.find(b"[", pos)  # NOTE: may be -1
    try:
        min_start: int = min(
            i for i in (pos_str_start, pos_dict_start, pos_list_start) if i != -1
        )
    except ValueError as e:
        raise ParserError("Not a valid json") from e

    def parser_str(start: int) -> tuple[bytearray, int]:
        nonlocal content
        result: bytearray = bytearray(b'"')
        pos: int = start + 1
        escape: bool = False
        while pos < len(content):
            char: bytes = content[pos : pos + 1]
            result += char
            pos += 1
            if escape:
                escape = False
            elif char == b"\\":
                escape = True
            elif char == b'"':
                break
        else:
            raise ParserError("Unexpected end of content")

        return result, pos

    def parser_dict(start: int) -> tuple[bytes, int]:
        nonlocal content
        result: bytearray = bytearray(b"{")
        pos: int = start + 1
        while pos < len(content):
            char: bytes = content[pos : pos + 1]
            if char == b'"':  # string
                parsed, pos = parser_str(pos)
                result += parsed
            elif char == b"[":  # nested list
                parsed, pos = parser_list(pos)
                result += parsed
            elif char == b"{":  # nested dict
                parsed, pos = parser_dict(pos)
                result += parsed
            elif char == b"}":  # end of dict
                result += b"}"
                pos += 1
                break
            else:  # numbers, true, false, null, whitespace{ \t\n\r}, comma{,}, colon{:}
                result += char
                pos += 1

        else:
            raise ParserError("Unexpected end of content")
        return result, pos

    def parser_list(start: int) -> tuple[bytes, int]:
        nonlocal content
        result: bytearray = bytearray(b"[")
        pos: int = start + 1
        while pos < len(content):
            char: bytes = content[pos : pos + 1]
            if char == b'"':  # string
                parsed, pos = parser_str(pos)
                result += parsed
            elif char == b"[":  # nested list
                parsed, pos = parser_list(pos)
                result += parsed
            elif char == b"{":  # nested dict
                parsed, pos = parser_dict(pos)
                result += parsed
            elif char == b"]":  # end of list
                result += b"]"
                pos += 1
                break
            else:  # numbers, true, false, null, whitespace{ \t\n\r}, comma{,}
                result += char
                pos += 1
        else:
            raise ParserError("Unexpected end of content")
        return result, pos

    result: bytes = b""
    if min_start == pos_str_start:  # NOTE: its a string
        result, _ = parser_str(pos_str_start)
    elif min_start == pos_dict_start:  # NOTE: its a dict
        result, _ = parser_dict(pos_dict_start)
    elif min_start == pos_list_start:  # NOTE: its a list
        result, _ = parser_list(pos_list_start)
    else:
        raise RuntimeError("Something Went Wrong")
    return result
