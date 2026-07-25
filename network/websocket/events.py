from enum import Enum


class WSEventType(str, Enum):
    WAKE_WORD_DETECTED = "WakeWordDetected"
    SPEECH_STARTED = "SpeechStarted"
    SPEECH_FINISHED = "SpeechFinished"
    LIFECYCLE_CHANGED = "LifecycleChanged"
    TASK_STARTED = "TaskStarted"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"
    HEALTH_CHANGED = "HealthChanged"
    HEALTH_CHECK_PASSED = "HealthCheckPassed"
    HEALTH_CHECK_FAILED = "HealthCheckFailed"
    NOTIFICATION_CREATED = "NotificationCreated"
    PLUGIN_LOADED = "PluginLoaded"
    LLM_RESPONSE = "LLMResponse"
    TOOL_EXECUTED = "ToolExecuted"
    APPLICATION_STARTED = "ApplicationStarted"
    APPLICATION_STOPPED = "ApplicationStopped"
    RECOVERY_SUCCEEDED = "RecoverySucceeded"
    RECOVERY_FAILED = "RecoveryFailed"
    RECOVERY_ESCALATED = "RecoveryEscalated"
    RECOVERY_NOTIFIED = "RecoveryNotified"
    # Automation events
    AUTOMATION_CREATED = "AutomationCreated"
    AUTOMATION_QUEUED = "AutomationQueued"
    AUTOMATION_STARTED = "AutomationStarted"
    AUTOMATION_PAUSED = "AutomationPaused"
    AUTOMATION_RESUMED = "AutomationResumed"
    AUTOMATION_APPROVAL_REQUESTED = "AutomationApprovalRequested"
    AUTOMATION_APPROVED = "AutomationApproved"
    AUTOMATION_REJECTED = "AutomationRejected"
    AUTOMATION_STEP_STARTED = "AutomationStepStarted"
    AUTOMATION_STEP_COMPLETED = "AutomationStepCompleted"
    AUTOMATION_RETRY = "AutomationRetry"
    AUTOMATION_ROLLBACK = "AutomationRollback"
    AUTOMATION_COMPLETED = "AutomationCompleted"
    AUTOMATION_FAILED = "AutomationFailed"
    AUTOMATION_CANCELLED = "AutomationCancelled"
    AUTOMATION_SCHEDULED = "AutomationScheduled"


ALL_EVENTS = [e.value for e in WSEventType]
