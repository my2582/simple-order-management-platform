"""Permission management system for role-based access control."""

from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles in the system."""
    PORTFOLIO_MANAGER = "portfolio_manager"
    TRADE_ASSISTANT = "trade_assistant"


class Permission(Enum):
    """Available permissions in the system."""
    # Portfolio Manager permissions
    PORTFOLIO_DOWNLOAD = "portfolio_download"
    ORDER_GENERATION = "order_generation"
    ACCOUNT_SUMMARY = "account_summary"
    
    # Trade Assistant permissions
    MARKET_DATA = "market_data"
    UNIVERSE_UPDATE = "universe_update"
    PRICE_DOWNLOAD = "price_download"


@dataclass
class IBKRProfile:
    """IBKR connection profile for a specific role."""
    
    role: UserRole
    description: str
    host: str
    port: int
    client_id: int
    timeout: int
    permissions: Set[Permission]

    @classmethod
    def from_config(cls, role: UserRole, config: Dict) -> 'IBKRProfile':
        """Create IBKRProfile from configuration dictionary."""
        permissions = set()
        for perm_str in config.get('permissions', []):
            try:
                permissions.add(Permission(perm_str))
            except ValueError:
                logger.warning(f"Unknown permission: {perm_str}")
        
        return cls(
            role=role,
            description=config.get('description', ''),
            host=config.get('host', '127.0.0.1'),
            port=config.get('port', 4002),
            client_id=config.get('client_id', 1),
            timeout=config.get('timeout', 30),
            permissions=permissions
        )


class PermissionManager:
    """Manages user roles and permissions."""
    
    def __init__(self, profiles_config: Dict):
        """Initialize permission manager with IBKR profiles config."""
        self.profiles: Dict[UserRole, IBKRProfile] = {}
        self._load_profiles(profiles_config)
    
    def _load_profiles(self, profiles_config: Dict) -> None:
        """Load IBKR profiles from configuration."""
        for role_str, config in profiles_config.items():
            try:
                role = UserRole(role_str)
                profile = IBKRProfile.from_config(role, config)
                self.profiles[role] = profile
                logger.info(f"Loaded IBKR profile for {role.value}: {profile.description}")
            except ValueError:
                logger.warning(f"Unknown user role: {role_str}")
    
    def get_profile(self, role: UserRole) -> Optional[IBKRProfile]:
        """Get IBKR profile for a user role."""
        return self.profiles.get(role)
    
    def has_permission(self, role: UserRole, permission: Permission) -> bool:
        """Check if a role has a specific permission."""
        profile = self.get_profile(role)
        return profile is not None and permission in profile.permissions
    
    def get_permissions(self, role: UserRole) -> Set[Permission]:
        """Get all permissions for a role."""
        profile = self.get_profile(role)
        return profile.permissions if profile else set()
    
    def validate_access(self, role: UserRole, required_permission: Permission) -> bool:
        """Validate that a role has required permission."""
        if not self.has_permission(role, required_permission):
            logger.error(f"Access denied: {role.value} does not have {required_permission.value} permission")
            return False
        return True
    
    def get_ibkr_connection_params(self, role: UserRole) -> Optional[Dict]:
        """Get IBKR connection parameters for a role."""
        profile = self.get_profile(role)
        if not profile:
            return None
        
        return {
            'host': profile.host,
            'port': profile.port,
            'client_id': profile.client_id,
            'timeout': profile.timeout
        }
    
    def list_profiles(self) -> Dict[UserRole, str]:
        """List all available profiles with descriptions."""
        return {role: profile.description for role, profile in self.profiles.items()}


def require_permission(permission: Permission):
    """Decorator to require specific permission for function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be enhanced with actual user context in a real system
            # For now, we'll assume portfolio_manager role for most operations
            role = UserRole.PORTFOLIO_MANAGER  # This should come from user context
            
            from ..config.loader import config_loader
            app_config = config_loader.load_app_config()
            profiles_config = app_config.app.get('ibkr_profiles', {})
            
            permission_manager = PermissionManager(profiles_config)
            
            if not permission_manager.validate_access(role, permission):
                raise PermissionError(f"Insufficient permissions: {permission.value} required")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user_role() -> UserRole:
    """Get current user role. In a real system, this would check authentication context."""
    # For now, default to portfolio manager
    # This should be enhanced to check actual user authentication
    return UserRole.PORTFOLIO_MANAGER


def get_role_ibkr_params(role: UserRole) -> Dict:
    """Get IBKR connection parameters for a specific role."""
    from ..config.loader import config_loader
    app_config = config_loader.load_app_config()
    profiles_config = app_config.app.get('ibkr_profiles', {})
    
    permission_manager = PermissionManager(profiles_config)
    params = permission_manager.get_ibkr_connection_params(role)
    
    if not params:
        # Fallback to legacy settings
        ib_settings = app_config.ib_settings
        params = {
            'host': ib_settings.get('host', '127.0.0.1'),
            'port': ib_settings.get('port', 4002),
            'client_id': ib_settings.get('client_id', 1),
            'timeout': ib_settings.get('timeout', 30)
        }
    
    return params