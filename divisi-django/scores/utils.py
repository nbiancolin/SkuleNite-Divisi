def increment_version(version: str, version_type: str) -> str:
    """Helper to increment version string like v1.0.0"""
    if version_type not in ["major", "minor", "release"]:
        raise ValueError("Invalid version type")

    major, minor, patch = int(version[1]), int(version[3]), int(version[5])
    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    return f"v{major}.{minor}.{patch}"
