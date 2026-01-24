# =============================================================================
# SERV.O v10.1 - SERVICE REGISTRY
# =============================================================================
# Central service registry with dependency injection support
# Allows services to be swapped for testing and modularity
# =============================================================================

from typing import Dict, Any, Callable, TypeVar, Generic, Optional
from functools import lru_cache

T = TypeVar('T')


class ServiceRegistry:
    """
    Central registry for service instances.

    Supports:
    - Singleton services (one instance per service)
    - Factory services (new instance per request)
    - Service overrides for testing

    Usage:
        # Register
        registry.register('orders', OrdersService)
        registry.register('anomalies', AnomaliesService, singleton=True)

        # Get
        orders = registry.get('orders')

        # Override for testing
        registry.override('orders', MockOrdersService)
    """

    _instance: Optional['ServiceRegistry'] = None
    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable] = {}
    _singletons: Dict[str, bool] = {}
    _overrides: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._factories = {}
            cls._instance._singletons = {}
            cls._instance._overrides = {}
        return cls._instance

    def register(
        self,
        name: str,
        factory: Callable,
        singleton: bool = True
    ):
        """
        Register a service factory.

        Args:
            name: Service name
            factory: Callable that creates service instance
            singleton: If True, only one instance is created
        """
        self._factories[name] = factory
        self._singletons[name] = singleton

        # Clear cached instance if re-registering
        if name in self._services:
            del self._services[name]

    def get(self, name: str) -> Any:
        """
        Get service instance.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Check for override first
        if name in self._overrides:
            return self._overrides[name]

        # Check for cached singleton
        if name in self._services and self._singletons.get(name, True):
            return self._services[name]

        # Create new instance
        if name not in self._factories:
            raise KeyError(f"Service '{name}' not registered")

        instance = self._factories[name]()

        # Cache if singleton
        if self._singletons.get(name, True):
            self._services[name] = instance

        return instance

    def override(self, name: str, instance: Any):
        """
        Override service with custom instance (for testing).

        Args:
            name: Service name
            instance: Override instance
        """
        self._overrides[name] = instance

    def clear_override(self, name: str):
        """Remove service override."""
        if name in self._overrides:
            del self._overrides[name]

    def clear_all_overrides(self):
        """Remove all overrides."""
        self._overrides.clear()

    def reset(self):
        """Reset registry (clear all cached instances)."""
        self._services.clear()
        self._overrides.clear()

    @property
    def registered_services(self) -> list:
        """List of registered service names."""
        return list(self._factories.keys())


# Global registry instance
registry = ServiceRegistry()


# =============================================================================
# SERVICE GETTERS (Convenience functions)
# =============================================================================

def get_orders_service():
    """Get orders service instance."""
    return registry.get('orders')


def get_anomalies_service():
    """Get anomalies service instance."""
    return registry.get('anomalies')


def get_supervision_service():
    """Get supervision service instance."""
    return registry.get('supervision')


def get_extraction_service():
    """Get extraction service instance."""
    return registry.get('extraction')


def get_export_service():
    """Get export service instance."""
    return registry.get('export')


def get_lookup_service():
    """Get lookup service instance."""
    return registry.get('lookup')


def get_listini_service():
    """Get listini service instance."""
    return registry.get('listini')


def get_espositori_service():
    """Get espositori service instance."""
    return registry.get('espositori')


# =============================================================================
# SERVICE REGISTRATION (On module import)
# =============================================================================

def _register_default_services():
    """Register default service factories."""

    # Orders service
    def orders_factory():
        from . import orders
        return orders

    registry.register('orders', orders_factory)

    # Anomalies service
    def anomalies_factory():
        from . import anomalies
        return anomalies

    registry.register('anomalies', anomalies_factory)

    # Supervision service
    def supervision_factory():
        from . import supervision
        return supervision

    registry.register('supervision', supervision_factory)

    # Extraction service
    def extraction_factory():
        from . import extraction
        return extraction

    registry.register('extraction', extraction_factory)

    # Export service
    def export_factory():
        from . import export
        return export

    registry.register('export', export_factory)

    # Lookup service
    def lookup_factory():
        from . import lookup
        return lookup

    registry.register('lookup', lookup_factory)

    # Listini service
    def listini_factory():
        from . import listini
        return listini

    registry.register('listini', listini_factory)

    # Espositori service
    def espositori_factory():
        from . import espositori
        return espositori

    registry.register('espositori', espositori_factory)


# Register on import
_register_default_services()


# =============================================================================
# DEPENDENCY INJECTION DECORATOR
# =============================================================================

def inject(*service_names: str):
    """
    Decorator that injects services into function parameters.

    Usage:
        @inject('orders', 'anomalies')
        def process_order(order_id, orders=None, anomalies=None):
            orders.get_ordine_detail(order_id)
            anomalies.get_anomalie_by_ordine(order_id)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for name in service_names:
                if name not in kwargs or kwargs[name] is None:
                    kwargs[name] = registry.get(name)
            return func(*args, **kwargs)
        return wrapper
    return decorator
