import subprocess
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager

try:
    import win32print
    import win32api
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


class PrinterEngine:
    """Printer automation for Windows. Important for POS/restaurant work."""

    def _check_win32(self):
        if not _HAS_WIN32:
            raise RuntimeError("pywin32 not installed. Run: pip install pywin32")

    def list_printers(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        result = []
        for p in printers:
            result.append({"name": p[2], "port": p[1], "server": p[0] or "local"})
        return {"status": "ok", "count": len(result), "printers": result}

    def get_default(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        default = win32print.GetDefaultPrinter()
        return {"status": "ok", "default_printer": default}

    def set_default(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        name = params.get("name", "")
        old_default = win32print.GetDefaultPrinter()
        win32print.SetDefaultPrinter(name)
        rollback.register("printer.set_default", lambda: win32print.SetDefaultPrinter(old_default), f"Restore default to {old_default}")
        return {"status": "ok", "default_printer": name}

    def get_jobs(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        printer_name = params.get("name", win32print.GetDefaultPrinter())
        handle = win32print.OpenPrinter(printer_name)
        try:
            jobs = win32print.EnumJobs(handle, 0, -1, 1)
            return {"status": "ok", "printer": printer_name, "job_count": len(jobs), "jobs": jobs[:20]}
        finally:
            win32print.ClosePrinter(handle)

    def cancel_job(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        printer_name = params.get("name", win32print.GetDefaultPrinter())
        job_id = params.get("job_id", 0)
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.SetJob(handle, job_id, 0, None, win32print.JOB_CONTROL_CANCEL)
            return {"status": "ok", "cancelled_job": job_id}
        finally:
            win32print.ClosePrinter(handle)

    def pause_printer(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        printer_name = params.get("name", "")
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_PAUSE)
            rollback.register("printer.resume", lambda: win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_RESUME), f"Resume {printer_name}")
            return {"status": "ok", "paused": printer_name}
        finally:
            win32print.ClosePrinter(handle)

    def resume_printer(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        printer_name = params.get("name", "")
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_RESUME)
            return {"status": "ok", "resumed": printer_name}
        finally:
            win32print.ClosePrinter(handle)

    def print_file(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        file_path = params.get("file", "")
        printer = params.get("printer", "")
        win32api.ShellExecute(0, "printto", file_path, f'"{printer}"' if printer else None, ".", 0)
        return {"status": "ok", "file": file_path, "printer": printer}

    def print_test_page(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        self._check_win32()
        printer_name = params.get("name", win32print.GetDefaultPrinter())
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.SetPrinter(handle, 0, None, win32print.PRINTER_CONTROL_TEST_PAGE)
            return {"status": "ok", "printer": printer_name}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            win32print.ClosePrinter(handle)


printer_engine = PrinterEngine()
