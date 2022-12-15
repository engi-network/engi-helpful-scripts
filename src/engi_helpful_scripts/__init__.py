class Singleton(object):
    _instance = None

    def _init_hook(self):
        pass

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_hook()
        return cls._instance
