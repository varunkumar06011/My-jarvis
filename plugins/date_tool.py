from datetime import datetime

TOOL = {
    "name": "date",
    "description": "Returns the current date."
}


def run():
    return datetime.now().strftime("%A, %d %B %Y")
