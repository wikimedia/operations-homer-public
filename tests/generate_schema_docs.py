#!/usr/bin/python3
import re
import subprocess
import shutil
from html.parser import HTMLParser
from pathlib import Path

import requests


INDEX_PREFIX = """<!DOCTYPE html>
<html>
  <head>
    <title>Homer Public documentation</title>
  </head>
  <body>
    <h1>Homer Public documentation</h1>
    <h3>Configuration files</h1>
    <p>All configuration files in config/ must adhere to their related schema:</p>
    <ul>
"""
INDEX_SUFFIX = """
    </ul>
  </body>
</html>
"""


class ExternalLinksParser(HTMLParser):
    """Html parser to extract all the external links."""

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        self.links = {}
        self.base_path = kwargs['output_base_path']
        del kwargs['output_base_path']
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        """Gets called when an HTML tag is opened."""
        if tag == 'link':
            self._process_tag('href', attrs)

        if tag == 'script':
            self._process_tag('src', attrs)

    def _process_tag(self, key_name, attrs):
        """Process a given tag finding the external link."""
        for key, value in attrs:
            if key == key_name:
                if value not in self.links and value.startswith('http'):
                    self._download_resource(key_name, value)
                break

    def _download_resource(self, key, url):
        """Dowload the external resource in the base path."""
        if url.startswith('https://use.fontawesome.com/'):  # Remove them completely
            self.links[url] = ''
            return

        url_path = Path(requests.utils.urlparse(url).path)
        if not url_path.suffix:
            url_path = url_path.with_suffix('.js' if key == 'src' else '.css')

        file_content = requests.get(url, timeout=10).text
        file_path = self.base_path / url_path.name
        file_path.write_text(file_content)

        if url_path.suffix == '.css' and 'src: url(' in file_content:  # Download the font
            links = self._download_fonts(file_content)
            replace_references(file_path, links)

        self.links[url] = url_path.name

    def _download_fonts(self, file_content):
        """Download external fonts and return the links to replace."""
        links = {}
        for line in file_content.splitlines():
            match = re.search(r'url\((?P<url>http[^)]+)\)', line)
            if match is not None:
                url = match.groupdict()['url']
                name = Path(requests.utils.urlparse(url).path).name
                (self.base_path / name).write_text(requests.get(url, timeout=10).text)
                links[url] = name

        return links


def collect_references(file_path):
    """Collect all exteral references in the generated file and download them."""
    parser = ExternalLinksParser(output_base_path=file_path.parent)
    parser.feed(file_path.read_text())
    print(f'Collected {len(parser.links)} external links')
    return parser.links


def replace_references(file_path, replaces):
    """Replace the references in the file."""
    replaced = file_path.read_text()
    for find, replace in replaces.items():
        if not replace:  # Remove it completely
            replaced = replaced.replace(f'<script src={find}></script>', '')
        else:
            replaced = replaced.replace(find, replace)

    print(f'Replaced external links in {file_path}')
    file_path.write_text(replaced)


def main():
    """Generate the documentation."""
    output_path = Path('doc/build')
    source_files = list(Path('tests/schemas/').glob('*.schema'))

    shutil.rmtree(output_path, ignore_errors=True)
    output_path.mkdir(mode=0o755, parents=True, exist_ok=True)
    print('Reset build directory')

    links = []
    for schema in source_files:
        print(f'Generating documentation for schema {schema}')
        schema_output = output_path / f'{schema.name}.html'
        subprocess.run(['generate-schema-doc', schema, schema_output], check=True)
        links.append(f'<li><p><a href="{schema.name}.html">{schema.with_suffix(".yaml").name}</a></p></li>')

    replaces = collect_references(output_path / f'{source_files[0].name}.html')
    for schema in source_files:
        replace_references(output_path / f'{schema.name}.html', replaces)

    (output_path / 'index.html').write_text(INDEX_PREFIX + '\n'.join(links) + INDEX_SUFFIX)


if __name__ == '__main__':
    exit(main())
