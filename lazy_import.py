"""
Lazy Import Utility for Media Downloader

Provides thread-safe lazy loading of heavy Python modules to improve startup time.
Includes comprehensive error handling, logging, and caching mechanisms.
"""

import sys
import threading
import logging
from typing import Callable, Any, Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LazyImporter:
    """Thread-safe lazy import manager with caching and error handling"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
    
    def import_module(
        self, 
        module_name: str, 
        import_func: Callable, 
        error_context: Optional[str] = None
    ) -> Any:
        """
        Safely import a module with thread locking and caching.
        
        Args:
            module_name: Unique identifier for this import
            import_func: Function that performs the actual import
            error_context: User-friendly context for error messages
        
        Returns:
            The imported module or result from import_func
            
        Raises:
            ImportError: If the module cannot be imported
        """
        # Fast path: already cached
        if module_name in self._cache:
            logger.debug(f"Using cached module: {module_name}")
            return self._cache[module_name]
        
        # Ensure lock exists for this module (double-checked locking)
        with self._main_lock:
            if module_name not in self._locks:
                self._locks[module_name] = threading.Lock()
        
        # Thread-safe import
        with self._locks[module_name]:
            # Double-check after acquiring lock
            if module_name in self._cache:
                logger.debug(f"Using cached module (post-lock): {module_name}")
                return self._cache[module_name]
            
            try:
                logger.info(f"Lazy loading module: {module_name}")
                start_time = __import__('time').time()
                
                result = import_func()
                
                elapsed_ms = (__import__('time').time() - start_time) * 1000
                logger.info(f"Successfully loaded {module_name} in {elapsed_ms:.1f}ms")
                
                self._cache[module_name] = result
                return result
                
            except ImportError as e:
                context = error_context or module_name
                logger.error(f"Failed to import {module_name}: {e}", exc_info=True)
                raise ImportError(
                    f"Failed to load {context}. "
                    f"Please check dependencies: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error importing {module_name}: {e}", 
                    exc_info=True
                )
                raise
    
    def clear_cache(self, module_name: Optional[str] = None) -> None:
        """
        Clear module cache for testing purposes.
        
        Args:
            module_name: Specific module to clear, or None to clear all
        """
        with self._main_lock:
            if module_name:
                removed = self._cache.pop(module_name, None)
                if removed:
                    logger.info(f"Cleared cache for: {module_name}")
            else:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cleared all cached modules ({count} items)")
    
    def get_cache_status(self) -> Dict[str, bool]:
        """Get current cache status for debugging"""
        return {name: True for name in self._cache.keys()}


# Global instance
_lazy_importer = LazyImporter()


def lazy_import(
    module_name: str, 
    import_func: Callable, 
    error_context: Optional[str] = None
) -> Any:
    """
    Convenience function for lazy imports.
    
    Example:
        def _import_numpy():
            import numpy
            return numpy
        
        np = lazy_import('numpy', _import_numpy, 'NumPy library')
        
    Args:
        module_name: Unique identifier for this import
        import_func: Function that performs the actual import
        error_context: User-friendly context for error messages
        
    Returns:
        The imported module or result from import_func
    """
    return _lazy_importer.import_module(module_name, import_func, error_context)


def clear_cache(module_name: Optional[str] = None) -> None:
    """Clear lazy import cache (for testing)"""
    _lazy_importer.clear_cache(module_name)


def get_cache_status() -> Dict[str, bool]:
    """Get current lazy import cache status"""
    return _lazy_importer.get_cache_status()
