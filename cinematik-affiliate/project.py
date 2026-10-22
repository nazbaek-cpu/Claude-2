"""Read projects/<name>/project.json, laid over a named preset (presets/<preset>.json) when it sets "preset"."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

def merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out

def read(prj):
    cfg = json.load(open(os.path.join(prj, "project.json")))
    if "preset" in cfg:
        cfg = merge(json.load(open(os.path.join(HERE, "presets", cfg["preset"] + ".json"))), cfg)
    return cfg
