from plugins import time_tool, date_tool, system_tool, calculator_tool


def execute_time():
    return time_tool.run()


def execute_date():
    return date_tool.run()


def execute_battery():
    return system_tool.run()


def execute_calculator(expression):
    return calculator_tool.run(expression)
