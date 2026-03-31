def preprocess(source: str):
    lines = source.splitlines()
    result = []
    for lineno, line in enumerate(lines, 1):
        line = line.ljust(72)
        if line[0].upper() in ("C", "*", "!"):
            continue
        if line.strip() == "":
            continue
        label = line[0:5].strip() or None
        continuation = line[5]
        code = line[6:72].rstrip()

        if continuation not in (" ", "0"):
            if result:
                prev = result[-1]
                result[-1] = (prev[0], prev[1], prev[2] + " " + code)
        else:
            result.append((lineno, label, code))
    return result
