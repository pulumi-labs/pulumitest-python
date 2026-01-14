"""Python conversion of copy.go - File and directory copying utilities for Pulumi testing framework."""

import os
import platform
import unittest
import uuid
from pathlib import Path
from typing import Optional, Union
import logging

class FileOwner:
    """File ownership information."""
    def __init__(self, uid: int, gid: int):
        self.uid = uid
        self.gid = gid

def get_file_owner(file_path: Path) -> Optional[FileOwner]:
    """Get file owner information, returns None on Windows."""
    try:
        if platform.system() == 'Windows':
            return None
        stat_info = file_path.stat()
        return FileOwner(stat_info.st_uid, stat_info.st_gid)
    except (AttributeError, OSError):
        return None


def temp_dir_without_cleanup_on_failed_test(
    log: logging.Logger,
    context: Union["TestContext", unittest.TestCase],  # type: ignore[name-defined]
    prefix: str,
    temp_dir: str = ""
) -> str:
    """Create a temporary directory with conditional cleanup on test failure.

    Args:
        log: Logger for messages
        context: TestContext protocol or unittest.TestCase for cleanup registration
        prefix: Prefix for temp directory name
        temp_dir: Base directory for temp dir (default: ./tmp)

    Returns:
        Path to created temporary directory
    """
    # Import here to avoid circular dependency
    from .context import TestContext

    if temp_dir:
        base_dir = Path(temp_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
    else:
        base_dir = Path.cwd() / "tmp"
        base_dir.mkdir(exist_ok=True)

    # Create unique temp directory
    temp_path = base_dir / f"{prefix}_{uuid.uuid4().hex[:8]}"
    log.info(f"Creating temp directory {temp_path.name}")
    temp_path.mkdir(exist_ok=True)

    def cleanup_temp_dir() -> None:
        log.info(f"Removing temp directory {temp_path.name}")
        try:
            if temp_path.exists():
                for child in temp_path.rglob('*'):
                    if child.is_file() or child.is_symlink():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                temp_path.rmdir()
        except OSError:
            pass  # Ignore cleanup errors

    # Register cleanup based on context type
    if isinstance(context, TestContext):
        # Use TestContext protocol for cleanup
        context.add_cleanup(cleanup_temp_dir)
    elif isinstance(context, unittest.TestCase):
        # Use unittest tearDown for cleanup (only runs on success)
        context.tearDown = cleanup_temp_dir  # type: ignore[method-assign]
    else:
        # Fallback: log warning but continue
        log.warning(f"Unknown context type {type(context)}, cleanup may not work correctly")

    return str(temp_path)


def exists(file_path: str) -> bool:
    """Check if a file or directory exists."""
    return Path(file_path).exists()


def create_if_not_exists(directory: str, mode: int = 0o755) -> None:
    """Create directory if it doesn't exist."""
    if not exists(directory):
        Path(directory).mkdir(parents=True, mode=mode, exist_ok=True)


def copy_file(src_file: str, dst_file: str) -> None:
    """Copy a single file from source to destination."""
    src_path = Path(src_file)
    dst_path = Path(dst_file)
    dst_path.write_bytes(src_path.read_bytes())
    # Copy metadata
    stat_info = src_path.stat()
    dst_path.chmod(stat_info.st_mode)


def copy_symlink(source: str, dest: str) -> None:
    """Copy a symbolic link."""
    src_path = Path(source)
    dest_path = Path(dest)
    link_target = src_path.readlink()
    dest_path.symlink_to(link_target)


def copy_directory(src_dir: str, dest: str) -> None:
    """Recursively copy directory contents preserving permissions and ownership."""
    src_path = Path(src_dir)
    dest_path = Path(dest)
    
    for entry in src_path.iterdir():
        source_path = entry
        dest_file_path = dest_path / entry.name
        
        owner = get_file_owner(source_path)
        
        if source_path.is_dir():
            create_if_not_exists(str(dest_file_path), 0o755)
            copy_directory(str(source_path), str(dest_file_path))
        elif source_path.is_symlink():
            copy_symlink(str(source_path), str(dest_file_path))
        else:
            copy_file(str(source_path), str(dest_file_path))
        
        # Set ownership (Unix/Linux only)
        if owner is not None:
            try:
                os.lchown(str(dest_file_path), owner.uid, owner.gid)
            except (OSError, AttributeError):
                pass  # Ignore ownership errors on Windows or permission issues