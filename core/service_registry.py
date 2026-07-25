class ServiceRegistry:
    def __init__(self):
        self._services = {}

    def register(self, name, instance):
        self._services[name] = instance

    def get(self, name):
        service = self._services.get(name)
        if service is None:
            raise KeyError(f"Service '{name}' not registered")
        return service

    def has(self, name):
        return name in self._services

    def remove(self, name):
        self._services.pop(name, None)

    def list_services(self):
        return list(self._services.keys())


registry = ServiceRegistry()
