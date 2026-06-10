"""Fix the final bad byte in setup_pgvector.py."""
path = "scripts/setup_pgvector.py"

with open(path, "rb") as f:
    raw = f.read()

# Replace the bad sequence: dagger + control char -> #
raw = raw.replace(b"\xe2\x80\xa0\xc2\x90", b"#")

with open(path, "wb") as f:
    f.write(raw)

print("Fixed. Checking syntax...")
import ast
try:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SyntaxError line {e.lineno}: {e.msg}")
    print(repr(e.text))
