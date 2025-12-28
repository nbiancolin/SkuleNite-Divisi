import subprocess
from django.conf import settings

def _get_container_name()-> str:
    if settings.DEBUG:
        return "skulenite-divisi-musescore-headless-1"
    return "app-musescore-headless-1"

def render_score(input_path: str, output_path: str | None = None, *args, timeout=120):
    """Helper function to interface with the headless docker container running MuseScore."""
    cmd = [
        "docker-compose", "exec",
        _get_container_name(),
        "timeout", str(timeout),
        "musescore",
        input_path,
    ]
    if output_path:
        cmd += ["-o", output_path]
    cmd += list(args)
    subprocess.run(cmd, check=True)
