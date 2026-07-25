import threading
import time
import uuid
from enum import Enum
from typing import Optional


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    MODIFIED = "modified"


class ApprovalRequest:
    def __init__(
        self,
        automation_id: str,
        action: str,
        summary: str,
        risk_level: str = "high",
        timeout: float = 120,
    ):
        self.id = uuid.uuid4().hex[:12]
        self.automation_id = automation_id
        self.action = action
        self.summary = summary
        self.risk_level = risk_level
        self.timeout = timeout
        self.status = ApprovalStatus.PENDING
        self.created_at = time.time()
        self.resolved_at: Optional[float] = None
        self.modified_params: Optional[dict] = None
        self._event = threading.Event()

    def approve(self):
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = time.time()
        self._event.set()

    def reject(self):
        self.status = ApprovalStatus.REJECTED
        self.resolved_at = time.time()
        self._event.set()

    def modify(self, params: dict):
        self.status = ApprovalStatus.MODIFIED
        self.modified_params = params
        self.resolved_at = time.time()
        self._event.set()

    def timeout_expired(self):
        self.status = ApprovalStatus.TIMEOUT
        self.resolved_at = time.time()
        self._event.set()

    def wait(self, timeout: Optional[float] = None) -> ApprovalStatus:
        wait_timeout = timeout or self.timeout
        self._event.wait(timeout=wait_timeout)
        if self.status == ApprovalStatus.PENDING:
            self.timeout_expired()
        return self.status

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "automation_id": self.automation_id,
            "action": self.action,
            "summary": self.summary,
            "risk_level": self.risk_level,
            "status": self.status.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "modified_params": self.modified_params,
        }


class ApprovalEngine:
    def __init__(self):
        self._pending: dict[str, ApprovalRequest] = {}
        self._lock = threading.Lock()
        self._on_request = None

    def set_callback(self, callback):
        """Set a callback fired when an approval request is created (e.g. GUI dialog)."""
        self._on_request = callback

    def request(
        self,
        automation_id: str,
        action: str,
        summary: str,
        risk_level: str = "high",
        timeout: float = 120,
    ) -> ApprovalRequest:
        req = ApprovalRequest(automation_id, action, summary, risk_level, timeout)
        with self._lock:
            self._pending[req.id] = req

        if self._on_request:
            try:
                self._on_request(req)
            except Exception as e:
                print(f"[Approval] Callback error: {e}")

        return req

    def approve(self, request_id: str) -> bool:
        with self._lock:
            req = self._pending.get(request_id)
        if req and req.status == ApprovalStatus.PENDING:
            req.approve()
            return True
        return False

    def reject(self, request_id: str) -> bool:
        with self._lock:
            req = self._pending.get(request_id)
        if req and req.status == ApprovalStatus.PENDING:
            req.reject()
            return True
        return False

    def modify(self, request_id: str, params: dict) -> bool:
        with self._lock:
            req = self._pending.get(request_id)
        if req and req.status == ApprovalStatus.PENDING:
            req.modify(params)
            return True
        return False

    def get_pending(self) -> list[dict]:
        with self._lock:
            return [
                r.to_dict() for r in self._pending.values()
                if r.status == ApprovalStatus.PENDING
            ]

    def get_request(self, request_id: str) -> Optional[dict]:
        with self._lock:
            req = self._pending.get(request_id)
            return req.to_dict() if req else None

    def cleanup(self):
        with self._lock:
            expired = [
                rid for rid, r in self._pending.items()
                if r.status != ApprovalStatus.PENDING
            ]
            for rid in expired:
                del self._pending[rid]


approval_engine = ApprovalEngine()
