import sys
import json
from pathlib import Path
from html.parser import HTMLParser

class SimpleHTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
        self.self_closing = {'img', 'br', 'hr', 'meta', 'link', 'input'}

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.self_closing:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.self_closing:
            return
        if not self.stack:
            self.errors.append(f'Unexpected closing tag: </{tag}>')
        elif self.stack[-1] == tag_lower:
            self.stack.pop()
        else:
            self.errors.append(f'Mismatched closing tag: </{tag}>, expected </{self.stack[-1]}>')

def validate_html_file(filepath):
    p = Path(filepath)
    if not p.exists():
        return {'file': str(p), 'valid': False, 'error': 'File not found'}
    
    content = p.read_text(encoding='utf-8')
    parser = SimpleHTMLValidator()
    try:
        parser.feed(content)
        parser.close()
    except Exception as e:
        return {'file': str(p), 'valid': False, 'error': str(e)}

    unclosed = parser.stack
    errors = parser.errors

    valid = len(errors) == 0 and len(unclosed) == 0
    return {
        'file': str(p),
        'valid': valid,
        'errors': errors,
        'unclosed_tags': unclosed
    }

if __name__ == '__main__':
    memory_dir = Path(__file__).resolve().parent.parent
    target = memory_dir / 'blog.html'
    result = validate_html_file(target)
    print(json.dumps(result, indent=2))
    if not result['valid']:
        sys.exit(1)
