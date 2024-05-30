import datetime

def date_in_gmt() -> datetime.datetime:
    """
    Returns the current date.
    
    Args:
        None.
    
    Returns:
        datetime.datetime
    """
    return datetime.datetime.now()
