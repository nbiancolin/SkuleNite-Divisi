"""Collection of functions to interface with git on the local machine"""

import subprocess
from logging import getLogger

LOGGER = getLogger("git_interface")

def init_repo(repo_path: str):
    try:
        subprocess.run(["git", "init", "--bare", repo_path])
    except Exception:
        LOGGER.error("ERROR: could not initialize git repo", exc_info=True)
        return False
    return True

"""
Implement:

get_commit(commit_hash)
get_head_commit()
read_canonical(commit_hash)
write_commit(canonical_json, parent_commit, message)

"""