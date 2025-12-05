"""Backup utilities for safe modifications."""

import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from .colors import Colors


def create_backup(
    source_dir: Path,
    backup_name: Optional[str] = None,
    include_patterns: list[str] = None
) -> Path:
    """
    Create backup of localization files.

    Args:
        source_dir: Directory to backup
        backup_name: Custom backup name (default: timestamp)
        include_patterns: Patterns to include (default: all)

    Returns:
        Path to backup directory
    """
    if backup_name is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'localization_backup_{timestamp}'

    backup_dir = source_dir / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Creating backup: {Colors.bold(backup_name)}")

    # Copy files
    if include_patterns:
        # Copy specific patterns
        for pattern in include_patterns:
            for file_path in source_dir.rglob(pattern):
                if file_path.is_file():
                    relative_path = file_path.relative_to(source_dir)
                    dest_path = backup_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)
    else:
        # Copy entire directory
        shutil.copytree(source_dir, backup_dir, dirs_exist_ok=True)

    print(f"   {Colors.success('✓')} Backup created: {backup_dir}")

    return backup_dir


def restore_backup(backup_dir: Path, target_dir: Path) -> bool:
    """
    Restore from backup.

    Args:
        backup_dir: Backup directory
        target_dir: Target directory to restore to

    Returns:
        Success status
    """
    if not backup_dir.exists():
        print(f"{Colors.error('❌')} Backup not found: {backup_dir}")
        return False

    print(f"\n🔄 Restoring from backup: {Colors.bold(backup_dir.name)}")

    try:
        shutil.copytree(backup_dir, target_dir, dirs_exist_ok=True)
        print(f"   {Colors.success('✓')} Restored successfully")
        return True
    except Exception as e:
        print(f"   {Colors.error('❌')} Restore failed: {e}")
        return False


def list_backups(project_dir: Path) -> list[Path]:
    """
    List all available backups.

    Args:
        project_dir: Project directory

    Returns:
        List of backup directories
    """
    backups = sorted(
        project_dir.glob('localization_backup_*'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return backups


def cleanup_old_backups(project_dir: Path, keep_count: int = 5):
    """
    Remove old backups, keeping only the most recent ones.

    Args:
        project_dir: Project directory
        keep_count: Number of backups to keep
    """
    backups = list_backups(project_dir)

    if len(backups) <= keep_count:
        return

    to_remove = backups[keep_count:]

    print(f"\n🧹 Cleaning up old backups (keeping {keep_count} most recent)")

    for backup in to_remove:
        shutil.rmtree(backup)
        print(f"   {Colors.success('✓')} Removed: {backup.name}")

    print(f"   {Colors.success('✓')} Cleanup complete")
