# https://github.com/jimbobbennett/CircuitPython_Parse/blob/master/circuitpython_parse.py

import binascii

HEX_DIG = "0123456789ABCDEFabcdef"
HEX_TO_BYTE = None


def unquote_to_bytes(string):
    """unquote_to_bytes('abc%20def') -> b'abc def'."""
    # Note: strings are encoded as UTF-8. This is only an issue if it contains
    # unescaped non-ASCII characters, which URIs should not.
    if not string:
        # Is it a string-like object?
        # pylint: disable=W0104
        string.split
        return b""
    if isinstance(string, str):
        string = string.encode("utf-8")
    bits = string.split(b"%")
    if len(bits) == 1:
        return string
    res = [bits[0]]
    append = res.append
    # Delay the initialization of the table to not waste memory
    # if the function is never called
    # pylint: disable=W0603
    global HEX_TO_BYTE
    if HEX_TO_BYTE is None:
        HEX_TO_BYTE = {
            (a + b).encode(): binascii.unhexlify(a + b)
            for a in HEX_DIG
            for b in HEX_DIG
        }
    for item in bits[1:]:
        try:
            append(HEX_TO_BYTE[item[:2]])
            append(item[2:])
        except KeyError:
            append(b"%")
            append(item)
    return b"".join(res)


def unquote(string, encoding="utf-8", errors="replace"):
    """Replace %xx escapes by their single-character equivalent. The optional
    encoding and errors parameters specify how to decode percent-encoded
    sequences into Unicode characters, as accepted by the bytes.decode()
    method.
    By default, percent-encoded sequences are decoded with UTF-8, and invalid
    sequences are replaced by a placeholder character.
    unquote('abc%20def') -> 'abc def'.
    """
    if isinstance(string, bytes):
        return unquote_to_bytes(string).decode(encoding, errors)
    if "%" not in string:
        # pylint: disable=W0104
        string.split
        return string
    if encoding is None:
        encoding = "utf-8"
    if errors is None:
        errors = "replace"

    current_string = ""
    str_pos = 0

    while str_pos < len(string):
        char = string[str_pos]

        if char == "%":
            part = char + string[str_pos + 1] + string[str_pos + 2]
            decoded_part = unquote_to_bytes(part).decode(encoding, errors)
            current_string = current_string + decoded_part
            str_pos = str_pos + 3
        else:
            current_string = current_string + char
            str_pos = str_pos + 1

    return current_string


def unquote_plus(string, encoding="utf-8", errors="replace"):
    """Like unquote(), but also replace plus signs by spaces, as required for
    unquoting HTML form values.
    unquote_plus('%7e/abc+def') -> '~/abc def'
    """
    string = string.replace("+", " ")
    return unquote(string, encoding, errors)
