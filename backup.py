#!/usr/bin/env python3
"""
Production backup script
"""

import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

class BackupManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.backup_dir = Path("backups")
        self.logger = logging.getLogger(__name__)
        
        # Create backup directories
        self.backup_dir.mkdir(exist_ok=True)
        (self.backup_dir / "daily").mkdir(exist_ok=True)
        (self.backup_dir / "weekly").mkdir(exist_ok=True)
    
    def create_backup(self, backup_type="daily"):
        """Create a backup of the database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            source_file = self.data_dir / "trading_data.duckdb"
            backup_file = self.backup_dir / backup_type / f"backup_{timestamp}.duckdb"
            
            if source_file.exists():
                shutil.copy2(source_file, backup_file)
                self.logger.info(f"Backup created: {backup_file}")
                return str(backup_file)
            else:
                self.logger.warning("No database file to backup")
                return None
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return None
    
    def cleanup_old_backups(self, retention_days=30):
        """Clean up old backup files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup_type in ["daily", "weekly"]:
                backup_path = self.backup_dir / backup_type
                if backup_path.exists():
                    for backup_file in backup_path.glob("backup_*.duckdb"):
                        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        if file_time < cutoff_date:
                            backup_file.unlink()
                            self.logger.info(f"Deleted old backup: {backup_file}")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def verify_backup(self, backup_file):
        """Verify backup file integrity"""
        try:
            if Path(backup_file).exists():
                file_size = Path(backup_file).stat().st_size
                return file_size > 0
            return False
        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return False

def main():
    """Main backup process"""
    backup_manager = BackupManager()
    
    # Create daily backup
    backup_file = backup_manager.create_backup("daily")
    
    # Create weekly backup on Sundays
    if datetime.now().weekday() == 6:  # Sunday
        backup_manager.create_backup("weekly")
    
    # Cleanup old backups
    backup_manager.cleanup_old_backups()
    
    # Verify backup
    if backup_file and backup_manager.verify_backup(backup_file):
        print(f"Backup completed successfully: {backup_file}")
    else:
        print("Backup failed or verification failed")

if __name__ == "__main__":
    main()
