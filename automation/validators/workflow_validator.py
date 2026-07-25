from typing import Optional

from automation.engine.workflow_engine import Workflow, WorkflowStep, StepType


class ValidationResult:
    def __init__(self):
        self.valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, msg: str):
        self.valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class WorkflowValidator:
    """Validates workflow definitions before execution."""

    REQUIRED_STEP_FIELDS = {
        StepType.ACTION: ["name", "action"],
        StepType.CONDITION: ["name", "condition"],
        StepType.LOOP: ["name", "items", "body"],
        StepType.PARALLEL: ["name", "body"],
        StepType.DELAY: ["name", "delay"],
        StepType.APPROVAL: ["name"],
        StepType.SUB_WORKFLOW: ["name", "sub_workflow"],
        StepType.TRY_CATCH: ["name"],
    }

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult()

        if not workflow.id:
            result.add_error("Workflow must have an id")

        if not workflow.name:
            result.add_error("Workflow must have a name")

        if not workflow.steps:
            result.add_error("Workflow must have at least one step")
            return result

        step_names = set()
        for i, step in enumerate(workflow.steps):
            prefix = f"Step {i+1}"

            if not step.name:
                result.add_error(f"{prefix}: Step must have a name")

            if step.name in step_names:
                result.add_warning(f"{prefix}: Duplicate step name '{step.name}'")
            step_names.add(step.name)

            required = self.REQUIRED_STEP_FIELDS.get(step.step_type, [])
            for field in required:
                val = getattr(step, field, None)
                if not val and val != 0:
                    result.add_error(f"{prefix} ({step.name}): Missing required field '{field}'")

            if step.step_type == StepType.ACTION and step.action:
                if not step.action.replace(".", "").replace("_", "").isalnum():
                    result.add_warning(f"{prefix}: Action name '{step.action}' contains unusual characters")

            if step.timeout <= 0:
                result.add_warning(f"{prefix} ({step.name}): Timeout is {step.timeout}, should be positive")

            if step.retries > 5:
                result.add_warning(f"{prefix} ({step.name}): {step.retries} retries is excessive")

            if step.step_type == StepType.SUB_WORKFLOW:
                result.add_warning(f"{prefix} ({step.name}): Sub-workflow '{step.sub_workflow}' must be registered")

            if step.step_type == StepType.LOOP and not step.body:
                result.add_error(f"{prefix} ({step.name}): Loop must have a body")

            if step.step_type == StepType.CONDITION and not step.body and not step.else_body:
                result.add_warning(f"{prefix} ({step.name}): Condition has no body or else_body")

        return result

    def validate_dict(self, data: dict) -> ValidationResult:
        try:
            workflow = Workflow.from_dict(data)
            return self.validate(workflow)
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Failed to parse workflow: {e}")
            return result


workflow_validator = WorkflowValidator()
