import json
import sys
from pathlib import Path
from html.parser import HTMLParser

class SimpleHTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.stack = []
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.void_tags:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.void_tags:
            return
        if self.stack and self.stack[-1] == tag_lower:
            self.stack.pop()
        elif tag_lower in self.stack:
            while self.stack and self.stack[-1] != tag_lower:
                unmatched = self.stack.pop()
                self.errors.append(f"Unclosed tag: <{unmatched}> before </{tag_lower}>")
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"Unexpected closing tag: </{tag_lower}>")

def validate_file(target_path):
    p = Path(target_path).resolve()
    if not p.is_file():
        return {"error": f"File not found: {target_path}"}

    try:
        content = p.read_text(encoding='utf-8')
        parser = SimpleHTMLValidator()
        parser.feed(content)
        unclosed = parser.stack
        is_valid = len(parser.errors) == 0 and len(unclosed) == 0
        return {
            "file": str(p),
            "valid": is_valid,
            "errors": parser.errors,
            "unclosed_tags": unclosed
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parent.parent
    default_target = workspace_root / "memory" / "blog.html"
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = default_target
        
    result = validate_file(target)
    print(json.dumps(result, indent=2))
    if "error" in result or not result.get("valid", False):
        sys.exit(1)
    sys.exit(0)
