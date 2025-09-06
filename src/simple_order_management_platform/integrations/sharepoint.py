"""SharePoint/OneDrive integration for automated file sharing."""

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class SharePointIntegration:
    """Integration with SharePoint/OneDrive for automated file sharing."""
    
    def __init__(self, sharepoint_root: str, project_sharepoint_dir: str):
        """
        Initialize SharePoint integration.
        
        Args:
            sharepoint_root: Root SharePoint directory path
            project_sharepoint_dir: Project-specific SharePoint directory path
        """
        self.sharepoint_root = Path(sharepoint_root)
        self.project_sharepoint_dir = Path(project_sharepoint_dir)
        
        # Validate paths
        self._validate_paths()
    
    def _validate_paths(self) -> None:
        """Validate SharePoint directory paths."""
        if not self.sharepoint_root.exists():
            logger.warning(f"SharePoint root directory not found: {self.sharepoint_root}")
            logger.warning("SharePoint integration will be disabled")
        
        if not self.project_sharepoint_dir.exists():
            logger.warning(f"Project SharePoint directory not found: {self.project_sharepoint_dir}")
            # Try to create it
            try:
                self.project_sharepoint_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created project SharePoint directory: {self.project_sharepoint_dir}")
            except Exception as e:
                logger.error(f"Failed to create project SharePoint directory: {e}")
    
    def is_available(self) -> bool:
        """Check if SharePoint integration is available."""
        return self.sharepoint_root.exists() and self.project_sharepoint_dir.exists()
    
    def upload_portfolio_report(
        self, 
        local_file_path: Path, 
        create_dated_folder: bool = True,
        custom_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        Upload portfolio report to SharePoint.
        
        Args:
            local_file_path: Local file path to upload
            create_dated_folder: Whether to create a dated subfolder
            custom_name: Custom filename (optional)
            
        Returns:
            SharePoint file path if successful, None otherwise
        """
        if not self.is_available():
            logger.error("SharePoint integration not available")
            return None
        
        try:
            # Determine target directory
            target_dir = self.project_sharepoint_dir / "daily_reports"
            
            if create_dated_folder:
                date_str = datetime.now().strftime('%Y-%m-%d')
                target_dir = target_dir / date_str
            
            # Create directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine target filename
            if custom_name:
                target_filename = custom_name
            else:
                target_filename = local_file_path.name
            
            target_path = target_dir / target_filename
            
            # Copy file to SharePoint
            shutil.copy2(local_file_path, target_path)
            
            logger.info(f"Successfully uploaded portfolio report to SharePoint: {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"Failed to upload portfolio report to SharePoint: {e}")
            return None
    
    def upload_market_data(
        self, 
        local_file_path: Path, 
        data_type: str = "market_data"
    ) -> Optional[Path]:
        """
        Upload market data files to SharePoint.
        
        Args:
            local_file_path: Local file path to upload
            data_type: Type of data (market_data, prices, etc.)
            
        Returns:
            SharePoint file path if successful, None otherwise
        """
        if not self.is_available():
            logger.error("SharePoint integration not available")
            return None
        
        try:
            # Create market data directory structure
            date_str = datetime.now().strftime('%Y-%m-%d')
            target_dir = self.sharepoint_root / "market_data" / data_type / date_str
            target_dir.mkdir(parents=True, exist_ok=True)
            
            target_path = target_dir / local_file_path.name
            
            # Copy file to SharePoint
            shutil.copy2(local_file_path, target_path)
            
            logger.info(f"Successfully uploaded market data to SharePoint: {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"Failed to upload market data to SharePoint: {e}")
            return None
    
    def create_project_backup(self, exclude_patterns: Optional[List[str]] = None) -> Optional[Path]:
        """
        Create a backup of the entire project to SharePoint.
        
        Args:
            exclude_patterns: List of patterns to exclude from backup
            
        Returns:
            Backup directory path if successful, None otherwise
        """
        if not self.is_available():
            logger.error("SharePoint integration not available")
            return None
        
        if exclude_patterns is None:
            exclude_patterns = ['.git', '__pycache__', '*.pyc', '.venv', 'venv', 'node_modules']
        
        try:
            # Create backup directory with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = self.project_sharepoint_dir / "backups" / f"backup_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Get project root (assuming we're in src/...)
            project_root = Path.cwd()
            while not (project_root / "pyproject.toml").exists() and project_root != project_root.parent:
                project_root = project_root.parent
            
            # Copy project files (excluding patterns)
            self._copy_directory_selective(project_root, backup_dir, exclude_patterns)
            
            logger.info(f"Successfully created project backup: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            logger.error(f"Failed to create project backup: {e}")
            return None
    
    def _copy_directory_selective(
        self, 
        source_dir: Path, 
        target_dir: Path, 
        exclude_patterns: List[str]
    ) -> None:
        """Copy directory contents selectively, excluding specified patterns."""
        import fnmatch
        
        for item in source_dir.iterdir():
            # Check if item matches any exclude pattern
            should_exclude = False
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(item.name, pattern):
                    should_exclude = True
                    break
            
            if should_exclude:
                continue
            
            target_item = target_dir / item.name
            
            if item.is_file():
                target_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_item)
            elif item.is_dir():
                target_item.mkdir(parents=True, exist_ok=True)
                self._copy_directory_selective(item, target_item, exclude_patterns)
    
    def list_recent_uploads(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        List recent uploads to SharePoint.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of file information dictionaries
        """
        if not self.is_available():
            return []
        
        recent_files = []
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        try:
            # Search in daily reports
            daily_reports_dir = self.project_sharepoint_dir / "daily_reports"
            if daily_reports_dir.exists():
                for file_path in daily_reports_dir.rglob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime > cutoff_time:
                        recent_files.append({
                            'path': str(file_path),
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                            'type': 'portfolio_report'
                        })
            
            # Search in market data
            market_data_dir = self.sharepoint_root / "market_data"
            if market_data_dir.exists():
                for file_path in market_data_dir.rglob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime > cutoff_time:
                        recent_files.append({
                            'path': str(file_path),
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                            'type': 'market_data'
                        })
            
            # Sort by modification time (newest first)
            recent_files.sort(key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list recent uploads: {e}")
        
        return recent_files
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information for SharePoint directories."""
        info = {
            'sharepoint_root_exists': self.sharepoint_root.exists(),
            'project_dir_exists': self.project_sharepoint_dir.exists(),
            'available': self.is_available()
        }
        
        if self.is_available():
            try:
                # Calculate directory sizes
                def get_dir_size(path: Path) -> int:
                    total_size = 0
                    for item in path.rglob("*"):
                        if item.is_file():
                            total_size += item.stat().st_size
                    return total_size
                
                info['project_size_bytes'] = get_dir_size(self.project_sharepoint_dir)
                info['project_size_mb'] = round(info['project_size_bytes'] / (1024 * 1024), 2)
                
                # Count files
                info['total_files'] = len([f for f in self.project_sharepoint_dir.rglob("*") if f.is_file()])
                
            except Exception as e:
                logger.error(f"Failed to get storage info: {e}")
                info['error'] = str(e)
        
        return info


# Factory function for easy initialization
def create_sharepoint_integration() -> SharePointIntegration:
    """Create SharePoint integration instance from configuration."""
    from ..config.loader import config_loader
    
    app_config = config_loader.load_app_config()
    directories = app_config.app.get('directories', {})
    
    sharepoint_root = directories.get(
        'sharepoint_dir', 
        '/Users/msyeom/Library/CloudStorage/OneDrive-SharedLibraries-OPTIMALVEST.AIPTE.LTD/Arki Investment - Trading'
    )
    
    project_sharepoint_dir = directories.get(
        'project_sharepoint_dir',
        '/Users/msyeom/Library/CloudStorage/OneDrive-SharedLibraries-OPTIMALVEST.AIPTE.LTD/Arki Investment - Trading/simple-order-management-platform'
    )
    
    return SharePointIntegration(sharepoint_root, project_sharepoint_dir)


# Global instance for easy access
sharepoint_integration = create_sharepoint_integration()