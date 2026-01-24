# =============================================================================
# SERV.O v10.1 - SERVICE REGISTRY TESTS
# =============================================================================
# Unit tests for service registry and dependency injection
# =============================================================================

import pytest


class TestServiceRegistry:
    """Test ServiceRegistry class."""

    def test_singleton_pattern(self):
        """Registry should be singleton."""
        from app.services.registry import ServiceRegistry

        reg1 = ServiceRegistry()
        reg2 = ServiceRegistry()

        assert reg1 is reg2

    def test_register_and_get_service(self):
        """Register and retrieve service."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        # Register a test service
        test_service = {'name': 'test'}
        registry.register('test_service', lambda: test_service)

        result = registry.get('test_service')
        assert result == test_service

    def test_singleton_service(self):
        """Singleton services return same instance."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {'instance': call_count}

        registry.register('singleton_test', factory, singleton=True)

        result1 = registry.get('singleton_test')
        result2 = registry.get('singleton_test')

        assert result1 is result2
        assert call_count == 1  # Factory called only once

    def test_factory_service(self):
        """Factory services return new instance each time."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {'instance': call_count}

        registry.register('factory_test', factory, singleton=False)

        result1 = registry.get('factory_test')
        result2 = registry.get('factory_test')

        assert result1 is not result2
        assert call_count == 2  # Factory called twice

    def test_get_unregistered_raises_keyerror(self):
        """Getting unregistered service raises KeyError."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        with pytest.raises(KeyError):
            registry.get('nonexistent_service')

    def test_override_service(self):
        """Override service for testing."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        original = {'type': 'original'}
        mock = {'type': 'mock'}

        registry.register('override_test', lambda: original)
        registry.override('override_test', mock)

        result = registry.get('override_test')
        assert result == mock

        # Clear override
        registry.clear_override('override_test')
        result = registry.get('override_test')
        assert result == original

    def test_clear_all_overrides(self):
        """Clear all overrides."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        registry.register('svc1', lambda: {'name': 'svc1'})
        registry.register('svc2', lambda: {'name': 'svc2'})

        registry.override('svc1', {'name': 'mock1'})
        registry.override('svc2', {'name': 'mock2'})

        registry.clear_all_overrides()

        assert registry.get('svc1') == {'name': 'svc1'}
        assert registry.get('svc2') == {'name': 'svc2'}

    def test_registered_services_list(self):
        """Get list of registered services."""
        from app.services.registry import ServiceRegistry

        registry = ServiceRegistry()

        # Default services should be registered
        services = registry.registered_services

        assert 'orders' in services
        assert 'anomalies' in services
        assert 'extraction' in services


class TestInjectDecorator:
    """Test @inject decorator."""

    def test_inject_services(self):
        """Inject services into function parameters."""
        from app.services.registry import inject, registry

        # Register a test service
        registry.register('inject_test', lambda: {'injected': True})

        @inject('inject_test')
        def my_function(data, inject_test=None):
            return {'data': data, 'service': inject_test}

        result = my_function('test_data')

        assert result['data'] == 'test_data'
        assert result['service'] == {'injected': True}

    def test_inject_does_not_override_provided(self):
        """Injection doesn't override explicitly provided services."""
        from app.services.registry import inject, registry

        registry.register('inject_test2', lambda: {'default': True})

        @inject('inject_test2')
        def my_function(inject_test2=None):
            return inject_test2

        custom = {'custom': True}
        result = my_function(inject_test2=custom)

        assert result == custom


class TestServiceGetters:
    """Test convenience getter functions."""

    def test_get_orders_service(self):
        """Get orders service."""
        from app.services.registry import get_orders_service

        service = get_orders_service()
        assert service is not None

    def test_get_anomalies_service(self):
        """Get anomalies service."""
        from app.services.registry import get_anomalies_service

        service = get_anomalies_service()
        assert service is not None

    def test_get_listini_service(self):
        """Get listini service."""
        from app.services.registry import get_listini_service

        service = get_listini_service()
        assert service is not None

    def test_get_espositori_service(self):
        """Get espositori service."""
        from app.services.registry import get_espositori_service

        service = get_espositori_service()
        assert service is not None
