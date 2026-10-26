"""Validated, atomic JSON persistence for Alien Defender."""
import json
import math
import os
from pathlib import Path

SHIPS = {"Falcon": (340, 100, 0.20), "Titan": (240, 160, 0.28), "Swift": (440, 75, 0.13)}

def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(temporary, path)

def load_game(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('ship') not in SHIPS:
        raise ValueError('Unsupported save file')
    for key, low, high in [('score', 0, 100000000), ('wave', 1, 10000), ('hp', 1, SHIPS[data['ship']][1]), ('x', 20, 940), ('y', 90, 610)]:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('Invalid save field: ' + key)
    if not isinstance(data['score'], int) or not isinstance(data['wave'], int):
        raise ValueError('Score and wave must be integers')
    return data
