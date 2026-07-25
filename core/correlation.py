import threading
import uuid
from contextlib import contextmanager
from typing import Optional


class CorrelationContext:
    """Thread-local correlation context for tracing events across the system."""

    _local = threading.local()

    @classmethod
    def get_request_id(cls) -> str:
        return getattr(cls._local, "request_id", "")

    @classmethod
    def get_session_id(cls) -> str:
        return getattr(cls._local, "session_id", "")

    @classmethod
    def get_conversation_id(cls) -> str:
        return getattr(cls._local, "conversation_id", "")

    @classmethod
    def get_automation_id(cls) -> str:
        return getattr(cls._local, "automation_id", "")

    @classmethod
    def set_request_id(cls, request_id: str):
        cls._local.request_id = request_id

    @classmethod
    def set_session_id(cls, session_id: str):
        cls._local.session_id = session_id

    @classmethod
    def set_conversation_id(cls, conversation_id: str):
        cls._local.conversation_id = conversation_id

    @classmethod
    def set_automation_id(cls, automation_id: str):
        cls._local.automation_id = automation_id

    @classmethod
    def generate_request_id(cls) -> str:
        rid = uuid.uuid4().hex[:12]
        cls.set_request_id(rid)
        return rid

    @classmethod
    def generate_conversation_id(cls) -> str:
        cid = uuid.uuid4().hex[:12]
        cls.set_conversation_id(cid)
        return cid

    @classmethod
    def generate_automation_id(cls) -> str:
        aid = uuid.uuid4().hex[:12]
        cls.set_automation_id(aid)
        return aid

    @classmethod
    def clear(cls):
        cls._local.request_id = ""
        cls._local.session_id = ""
        cls._local.conversation_id = ""
        cls._local.automation_id = ""

    @classmethod
    def snapshot(cls) -> dict:
        return {
            "request_id": cls.get_request_id(),
            "session_id": cls.get_session_id(),
            "conversation_id": cls.get_conversation_id(),
            "automation_id": cls.get_automation_id(),
        }

    @classmethod
    @contextmanager
    def request(cls, request_id: Optional[str] = None):
        """Context manager for an API request lifecycle."""
        old = cls.get_request_id()
        cls.set_request_id(request_id or uuid.uuid4().hex[:12])
        try:
            yield cls.get_request_id()
        finally:
            cls.set_request_id(old)

    @classmethod
    @contextmanager
    def conversation(cls, conversation_id: Optional[str] = None):
        """Context manager for a conversation lifecycle."""
        old = cls.get_conversation_id()
        cls.set_conversation_id(conversation_id or uuid.uuid4().hex[:12])
        try:
            yield cls.get_conversation_id()
        finally:
            cls.set_conversation_id(old)

    @classmethod
    @contextmanager
    def automation(cls, automation_id: Optional[str] = None):
        """Context manager for an automation workflow lifecycle."""
        old = cls.get_automation_id()
        cls.set_automation_id(automation_id or uuid.uuid4().hex[:12])
        try:
            yield cls.get_automation_id()
        finally:
            cls.set_automation_id(old)
