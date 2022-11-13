from datetime import timedelta




def duration(elapsed, digits: int = 0):
    if isinstance(elapsed, timedelta):
        elapsed = elapsed.total_seconds()

    if elapsed > 60 * 60:
        hours = round(elapsed/(60*60), digits)
        return str(hours if digits>0 else int(hours)) + " hour"
    elif elapsed > 60:
        minutes = round(elapsed/60, digits)
        return str(minutes if digits>0 else int(minutes)) + " min"
    else:
        return str(elapsed if digits>0 else int(elapsed)) + " sec"