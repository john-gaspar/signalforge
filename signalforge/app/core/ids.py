import uuid


def generate_run_id() -> str:
    """Generate a unique run identifier."""
    return f"run_{uuid.uuid4().hex}"
