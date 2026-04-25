import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.reload()
    
    def reload(self):
        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = {}
    
    def get(self, *keys, default=None) -> Any:
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        return self._config.get(section, {})
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config