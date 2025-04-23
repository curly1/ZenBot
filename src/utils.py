def print_in_column(text: str, width: int):
    for line in text.splitlines():
        start = 0
        while start < len(line):
            chunk = line[start:start+width]
            print(chunk.ljust(width))
            start += width