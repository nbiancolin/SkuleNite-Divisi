# Dynamic Programming approach to solving page turns

from mscz_formatter.mscx.models import Page, Line
from mscz_formatter.mscx.models import MAX_PAGE_HEIGHT

def page_cost(page: Page, next_line: Line | None) -> float:

    def get_whitespace_penalty(page: Page) -> float:
        """Want to prefer pages that are full over those that are empty"""
        fullness = page.height / MAX_PAGE_HEIGHT
        return 1.0 - fullness
        

    if next_line is None:
        return 0.
    
