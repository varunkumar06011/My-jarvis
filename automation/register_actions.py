"""Register all automation action handlers with the workflow engine."""
from automation.engine.automation_engine import automation_engine


def register_all_actions():
    """Register all built-in automation actions."""

    # ── Browser ──
    from automation.browser.controller import browser_automation
    automation_engine.register_action("browser.open", browser_automation.open)
    automation_engine.register_action("browser.navigate", browser_automation.navigate)
    automation_engine.register_action("browser.click", browser_automation.click)
    automation_engine.register_action("browser.type", browser_automation.type_text)
    automation_engine.register_action("browser.screenshot", browser_automation.screenshot)
    automation_engine.register_action("browser.get_text", browser_automation.get_text)
    automation_engine.register_action("browser.get_dom", browser_automation.get_dom)
    automation_engine.register_action("browser.wait_for", browser_automation.wait_for)
    automation_engine.register_action("browser.download", browser_automation.download)
    automation_engine.register_action("browser.export_pdf", browser_automation.export_pdf)
    automation_engine.register_action("browser.close", browser_automation.close)

    # ── Windows ──
    from automation.windows.controller import windows_automation
    automation_engine.register_action("windows.launch_app", windows_automation.launch_app)
    automation_engine.register_action("windows.close_app", windows_automation.close_app)
    automation_engine.register_action("windows.list_processes", windows_automation.list_processes)
    automation_engine.register_action("windows.clipboard_get", windows_automation.clipboard_get)
    automation_engine.register_action("windows.clipboard_set", windows_automation.clipboard_set)
    automation_engine.register_action("windows.screenshot", windows_automation.screenshot)
    automation_engine.register_action("windows.set_volume", windows_automation.set_volume)
    automation_engine.register_action("windows.open_explorer", windows_automation.open_explorer)
    automation_engine.register_action("windows.lock_screen", windows_automation.lock_screen)
    automation_engine.register_action("windows.get_installed_apps", windows_automation.get_installed_apps)

    # ── Filesystem ──
    from automation.filesystem.controller import filesystem_engine
    automation_engine.register_action("fs.read", filesystem_engine.read)
    automation_engine.register_action("fs.read_binary", filesystem_engine.read_binary)
    automation_engine.register_action("fs.write", filesystem_engine.write)
    automation_engine.register_action("fs.copy", filesystem_engine.copy)
    automation_engine.register_action("fs.move", filesystem_engine.move)
    automation_engine.register_action("fs.rename", filesystem_engine.rename)
    automation_engine.register_action("fs.delete", filesystem_engine.delete)
    automation_engine.register_action("fs.search", filesystem_engine.search)
    automation_engine.register_action("fs.hash", filesystem_engine.hash_file)
    automation_engine.register_action("fs.compress", filesystem_engine.compress)
    automation_engine.register_action("fs.extract", filesystem_engine.extract)
    automation_engine.register_action("fs.list_dir", filesystem_engine.list_dir)

    # ── Terminal ──
    from automation.terminal.controller import terminal_engine
    automation_engine.register_action("terminal.execute", terminal_engine.execute)
    automation_engine.register_action("terminal.safe_execute", terminal_engine.safe_execute)
    automation_engine.register_action("terminal.stream", terminal_engine.stream_execute)

    # ── Docker ──
    from automation.docker.controller import docker_engine
    automation_engine.register_action("docker.ps", docker_engine.ps)
    automation_engine.register_action("docker.images", docker_engine.images)
    automation_engine.register_action("docker.logs", docker_engine.logs)
    automation_engine.register_action("docker.restart", docker_engine.restart)
    automation_engine.register_action("docker.stop", docker_engine.stop)
    automation_engine.register_action("docker.start", docker_engine.start)
    automation_engine.register_action("docker.compose_up", docker_engine.compose_up)
    automation_engine.register_action("docker.compose_down", docker_engine.compose_down)
    automation_engine.register_action("docker.stats", docker_engine.stats)
    automation_engine.register_action("docker.exec", docker_engine.exec_cmd)
    automation_engine.register_action("docker.cleanup", docker_engine.cleanup)

    # ── Database ──
    from automation.database.controller import database_engine
    automation_engine.register_action("db.query", database_engine.query)
    automation_engine.register_action("db.schema", database_engine.schema)
    automation_engine.register_action("db.explain", database_engine.explain)
    automation_engine.register_action("db.export_csv", database_engine.export_csv)

    # ── Printer ──
    from automation.printer.controller import printer_engine
    automation_engine.register_action("printer.list", printer_engine.list_printers)
    automation_engine.register_action("printer.get_default", printer_engine.get_default)
    automation_engine.register_action("printer.set_default", printer_engine.set_default)
    automation_engine.register_action("printer.get_jobs", printer_engine.get_jobs)
    automation_engine.register_action("printer.cancel_job", printer_engine.cancel_job)
    automation_engine.register_action("printer.pause", printer_engine.pause_printer)
    automation_engine.register_action("printer.resume", printer_engine.resume_printer)
    automation_engine.register_action("printer.print", printer_engine.print_file)
    automation_engine.register_action("printer.test_page", printer_engine.print_test_page)

    # ── Office ──
    from automation.office.controller import office_engine
    automation_engine.register_action("office.create", office_engine.create_document)
    automation_engine.register_action("office.read", office_engine.read_document)

    # ── Macro Recorder ──
    from automation.recorder.controller import macro_recorder
    automation_engine.register_action("macro.replay", macro_recorder.replay)

    print("[Automation] All core action handlers registered")

    # ── Load automation plugins ──
    from automation.plugins.base import plugin_loader
    loaded = plugin_loader.load_all()

    for plugin_name in loaded:
        plugin = plugin_loader.get_plugin(plugin_name)
        if plugin:
            # Register actions
            for action_name, handler in plugin.actions.items():
                automation_engine.register_action(action_name, handler)

            # Register policies
            for action_name, policy in plugin.policies.items():
                automation_engine.policy_engine.register(policy)

            # Register workflows
            from automation.engine.workflow_engine import Workflow
            for wf_data in plugin.workflows:
                workflow = Workflow.from_dict(wf_data)
                automation_engine.register_workflow(workflow)

    print(f"[Automation] {len(loaded)} plugins loaded with {sum(len(p.actions) for p in plugin_loader._loaded.values())} actions")
