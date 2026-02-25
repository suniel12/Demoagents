"""Technical tools — check system status, look up error codes."""

from agents import function_tool


@function_tool
def check_system_status() -> str:
    """Check the current system status of all CloudSync services."""
    return (
        "CloudSync System Status:\n"
        "  - Sync Service: ✅ Operational\n"
        "  - API Gateway: ✅ Operational\n"
        "  - Web Dashboard: ✅ Operational\n"
        "  - Mobile App: ⚠️ Degraded (intermittent latency)\n"
        "  - Integrations: ✅ Operational\n"
        "Last updated: 2024-02-15T10:30:00Z"
    )


@function_tool
def lookup_error_code(error_code: str) -> str:
    """Look up the meaning and resolution for a CloudSync error code."""
    errors = {
        "E-SYNC-001": {
            "meaning": "File conflict detected during sync",
            "fix": "Open the file in CloudSync and choose which version to keep.",
        },
        "E-SYNC-003": {
            "meaning": "Upload failed — file too large",
            "fix": "Files over 5GB require Business or Enterprise plan. Split the file or upgrade.",
        },
        "E-AUTH-001": {
            "meaning": "Invalid credentials",
            "fix": "Reset your password via Settings > Security > Reset Password.",
        },
        "E-AUTH-003": {
            "meaning": "Account locked due to too many failed attempts",
            "fix": "Wait 30 minutes or contact Account support to unlock.",
        },
    }
    info = errors.get(error_code.upper())
    if not info:
        return f"Unknown error code: {error_code}. Please check the format (e.g., E-SYNC-001)."
    return f"Error {error_code}: {info['meaning']}\nResolution: {info['fix']}"
