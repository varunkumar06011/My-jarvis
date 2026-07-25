import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from automation.engine.context import AutomationContext
from automation.engine.rollback import RollbackManager
from automation.engine.artifacts import artifact_manager
from automation.plugins.base import AutomationPlugin, RiskLevel


class RestaurantPlugin(AutomationPlugin):
    """Restaurant/POS automation plugin — important for Softshape work."""

    def __init__(self):
        super().__init__()
        self.name = "Restaurant"
        self.description = "Restaurant/POS: print receipt, daily report, menu sync, order processing"
        self.version = "1.0"
        self.author = "Jarvis"

    def initialize(self):
        self.register_action("restaurant.print_receipt", self.print_receipt, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("restaurant.daily_report", self.daily_report, RiskLevel.SAFE)
        self.register_action("restaurant.menu_sync", self.menu_sync, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("restaurant.process_order", self.process_order, RiskLevel.MEDIUM, requires_rollback=True)
        self.register_action("restaurant.kot_print", self.print_kot, RiskLevel.SAFE)
        self.register_action("restaurant.bill_calc", self.calculate_bill, RiskLevel.SAFE)
        self.register_action("restaurant.table_status", self.table_status, RiskLevel.SAFE)
        self.register_action("restaurant.inventory_check", self.inventory_check, RiskLevel.SAFE)
        self.register_action("restaurant.sales_summary", self.sales_summary, RiskLevel.SAFE)
        self.register_action("restaurant.generate_qr", self.generate_qr, RiskLevel.SAFE)

        self.register_workflow({
            "id": "restaurant_end_of_day",
            "name": "Restaurant End of Day",
            "description": "Generate daily report, sales summary, print closing report",
            "version": "1.0",
            "variables": {"date": ""},
            "steps": [
                {"name": "daily_report", "type": "action", "action": "restaurant.daily_report", "params": {"date": "{{date}}"}},
                {"name": "sales_summary", "type": "action", "action": "restaurant.sales_summary", "params": {"date": "{{date}}"}},
                {"name": "inventory", "type": "action", "action": "restaurant.inventory_check", "params": {}},
                {"name": "approval", "type": "approval", "approval_summary": "Approve end-of-day closing report printing"},
                {"name": "print", "type": "action", "action": "office.create", "params": {"type": "pdf", "name": "daily_closing", "content": "End of Day Report"}},
            ],
        })

        self.register_workflow({
            "id": "restaurant_order_flow",
            "name": "Restaurant Order Flow",
            "description": "Process order, calculate bill, print KOT, print receipt",
            "version": "1.0",
            "variables": {"order_id": "", "table": "1", "items": []},
            "steps": [
                {"name": "process_order", "type": "action", "action": "restaurant.process_order", "params": {"order_id": "{{order_id}}", "table": "{{table}}", "items": "{{items}}"}},
                {"name": "kot", "type": "action", "action": "restaurant.kot_print", "params": {"order_id": "{{order_id}}", "table": "{{table}}"}},
                {"name": "bill", "type": "action", "action": "restaurant.bill_calc", "params": {"order_id": "{{order_id}}"}},
                {"name": "receipt", "type": "action", "action": "restaurant.print_receipt", "params": {"order_id": "{{order_id}}"}},
            ],
        })

    def print_receipt(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        order_id = params.get("order_id", "")
        printer = params.get("printer", "")
        content = params.get("content", f"Receipt #{order_id}\nThank you for dining with us!")
        try:
            from automation.printer.controller import printer_engine
            if printer_engine._check_win32():
                import win32print
                handle = win32print.OpenPrinter(printer or win32print.GetDefaultPrinter())
                try:
                    win32print.StartDocPrinter(handle, 1, {"DocName": f"Receipt_{order_id}"})
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, content.encode("utf-8"))
                    win32print.EndPagePrinter(handle)
                    win32print.EndDocPrinter(handle)
                finally:
                    win32print.ClosePrinter(handle)
                return {"status": "ok", "order_id": order_id, "printer": printer}
        except Exception:
            pass
        return {"status": "ok", "order_id": order_id, "method": "fallback", "content": content}

    def daily_report(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        report = {
            "date": date,
            "total_orders": params.get("total_orders", 0),
            "total_revenue": params.get("total_revenue", 0),
            "total_tax": params.get("total_tax", 0),
            "total_discounts": params.get("total_discounts", 0),
            "net_revenue": params.get("net_revenue", 0),
            "payment_modes": params.get("payment_modes", {"cash": 0, "card": 0, "upi": 0}),
        }
        ctx.set_var("daily_report", report)
        artifact = artifact_manager.save_file(
            name=f"daily_report_{date}",
            content=json.dumps(report, indent=2).encode(),
            automation_id=ctx.automation_id,
            extension="json",
        )
        return {"status": "ok", "report": report, "artifact_id": artifact.id}

    def menu_sync(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        source = params.get("source", "")
        menu_data = params.get("menu", [])
        if source:
            try:
                with open(source, "r", encoding="utf-8") as f:
                    menu_data = json.load(f)
            except Exception:
                pass

        dest = params.get("destination", "data/menu.json")
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        old_menu = None
        if Path(dest).exists():
            old_menu = Path(dest).read_text(encoding="utf-8")
            rollback.register("restaurant.menu_sync", lambda: Path(dest).write_text(old_menu, encoding="utf-8"), f"Restore old menu")

        with open(dest, "w", encoding="utf-8") as f:
            json.dump(menu_data, f, indent=2, ensure_ascii=False)

        return {"status": "ok", "items_synced": len(menu_data) if isinstance(menu_data, list) else 0, "destination": dest}

    def process_order(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        order_id = params.get("order_id", f"ORD-{int(time.time())}")
        table = params.get("table", "")
        items = params.get("items", [])

        subtotal = sum(i.get("price", 0) * i.get("qty", 1) for i in items)
        tax_rate = params.get("tax_rate", 0.05)
        tax = round(subtotal * tax_rate, 2)
        discount = params.get("discount", 0)
        total = round(subtotal + tax - discount, 2)

        order = {
            "order_id": order_id,
            "table": table,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "discount": discount,
            "total": total,
            "timestamp": datetime.now().isoformat(),
        }
        ctx.set_var("current_order", order)
        return {"status": "ok", "order": order}

    def print_kot(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        order_id = params.get("order_id", "")
        table = params.get("table", "")
        items = ctx.get_var("current_order", {}).get("items", params.get("items", []))

        kot_content = f"KITCHEN ORDER TICKET\nTable: {table}\nOrder: {order_id}\n\n"
        for item in items:
            kot_content += f"  {item.get('qty', 1)}x {item.get('name', 'Unknown')}\n"
        kot_content += f"\nTime: {datetime.now().strftime('%H:%M:%S')}"

        return {"status": "ok", "kot": kot_content, "order_id": order_id}

    def calculate_bill(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        order = ctx.get_var("current_order", {})
        if not order:
            items = params.get("items", [])
            subtotal = sum(i.get("price", 0) * i.get("qty", 1) for i in items)
            tax = round(subtotal * 0.05, 2)
            total = subtotal + tax
            return {"status": "ok", "subtotal": subtotal, "tax": tax, "total": total}
        return {"status": "ok", "subtotal": order.get("subtotal"), "tax": order.get("tax"), "total": order.get("total")}

    def table_status(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        tables = params.get("tables", [])
        if not tables:
            tables = [{"table": str(i), "status": "available" if i % 3 != 0 else "occupied"} for i in range(1, 21)]
        return {"status": "ok", "tables": tables}

    def inventory_check(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        items = params.get("items", [])
        low_stock = [i for i in items if i.get("stock", 0) < i.get("threshold", 10)]
        return {"status": "ok", "total_items": len(items), "low_stock": low_stock, "need_reorder": len(low_stock) > 0}

    def sales_summary(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        summary = {
            "date": date,
            "peak_hours": params.get("peak_hours", ["12:00-14:00", "19:00-21:00"]),
            "top_items": params.get("top_items", []),
            "total_bills": params.get("total_bills", 0),
            "average_bill": params.get("average_bill", 0),
            "dine_in": params.get("dine_in", 0),
            "takeaway": params.get("takeaway", 0),
            "delivery": params.get("delivery", 0),
        }
        ctx.set_var("sales_summary", summary)
        return {"status": "ok", "summary": summary}

    def generate_qr(self, params: dict, ctx: AutomationContext, rollback: RollbackManager) -> dict:
        data = params.get("data", "")
        name = params.get("name", "qr_code")
        try:
            import qrcode
            from io import BytesIO
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            artifact = artifact_manager.save_file(name, buf.getvalue(), ctx.automation_id, "png")
            return {"status": "ok", "artifact_id": artifact.id, "data": data}
        except ImportError:
            return {"status": "error", "error": "qrcode package not installed. Run: pip install qrcode[pil]"}
