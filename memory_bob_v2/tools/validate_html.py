import sys
import json
from pathlib import Path
from html.parser import HTMLParser

class SimpleHTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.stack = []
        self.self_closing = {
            'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'
        }

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.self_closing:
            self.stack.append((tag.lower(), self.getpos()))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.self_closing:
            return
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}> at line {self.getpos()[0]}")
            return
        top_tag, _ = self.stack[-1]
        if top_tag == tag:
            self.stack.pop()
        else:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    for j in range(len(self.stack) - 1, i, -1):
                        unclosed_tag, pos = self.stack.pop()
                        self.errors.append(f"Unclosed tag <{unclosed_tag}> from line {pos[0]}")
                    self.stack.pop()
                    return
            self.errors.append(f"Mismatched closing tag </{tag}> at line {self.getpos()[0]}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].strip():
        target = Path(sys.argv[1])
    else:
        base = Path(__file__).resolve().parent.parent
        target = base / "blog.html"
        if not target.exists():
            target = base / "memory" / "blog.html"

    if not target.exists():
        print(json.dumps({"error": f"File not found: {target}"}))
        sys.exit(1)

    try:
        content = target.read_text(encoding="utf-8")
        parser = SimpleHTMLValidator()
        parser.feed(content)
        
        unclosed = [f"<{tag}> from line {pos[0]}" for tag, pos in parser.stack]
        is_valid = len(parser.errors) == 0 and len(unclosed) == 0
        
        res = {
            "file": str(target.resolve()),
            "valid": is_valid,
            "errors": parser.errors,
            "unclosed_tags": unclosed
        }
        print(json.dumps(res, indent=2))
        sys.exit(0 if is_valid else 1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
