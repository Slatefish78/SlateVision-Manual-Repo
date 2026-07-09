import json
from pathlib import Path

class JsonData:
    def __init__(self, config_path):
        self.path = Path(config_path)

        with open(self.path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def get(self, *keys, default=None):
        data = self._data
        try:
            for key in keys:
                data = data[key]
            return data
        except (KeyError, TypeError):
            return default

    def set(self, *keys, value):
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4)