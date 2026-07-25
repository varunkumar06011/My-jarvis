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
    NOTIFICATION_CREATED = "NotificationCreated"
    PLUGIN_LOADED = "PluginLoaded"
    LLM_RESPONSE = "LLMResponse"
    TOOL_EXECUTED = "ToolExecuted"
    APPLICATION_STARTED = "ApplicationStarted"
    APPLICATION_STOPPED = "ApplicationStopped"


ALL_EVENTS = [e.value for e in WSEventType]
