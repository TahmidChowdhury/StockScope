"""Same-directory temporary writes for local file storage."""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO


@contextmanager
def atomic_text_writer(path: Path) -> Iterator[TextIO]:
    """Replace path only after the temporary file has closed successfully."""
    handle = tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False)
    try:
        with handle:
            yield handle
        os.replace(handle.name, path)
    finally:
        Path(handle.name).unlink(missing_ok=True)
