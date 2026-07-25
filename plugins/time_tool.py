from datetime import datetime

TOOL = {
    "name": "time",
    "description": "Returns the current time."
}


def run():
    return datetime.now().strftime("%I:%M:%S %p")
