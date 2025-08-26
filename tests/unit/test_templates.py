from pathlib import Path

import pytest
from jinja2 import Template

TEMPLATE_DIR: str = "templates"


def get_templates():
    path = Path(TEMPLATE_DIR)
    return list(path.glob("**/*.conf"))


@pytest.mark.parametrize("template", get_templates())
def test_valid_jinja2(template):
    with open(str(template)) as f:
        Template(f.read())  # If invalid will raise
