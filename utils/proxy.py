# credits to someone on github lol, not made by cyberbeach

import os, threading

class ProxyManager:

    def __init__(self, file_path="input/proxies.txt"):
        self.file_path = file_path
        self.lock = threading.Lock()
        self.proxies = self._load_proxies()
        self.available_proxies = set(self.proxies)
        self.initial_load_time = self._get_file_modification_time()

    def _load_proxies(self):
        if not os.path.exists(self.file_path):
            print(f"Warning: Proxy file not found at {self.file_path}. Returning empty list.")
            return []

        with open(self.file_path, "r", encoding="utf-8") as f:
            proxies = [
                line.strip()
                for line in f
                if line.strip()
            ]
        return proxies

    def _get_file_modification_time(self):
        if os.path.exists(self.file_path):
            return os.path.getmtime(self.file_path)
        return 0

    def get_proxy(self):
        with self.lock:
            current_mod_time = self._get_file_modification_time()
            if current_mod_time > self.initial_load_time:
                print(f"Proxy file '{self.file_path}' modified. Reloading proxies...")
                self.reload()
                self.initial_load_time = current_mod_time

            if not self.proxies:
                print("No proxies loaded.")
                return None

            if not self.available_proxies:
                print("All proxies used in this cycle. Resetting available proxies.")
                self.available_proxies = set(self.proxies)
                if not self.available_proxies:
                    print("No proxies available after reset.")
                    return None

            proxy = self.available_proxies.pop()
            return proxy

    def reload(self):
        with self.lock:
            old_proxies = set(self.proxies)
            self.proxies = self._load_proxies()
            new_proxies = set(self.proxies)

            added = new_proxies - old_proxies
            removed = old_proxies - new_proxies

            if added or removed:
                print(f"Reloaded proxies. Added: {len(added)}, Removed: {len(removed)}")
                if added: print(f"  New proxies: {', '.join(added)}")
                if removed: print(f"  Removed proxies: {', '.join(removed)}")

            self.available_proxies = set(self.proxies)
            self.initial_load_time = self._get_file_modification_time()
            if not self.proxies:
                print("Warning: Proxy file is empty or contains no valid proxies after reload.")