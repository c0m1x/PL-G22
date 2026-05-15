import re


_FREE_LABEL_RE = re.compile(r"^(\d+)\s+(.*)$")


def _strip_inline_comment(code: str) -> str:
    quote = None
    i = 0
    while i < len(code):
        ch = code[i]
        if quote is not None:
            if ch == quote:
                if quote == "'" and i + 1 < len(code) and code[i + 1] == "'":
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if ch in ("'", '"'):
            quote = ch
        elif ch == "!":
            return code[:i].rstrip()
        i += 1
    return code.rstrip()


def _is_comment_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return True
    if stripped.startswith("!"):
        return True
    if line[0] == "*":
        return True
    if line[0].upper() == "C":
        rest = line[1:].lstrip()
        if not rest:
            return True
        # Fixed-form comments use C/c in column 1. Keep free-form statements
        # such as CALL ... and C = 'x' as executable source.
        if line[1:2].isspace() and not rest.startswith(("=", "(", "+", "-", "*", "/", ",")):
            return True
    return False


def _free_form_line(line: str):
    code = _strip_inline_comment(line.strip())
    if not code:
        return None, ""
    match = _FREE_LABEL_RE.match(code)
    if match:
        return match.group(1), match.group(2).rstrip()
    return None, code


def preprocess(source: str):
    lines = source.splitlines()
    result = []
    last_mode = None
    for lineno, raw_line in enumerate(lines, 1):
        if _is_comment_line(raw_line):
            continue

        leading_spaces = len(raw_line) - len(raw_line.lstrip(" \t"))
        padded = raw_line.ljust(72)
        fixed_continuation = (
            last_mode == "fixed"
            and padded[0:5].strip() == ""
            and padded[5] not in (" ", "0")
            and (padded[5].isdigit() or padded[5] in ("+", "-", "&"))
        )

        if fixed_continuation:
            if result:
                code = _strip_inline_comment(padded[6:72].rstrip())
                prev = result[-1]
                result[-1] = (prev[0], prev[1], prev[2] + " " + code)
            continue

        fixed_label = padded[0:5].strip().isdigit() and padded[5] in (" ", "0")
        if leading_spaces >= 6 or fixed_label:
            label = padded[0:5].strip() or None
            code = _strip_inline_comment(padded[6:72].rstrip())
            result.append((lineno, label, code))
            last_mode = "fixed"
        else:
            label, code = _free_form_line(raw_line)
            if code:
                result.append((lineno, label, code))
                last_mode = "free"
    return result
