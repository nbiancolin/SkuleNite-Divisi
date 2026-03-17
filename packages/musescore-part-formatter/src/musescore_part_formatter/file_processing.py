from contextlib import contextmanager
from typing import Iterator, Tuple, List
import zipfile
import tempfile
import os


def _rezip_mscz(work_dir: str, output_path: str) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(work_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, work_dir)
                z.write(full_path, arcname)


@contextmanager
def unpack_mscz_to_tempdir(
    mscz_path: str, repack=True
) -> Iterator[Tuple[str, List[str]]]:
    """
    Unpack a .mscz (zip) into a temporary directory.
    On successful exit and if repack=True, rezip contents back into the same .mscz.
    """
    with tempfile.TemporaryDirectory() as work_dir:
        try:
            # --- unzip ---
            with zipfile.ZipFile(mscz_path, "r") as z:
                z.extractall(work_dir)
                mscx_files = [
                    os.path.join(work_dir, name)
                    for name in z.namelist()
                    if name.endswith(".mscx")
                ]

            yield work_dir, mscx_files

            if repack:
                _rezip_mscz(work_dir, mscz_path)

        except Exception:
            # don't overwrite original file if something goes wrong
            raise
