import os
import logging

def configure_logger(log_path: str, level: int = logging.INFO):
    """
    Create the directory/file (if needed) and set up handlers on a shared logger.
    """
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    open(log_path, "a").close()

    logging.basicConfig(
        filename=log_path,
        filemode='w',
        level=level,
        format="%(asctime)s | %(levelname)8s | %(filename)16s:%(lineno)4d | %(message)s"
    )

def print_in_column(text: str, width: int):
    for line in text.splitlines():
        start = 0
        while start < len(line):
            chunk = line[start:start+width]
            print(chunk.ljust(width))
            start += width

def pretty_section(title, body):
    sep = "=" * 70
    print(f"\n{sep}\n{title}\n{sep}\n{body}")