"""Storage management for local and SharePoint modes."""

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import logging
import os

from .sharepoint import SharePointIntegration

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Unified storage manager supporting both local and SharePoint modes.
    
    Provides a consistent interface for file operations regardless of storage backend.
    """
    
    def __init__(
        self, 
        storage_mode: str = "local",
        local_config: Optional[Dict[str, str]] = None,
        sharepoint_config: Optional[Dict[str, str]] = None
    ):
        """
        Initialize storage manager.
        
        Args:
            storage_mode: "local" or "sharepoint"
            local_config: Local storage configuration with directory paths
            sharepoint_config: SharePoint configuration with directory paths
        """
        self.storage_mode = storage_mode.lower()
        self.local_config = local_config or {}
        self.sharepoint_config = sharepoint_config or {}
        
        # Initialize storage backend
        self.sharepoint = None
        if self.storage_mode == "sharepoint" and sharepoint_config:
            try:
                self.sharepoint = SharePointIntegration(
                    sharepoint_root=sharepoint_config.get('sharepoint_dir', ''),
                    project_sharepoint_dir=sharepoint_config.get('project_sharepoint_dir', '')
                )
            except Exception as e:
                logger.warning(f"SharePoint initialization failed: {e}")
                logger.info("Falling back to local storage mode")
                self.storage_mode = "local"
        
        # Setup local directories
        self._setup_local_directories()
        
        logger.info(f"Storage manager initialized in '{self.storage_mode}' mode")
    
    def _setup_local_directories(self) -> None:
        """Create local directories if they don't exist."""
        if self.storage_mode == "local":
            local_dirs = [
                self.local_config.get('local_output_dir', '/Users/msyeom/arki/portfolio-reports'),
                self.local_config.get('local_market_data_dir', '/Users/msyeom/arki/market-data'),
                self.local_config.get('local_backup_dir', '/Users/msyeom/arki/backups')
            ]
            
            for dir_path in local_dirs:
                if dir_path:
                    path = Path(dir_path)
                    path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Ensured directory exists: {path}")
    
    def is_available(self) -> bool:
        """Check if storage backend is available."""
        if self.storage_mode == "local":
            # Local storage is always available
            return True
        elif self.storage_mode == "sharepoint":
            return self.sharepoint and self.sharepoint.is_available()
        return False
    
    def get_output_directory(self, subfolder: Optional[str] = None) -> Path:
        """
        Get the appropriate output directory for the current storage mode.
        
        Args:
            subfolder: Optional subfolder name (e.g., date string)
            
        Returns:
            Path to output directory
        """
        if self.storage_mode == "local":
            base_dir = Path(self.local_config.get('local_output_dir', '/Users/msyeom/arki/portfolio-reports'))
        else:  # sharepoint mode
            base_dir = Path(self.sharepoint_config.get('sharepoint_dir', ''))
        
        if subfolder:
            output_dir = base_dir / subfolder
        else:
            output_dir = base_dir
        
        # Ensure directory exists (for local mode)
        if self.storage_mode == "local":
            output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir
    
    def get_market_data_directory(self) -> Path:
        """Get market data storage directory."""
        if self.storage_mode == "local":
            market_data_dir = Path(self.local_config.get('local_market_data_dir', '/Users/msyeom/arki/market-data'))
            market_data_dir.mkdir(parents=True, exist_ok=True)
            return market_data_dir
        else:  # sharepoint mode
            return Path(self.sharepoint_config.get('sharepoint_dir', '')) / 'market-data'
    
    def save_portfolio_report(
        self,
        file_path: Path,
        target_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save portfolio report to appropriate storage location.
        
        Args:
            file_path: Source file path
            target_filename: Target filename (optional, uses source filename if not provided)
            
        Returns:
            Dictionary with operation result and target path
        """
        try:
            # Generate date-based subfolder
            date_folder = datetime.now().strftime('%Y-%m-%d')
            target_dir = self.get_output_directory(date_folder)
            
            # Determine target filename
            if not target_filename:
                target_filename = file_path.name
            
            target_path = target_dir / target_filename
            
            if self.storage_mode == "local":
                # Simple file copy for local mode
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_path)
                logger.info(f"Portfolio report saved locally: {target_path}")
                
                return {
                    'success': True,
                    'target_path': target_path,
                    'message': f'Saved to local directory: {target_path}',
                    'storage_mode': 'local'
                }
            
            else:  # sharepoint mode
                if not self.sharepoint or not self.sharepoint.is_available():
                    # Fallback to local if SharePoint not available
                    logger.warning("SharePoint not available, falling back to local storage")
                    return self._save_local_fallback(file_path, target_filename, date_folder)
                
                # Use SharePoint integration
                result = self.sharepoint.upload_portfolio_report(
                    file_path=file_path,
                    date_folder=date_folder,
                    target_filename=target_filename
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to save portfolio report: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to save portfolio report: {e}',
                'storage_mode': self.storage_mode
            }
    
    def save_market_data_report(
        self,
        file_path: Path,
        target_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save market data report to appropriate storage location.
        
        Args:
            file_path: Source file path
            target_filename: Target filename (optional)
            
        Returns:
            Dictionary with operation result and target path
        """
        try:
            market_data_dir = self.get_market_data_directory()
            
            if not target_filename:
                target_filename = file_path.name
            
            target_path = market_data_dir / target_filename
            
            if self.storage_mode == "local":
                shutil.copy2(file_path, target_path)
                logger.info(f"Market data report saved locally: {target_path}")
                
                return {
                    'success': True,
                    'target_path': target_path,
                    'message': f'Market data saved to: {target_path}',
                    'storage_mode': 'local'
                }
            
            else:  # sharepoint mode
                if not self.sharepoint or not self.sharepoint.is_available():
                    return self._save_local_fallback(file_path, target_filename, 'market-data')
                
                # For SharePoint, you can implement specific market data upload logic
                # For now, use the same directory structure
                shutil.copy2(file_path, target_path)
                logger.info(f"Market data report copied to SharePoint area: {target_path}")
                
                return {
                    'success': True,
                    'target_path': target_path,
                    'message': f'Market data saved to SharePoint: {target_path}',
                    'storage_mode': 'sharepoint'
                }
                
        except Exception as e:
            logger.error(f"Failed to save market data report: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to save market data report: {e}',
                'storage_mode': self.storage_mode
            }
    
    def _save_local_fallback(
        self,
        file_path: Path,
        target_filename: str,
        subfolder: str
    ) -> Dict[str, Any]:
        """Save file to local directory as fallback."""
        try:
            local_dir = Path(self.local_config.get('local_output_dir', '/Users/msyeom/arki')) / subfolder
            local_dir.mkdir(parents=True, exist_ok=True)
            
            target_path = local_dir / target_filename
            shutil.copy2(file_path, target_path)
            
            logger.info(f"File saved to local fallback: {target_path}")
            
            return {
                'success': True,
                'target_path': target_path,
                'message': f'Saved to local fallback: {target_path}',
                'storage_mode': 'local_fallback'
            }
            
        except Exception as e:
            logger.error(f"Local fallback failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Local fallback failed: {e}',
                'storage_mode': 'failed'
            }
    
    def backup_project_files(self, source_dir: Path, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Backup project files to appropriate storage location.
        
        Args:
            source_dir: Source directory to backup
            backup_name: Optional backup name (uses timestamp if not provided)
            
        Returns:
            Dictionary with backup result
        """
        try:
            if not backup_name:
                backup_name = f"project_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if self.storage_mode == "local":
                backup_dir = Path(self.local_config.get('local_backup_dir', '/Users/msyeom/arki/backups'))
                backup_dir.mkdir(parents=True, exist_ok=True)
                target_path = backup_dir / backup_name
                
                # Create backup archive
                shutil.make_archive(str(target_path), 'zip', source_dir)
                archive_path = Path(f"{target_path}.zip")
                
                logger.info(f"Project backup created: {archive_path}")
                
                return {
                    'success': True,
                    'backup_path': archive_path,
                    'message': f'Backup created: {archive_path}',
                    'storage_mode': 'local'
                }
            
            else:  # sharepoint mode
                if self.sharepoint and self.sharepoint.is_available():
                    result = self.sharepoint.backup_project_files(source_dir, backup_name)
                    return result
                else:
                    # Fallback to local backup
                    logger.warning("SharePoint not available for backup, using local backup")
                    return self._save_local_fallback(source_dir, f"{backup_name}.zip", 'backups')
                    
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Backup failed: {e}',
                'storage_mode': self.storage_mode
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get storage manager status information."""
        status = {
            'storage_mode': self.storage_mode,
            'available': self.is_available(),
            'directories': {}
        }
        
        if self.storage_mode == "local":
            status['directories'] = {
                'output': self.local_config.get('local_output_dir'),
                'market_data': self.local_config.get('local_market_data_dir'),
                'backup': self.local_config.get('local_backup_dir')
            }
        else:
            status['directories'] = {
                'sharepoint_root': self.sharepoint_config.get('sharepoint_dir'),
                'project_dir': self.sharepoint_config.get('project_sharepoint_dir')
            }
            
            if self.sharepoint:
                status['sharepoint_available'] = self.sharepoint.is_available()
        
        return status


def create_storage_manager() -> StorageManager:
    """Create storage manager instance from configuration."""
    from ..config.loader import config_loader
    
    app_config = config_loader.load_app_config()
    app = app_config.app
    
    # Get storage mode
    storage_mode = app.get('storage', {}).get('mode', 'local')
    
    # Get directories configuration
    directories = app.get('directories', {})
    
    local_config = {
        'local_output_dir': directories.get('local_output_dir'),
        'local_market_data_dir': directories.get('local_market_data_dir'),
        'local_backup_dir': directories.get('local_backup_dir')
    }
    
    sharepoint_config = {
        'sharepoint_dir': directories.get('sharepoint_dir'),
        'project_sharepoint_dir': directories.get('project_sharepoint_dir')
    }
    
    return StorageManager(
        storage_mode=storage_mode,
        local_config=local_config,
        sharepoint_config=sharepoint_config
    )


# Global instance for easy access
storage_manager = create_storage_manager()