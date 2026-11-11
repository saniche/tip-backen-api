import re
from datetime import date
from typing import Annotated

from pydantic import BeforeValidator


def _validate_iso_date(value: object) -> object:
    if isinstance(value, str) and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Date must use YYYY-MM-DD format")
    return value


ISODate = Annotated[date, BeforeValidator(_validate_iso_date)]
