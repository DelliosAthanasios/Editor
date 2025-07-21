import json
import os
import jsonschema

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "config_schema.json")


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_config(config):
    schema = load_schema()
    jsonschema.validate(instance=config, schema=schema)

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    validate_config(config)
    return config 