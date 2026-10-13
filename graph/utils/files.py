import logging
from pathlib import Path

logger = logging.getLogger(__name__)

WORK_DIR = None


def update_work_dir(work_dir):
    global WORK_DIR
    WORK_DIR = work_dir

def write_file(content, path='.', file_name='file.txt', encoding='utf-8'):
    """
    Write content to a file at the specified path.

    Args:
        content (str): The content to write to the file.
        path (str): The directory path where the file will be saved. Defaults to '.'.
        file_name (str): The name of the file. Defaults to 'file.txt'.
        encoding (str): The encoding to use for writing the file. Defaults to 'utf-8'.
    """
    global WORK_DIR
    if WORK_DIR is None:
        full_path = Path(path) / file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)
    else:
        full_path = Path(WORK_DIR) / path / file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding=encoding)

def write_plan(content, path='.', file_name='Plan.md', encoding='utf-8'):
    """
    Write the plan content to a file named 'Plan.md' at the specified path.

    Args:
        content (str): The plan content to write to the file.
        path (str): The directory path where the file will be saved. Defaults to '.'.
        file_name (str): The name of the file. Defaults to 'Plan.md'.
        encoding (str): The encoding to use for writing the file. Defaults to 'utf-8'.
    """
    logger.info("Writing plan to %s", Path(WORK_DIR) / path / file_name if WORK_DIR else Path(path) / file_name)
    write_file(content, path=f"{path}/docs", file_name=file_name, encoding=encoding)
