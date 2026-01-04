"""Collection of functions to interface with git on the local machine"""

import subprocess
import os
import json
import tempfile
from logging import getLogger

LOGGER = getLogger("git_interface")

def _is_valid_git_repo(path: str):
    """Check if folder is valid git repo."""
    if not os.path.isdir(path):
        return False
    # Check for .git directory (normal repo) or HEAD file (bare repo)
    git_dir = os.path.join(path, ".git")
    head_file = os.path.join(path, "HEAD")
    config_file = os.path.join(path, "config")
    # For bare repos, HEAD and config are in the root
    # For normal repos, .git directory exists
    return os.path.exists(head_file) or os.path.exists(git_dir) or os.path.exists(config_file)


class GitRepo:
    """ Class to contain all git operations needed for a repo """

    def __init__(self, path: str):
        self.path = path


    @classmethod
    def init(cls, path: str) -> "GitRepo":
        """Create a new bare repo for a score."""
        try:
            subprocess.run(["git", "init", "--bare", path])
        except Exception:
            LOGGER.error("ERROR: could not initialize git repo", exc_info=True)
            raise
        return GitRepo(path)


    def exists(self) -> bool:
        """ Check if the repo exists on disk"""
        return os.path.isdir(self.path) and _is_valid_git_repo(self.path)

# ---------- Reading ----------

    def get_head(self) -> str:
        """Return HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "--git-dir", self.path, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()
            if not commit_hash:
                raise ValueError("Repository has no commits")
            return commit_hash
        except subprocess.CalledProcessError as e:
            # Check if repo is empty (no commits)
            if "fatal: ambiguous argument 'HEAD'" in (e.stderr or "") or "fatal: your current branch" in (e.stderr or ""):
                raise ValueError("Repository has no commits") from e
            error_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr) if e.stderr else str(e)
            LOGGER.error(f"Failed to get HEAD commit: {error_msg}", exc_info=True)
            raise
        except Exception as e:
            LOGGER.error(f"Unexpected error getting HEAD: {e}", exc_info=True)
            raise

    def read_canonical(self, commit: str) -> dict:
        """Load canonical.json from a commit."""
        try:
            result = subprocess.run(
                ["git", "--git-dir", self.path, "show", f"{commit}:canonical.json"],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr) if e.stderr else str(e)
            LOGGER.error(f"Failed to read canonical.json from commit {commit}: {error_msg}", exc_info=True)
            raise
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse canonical.json: {e}", exc_info=True)
            raise
        except Exception as e:
            LOGGER.error(f"Unexpected error reading canonical.json: {e}", exc_info=True)
            raise

    def get_commit_info(self, commit: str) -> dict:
        """Author, date, message."""
        try:
            # Get commit info using git show with format string
            result = subprocess.run(
                [
                    "git",
                    "--git-dir",
                    self.path,
                    "show",
                    "--no-patch",
                    "--format=%an%n%ae%n%ad%n%s",
                    "--date=iso",
                    commit,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = result.stdout.strip().split("\n", 3)
            if len(lines) < 4:
                raise ValueError(f"Unexpected git output format: {result.stdout}")
            
            return {
                "author": lines[0],
                "email": lines[1],
                "date": lines[2],
                "message": lines[3] if len(lines) > 3 else "",
            }
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr) if e.stderr else str(e)
            LOGGER.error(f"Failed to get commit info for {commit}: {error_msg}", exc_info=True)
            raise
        except Exception as e:
            LOGGER.error(f"Unexpected error getting commit info: {e}", exc_info=True)
            raise

    # ---------- Writing ----------

    def commit_canonical(
        self,
        canonical: dict,
        parent: str,
        message: str,
        author: str,
    ) -> str:
        """Write canonical.json and return new commit hash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                # Write canonical.json to temp file
                canonical_path = os.path.join(tmp_dir, "canonical.json")
                with open(canonical_path, "w", encoding="utf-8") as f:
                    json.dump(canonical, f, indent=2, ensure_ascii=False)
                
                # Set up git environment for the bare repo
                # Use GIT_WORK_TREE to point to our temp directory
                env = os.environ.copy()
                env["GIT_DIR"] = self.path
                env["GIT_WORK_TREE"] = tmp_dir
                
                # Parse author string (format: "Name <email@example.com>" or just "Name")
                author_name = author
                author_email = f"{author}@divisi.local"
                if "<" in author and ">" in author:
                    parts = author.rsplit("<", 1)
                    if len(parts) == 2:
                        author_name = parts[0].strip()
                        author_email = parts[1].rstrip(">").strip()
                
                commit_env = env.copy()
                commit_env["GIT_AUTHOR_NAME"] = author_name
                commit_env["GIT_AUTHOR_EMAIL"] = author_email
                commit_env["GIT_COMMITTER_NAME"] = author_name
                commit_env["GIT_COMMITTER_EMAIL"] = author_email
                
                # If parent is provided, load its tree into the index first
                if parent:
                    subprocess.run(
                        ["git", "read-tree", parent],
                        env=env,
                        check=True,
                        capture_output=True,
                    )
                
                # Add the file to git (will update existing or add new)
                subprocess.run(
                    ["git", "add", "canonical.json"],
                    env=env,
                    check=True,
                    capture_output=True,
                )
                
                # Create commit
                subprocess.run(
                    ["git", "commit", "-m", message],
                    env=commit_env,
                    check=True,
                    capture_output=True,
                )
                
                # Get the commit hash
                commit_hash = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                
                return commit_hash
                    
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr) if e.stderr else str(e)
                LOGGER.error(
                    f"Failed to commit canonical.json: {error_msg}",
                    exc_info=True,
                )
                raise
            except Exception as e:
                LOGGER.error(f"Unexpected error committing canonical.json: {e}", exc_info=True)
                raise

    # ---------- Export ----------

    def export_mscz(self, commit: str, out_path: str):
        """Canonical → mscz."""

        #TODO: fill in with ScoreForge Code