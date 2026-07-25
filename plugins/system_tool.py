import psutil

TOOL = {
    "name": "battery",
    "description": "Returns the current battery percentage."
}


def run():
    battery = psutil.sensors_battery()

    if battery:
        return f"Battery: {battery.percent}%"

    return "Battery information unavailable."
