# credits to someone on github lol

import os, threading

class ProxyManager:

    def __init__(self, file_path="input/proxies.txt"):
        self.file_path = file_path
        self.lock = threading.Lock()
        self.index = 0
        self.proxies = self._load_proxies()

    def _load_proxies(self):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, "r", encoding="utf-8") as f:
            return [
                line.strip()
                for line in f
                if line.strip()
            ]

    def pop_top(self):
        with self.lock:
            if not self.proxies:
                return None

            proxy = self.proxies[self.index]
            self.index = (self.index + 1) % len(self.proxies)

            return proxy


    def reload(self):
        with self.lock:
            self.proxies = self._load_proxies()
            self.index = 0

proxy_manager = ProxyManager()