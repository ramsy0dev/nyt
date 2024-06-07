import re

def parse_range_header(header_value: str) -> tuple[int, int]:
    """
    Parses the Range header value to extract start and end byte positions.
    Assumes the format is "bytes=start-end".
    """
    match = re.match(r"bytes=(\d+)-(\d+)", header_value)
    if match:
        start, end = map(int, match.groups())
        return start, end
    return 0, None
