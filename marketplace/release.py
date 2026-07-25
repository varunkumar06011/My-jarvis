import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class ReleaseManager:
    def __init__(self):
        self.root = Path(".")
        self.dist_dir = self.root / "dist"
        self.dist_dir.mkdir(exist_ok=True)

    def create_version_tag(self, version: str) -> dict:
        tag = f"v{version}"
        try:
            subprocess.run(["git", "tag", tag], capture_output=True, cwd=self.root)
            return {"status": "ok", "tag": tag}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def build_exe(self, app_name: str = "Jarvis") -> dict:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller",
                 "--name", app_name,
                 "--windowed",
                 "--onefile",
                 "--add-data", "assets;assets",
                 "--add-data", "configs;configs",
                 "--add-data", "plugins;plugins",
                 "app/bootstrap.py"],
                capture_output=True, text=True, timeout=600,
                cwd=self.root,
            )
            if result.returncode == 0:
                return {"status": "ok", "output": result.stdout[-500:]}
            return {"status": "error", "output": result.stderr[-500:]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create_installer_script(self, version: str, app_name: str = "Jarvis") -> Path:
        iss_content = f"""#define MyAppName "{app_name}"
#define MyAppVersion "{version}"
#define MyAppExeName "{app_name}.exe"

[Setup]
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
OutputDir=dist
OutputBaseFilename={app_name}-{version}-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\\{app_name}\\{app_name}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "assets\\*"; DestDir: "{{app}}\\assets"; Flags: recursesubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\Uninstall {{#MyAppName}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "Launch {{#MyAppName}}"; Flags: nowait postinstall skipifsilent
"""
        iss_path = self.dist_dir / f"{app_name}-{version}.iss"
        iss_path.write_text(iss_content, encoding="utf-8")
        return iss_path

    def backup_config(self) -> dict:
        backup_dir = self.root / "backups" / f"config-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        files_to_backup = [
            "configs/config.py",
            ".env",
            "flags/flags.json",
            "data/learning/patterns.json",
            "data/learning/decisions.json",
            "data/learning/preferences.json",
            "data/marketplace/installed.json",
        ]

        copied = []
        for f in files_to_backup:
            src = self.root / f
            if src.exists():
                dst = backup_dir / Path(f).name
                shutil.copy2(src, dst)
                copied.append(f)

        return {"status": "ok", "backup_dir": str(backup_dir), "files": copied}

    def restore_config(self, backup_dir: str) -> dict:
        src_dir = Path(backup_dir)
        if not src_dir.exists():
            return {"error": "Backup directory not found"}

        restored = []
        for f in src_dir.iterdir():
            if f.name == "config.py":
                shutil.copy2(f, self.root / "configs" / "config.py")
                restored.append("configs/config.py")
            elif f.name == ".env":
                shutil.copy2(f, self.root / ".env")
                restored.append(".env")
            elif f.name == "flags.json":
                shutil.copy2(f, self.root / "flags" / "flags.json")
                restored.append("flags/flags.json")
            elif f.name in ("patterns.json", "decisions.json", "preferences.json"):
                shutil.copy2(f, self.root / "data" / "learning" / f.name)
                restored.append(f"data/learning/{f.name}")
            elif f.name == "installed.json":
                shutil.copy2(f, self.root / "data" / "marketplace" / "installed.json")
                restored.append("data/marketplace/installed.json")

        return {"status": "ok", "restored": restored}

    def list_backups(self) -> list[dict]:
        backups = []
        backup_root = self.root / "backups"
        if not backup_root.exists():
            return []

        for d in sorted(backup_root.iterdir(), reverse=True):
            if d.is_dir():
                files = list(d.iterdir())
                backups.append({
                    "dir": str(d),
                    "name": d.name,
                    "files": len(files),
                    "created": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
                })
        return backups

    def run_tests(self) -> dict:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                capture_output=True, text=True, timeout=300,
                cwd=self.root,
            )
            return {
                "status": "ok" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "output": result.stdout[-2000:],
                "errors": result.stderr[-1000:],
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def release_info(self) -> dict:
        from configs.config import APP_NAME, VERSION
        return {
            "app_name": APP_NAME,
            "version": VERSION,
            "python_version": sys.version,
            "platform": sys.platform,
            "dist_dir": str(self.dist_dir),
            "backups": len(self.list_backups()),
        }


release_manager = ReleaseManager()
