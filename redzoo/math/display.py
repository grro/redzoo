from datetime import timedelta




def duration(elapsed_seconds, digits: int = 0) -> str:
    if isinstance(elapsed_seconds, timedelta):
        elapsed_seconds = elapsed_seconds.total_seconds()

    if elapsed_seconds > 60 * 60:
        hours = round(elapsed_seconds / (60 * 60), digits)
        return str(hours if digits>0 else int(hours)) + " hour"
    elif elapsed_seconds > 60:
        minutes = round(elapsed_seconds / 60, digits)
        return str(minutes if digits>0 else int(minutes)) + " min"
    else:
        seconds = round(elapsed_seconds, digits)
        return str(seconds if digits>0 else int(seconds)) + " sec"



def formatted_size(bytes, digits: int = 0) -> str:

    if bytes > (1000 * 1000):
        hours = round(bytes / (1000 * 1000), digits)
        return str(hours if digits>0 else int(hours)) + " MB"
    elif bytes > 1000:
        hours = round(bytes / (1000), digits)
        return str(hours if digits>0 else int(hours)) + " KB"
    else:
        bytes = round(bytes, digits)
        return str(bytes if digits>0 else int(bytes)) + " byte"