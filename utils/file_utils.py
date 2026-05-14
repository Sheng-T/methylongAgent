import os
import re
from bs4 import BeautifulSoup
import html2text
import requests
from urllib.parse import urljoin, urlparse
import time


def setup_converter():
    """Configure HTML to Markdown converter."""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.bypass_tables = False
    converter.ignore_images = True
    converter.code_style = 'backticks'
    converter.body_width = 0
    return converter


def clean_html_and_convert(file_path, converter):
    """Clean HTML and extract core content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    main_content = (
        soup.find('main') or
        soup.find('article') or
        soup.find('div', {'class': 'document'}) or
        soup.find('div', {'id': 'content'}) or
        soup.body
    )

    if not main_content:
        return ""

    for tag in main_content.find_all(['nav', 'footer', 'script', 'style', 'header']):
        tag.decompose()

    title = soup.title.string if soup.title else os.path.basename(file_path)
    title = re.sub(r' — .*', '', title)

    raw_md = converter.handle(str(main_content))
    raw_md = re.sub(r'^(#+)\s', r'#\1 ', raw_md, flags=re.MULTILINE)

    markdown_text = f"\n\n# Tool Documentation: {title}\n\n"
    markdown_text += raw_md

    return markdown_text


def html2md(input_dir, output_file, title):
    converter = setup_converter()
    all_markdown = f"# {title}\n"

    file_list = []
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            if f.endswith('.html'):
                file_list.append(os.path.join(root, f))

    file_list.sort()

    for file_path in file_list:
        try:
            md_content = clean_html_and_convert(file_path, converter)
            all_markdown += md_content
        except Exception as e:
            print(f"Error: cannot process {file_path} - {str(e)}")

    all_markdown = re.sub(r'\n{3,}', '\n\n', all_markdown)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(all_markdown)

    print(f"Done. Markdown saved to: {output_file}")
