from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


REQUIRES_APPROVAL = {RiskLevel.HIGH, RiskLevel.CRITICAL}
REQUIRES_ROLLBACK = {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}


DEFAULT_RISK_MAP = {
    # Browser
    "browser.open": RiskLevel.SAFE,
    "browser.navigate": RiskLevel.SAFE,
    "browser.click": RiskLevel.SAFE,
    "browser.type": RiskLevel.SAFE,
    "browser.screenshot": RiskLevel.SAFE,
    "browser.download": RiskLevel.MEDIUM,
    "browser.upload": RiskLevel.MEDIUM,
    "browser.close": RiskLevel.SAFE,
    # Windows
    "windows.launch_app": RiskLevel.SAFE,
    "windows.close_app": RiskLevel.MEDIUM,
    "windows.clipboard": RiskLevel.SAFE,
    "windows.screenshot": RiskLevel.SAFE,
    "windows.volume": RiskLevel.SAFE,
    "windows.brightness": RiskLevel.SAFE,
    "windows.power": RiskLevel.CRITICAL,
    "windows.registry": RiskLevel.CRITICAL,
    # Filesystem
    "fs.read": RiskLevel.SAFE,
    "fs.write": RiskLevel.MEDIUM,
    "fs.copy": RiskLevel.SAFE,
    "fs.move": RiskLevel.MEDIUM,
    "fs.rename": RiskLevel.MEDIUM,
    "fs.delete": RiskLevel.HIGH,
    "fs.compress": RiskLevel.SAFE,
    "fs.extract": RiskLevel.SAFE,
    # Terminal
    "terminal.execute": RiskLevel.HIGH,
    "terminal.safe_execute": RiskLevel.MEDIUM,
    # Docker
    "docker.ps": RiskLevel.SAFE,
    "docker.logs": RiskLevel.SAFE,
    "docker.restart": RiskLevel.HIGH,
    "docker.stop": RiskLevel.HIGH,
    "docker.rm": RiskLevel.CRITICAL,
    # Database
    "db.query": RiskLevel.SAFE,
    "db.write": RiskLevel.CRITICAL,
    # Office
    "office.create": RiskLevel.SAFE,
    "office.edit": RiskLevel.MEDIUM,
    "office.export": RiskLevel.SAFE,
    # Printer
    "printer.print": RiskLevel.MEDIUM,
    "printer.cancel_job": RiskLevel.MEDIUM,
}


class Policy:
    def __init__(
        self,
        action: str,
        risk: RiskLevel = RiskLevel.SAFE,
        timeout: float = 300,
        max_retries: int = 0,
        requires_rollback: bool = False,
        requires_approval: bool = False,
        allowed_in_sandbox: bool = True,
    ):
        self.action = action
        self.risk = risk
        self.timeout = timeout
        self.max_retries = max_retries
        self.requires_rollback = requires_rollback
        self.requires_approval = requires_approval
        self.allowed_in_sandbox = allowed_in_sandbox

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "risk": self.risk.value,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "requires_rollback": self.requires_rollback,
            "requires_approval": self.requires_approval,
            "allowed_in_sandbox": self.allowed_in_sandbox,
        }


class PolicyEngine:
    def __init__(self):
        self._policies: dict[str, Policy] = {}
        self._load_defaults()

    def _load_defaults(self):
        for action, risk in DEFAULT_RISK_MAP.items():
            requires_approval = risk in REQUIRES_APPROVAL
            requires_rollback = risk in REQUIRES_ROLLBACK
            timeout = 600 if risk == RiskLevel.CRITICAL else 300
            max_retries = 0 if risk == RiskLevel.CRITICAL else 2
            self._policies[action] = Policy(
                action=action,
                risk=risk,
                timeout=timeout,
                max_retries=max_retries,
                requires_rollback=requires_rollback,
                requires_approval=requires_approval,
                allowed_in_sandbox=risk != RiskLevel.CRITICAL,
            )

    def register(self, policy: Policy):
        self._policies[policy.action] = policy

    def get(self, action: str) -> Optional[Policy]:
        return self._policies.get(action)

    def get_risk(self, action: str) -> RiskLevel:
        policy = self._policies.get(action)
        if policy:
            return policy.risk
        return RiskLevel.MEDIUM

    def needs_approval(self, action: str) -> bool:
        policy = self._policies.get(action)
        if policy:
            return policy.requires_approval
        return self.get_risk(action) in REQUIRES_APPROVAL

    def needs_rollback(self, action: str) -> bool:
        policy = self._policies.get(action)
        if policy:
            return policy.requires_rollback
        return self.get_risk(action) in REQUIRES_ROLLBACK

    def get_timeout(self, action: str) -> float:
        policy = self._policies.get(action)
        if policy:
            return policy.timeout
        return 300

    def get_max_retries(self, action: str) -> int:
        policy = self._policies.get(action)
        if policy:
            return policy.max_retries
        return 2

    def list_policies(self) -> list[dict]:
        return [p.to_dict() for p in self._policies.values()]


policy_engine = PolicyEngine()
