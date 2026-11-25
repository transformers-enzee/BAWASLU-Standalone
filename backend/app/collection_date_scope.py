"""Explicit publication date verification without inferring a missing date."""
from datetime import date

def publication_in_window(value,start='',end=''):
    if not start and not end:return True
    try:day=date.fromisoformat(str(value or '')[:10]).isoformat()
    except (ValueError,TypeError):return False
    return (not start or day>=start) and (not end or day<=end)
