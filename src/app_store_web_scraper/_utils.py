import sys
from datetime import datetime


def fromisoformat_utc(date_string: str) -> datetime:
    """
    Wrapper for :meth:datetime.fromisoformat: that handles timestamps
    with the "Z" suffix on Python < 3.11.
    """
    if sys.version_info < (3, 11):
        date_string = date_string.replace("Z", "+00:00")
    return datetime.fromisoformat(date_string)
