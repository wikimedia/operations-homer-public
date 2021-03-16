import ipaddress
import json

from pathlib import Path

import jsonschema
import pytest
import yaml


CONFIG_DIR = Path('config')
SCHEMA_DIR = Path('tests/schemas')
DEFINITIONS_PATH = 'definitions'
DEFINITIONS_DIR = SCHEMA_DIR / DEFINITIONS_PATH


@pytest.fixture(name='jsonschema_store', scope='session')
def _jsonschema_store():
    """Load the definitions used by $ref in the json schemas to be used by the RefResolver."""
    store = {}
    for schema_file in DEFINITIONS_DIR.glob('*.schema'):
        with open(schema_file) as f:
            schema = json.load(f)
            store['/'.join((DEFINITIONS_PATH, schema['$id']))] = schema

    return store


@jsonschema.FormatChecker.cls_checks('ip_network', raises=(ValueError,))
def is_ip_network(instance):
    """Custom jsonschema format validator for IPv4 and IPv6 networks."""
    ipaddress.ip_network(instance)  # Raises ValueError if invalid
    return True

@jsonschema.FormatChecker.cls_checks('ip_interface', raises=(ValueError,))
def is_ip_interface(instance):
    """Custom jsonschema format validator for IPv4 and IPv6 interfaces."""
    ipaddress.ip_interface(instance)  # Raises ValueError if invalid
    return True

def get_configs():
    """Collect all the existing config files and return them as a list of Paths."""
    return list(CONFIG_DIR.glob('**/*.yaml'))


@pytest.mark.parametrize('config_file', get_configs())
def test_valid_config(jsonschema_store, config_file):
    """All config files should comply to their related schema."""
    config = yaml.safe_load(config_file.read_text())
    schema_file = SCHEMA_DIR / config_file.with_suffix('.schema').name
    with open(schema_file) as f:
        schema = json.load(f)

    resolver = jsonschema.RefResolver(base_uri=DEFINITIONS_PATH, referrer=schema, store=jsonschema_store)
    jsonschema.validate(instance=config, schema=schema, resolver=resolver)  # Raises if invalid
