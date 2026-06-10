with open("scripts/setup_pgvector.py", "rb") as f:
    content = f.read()

lines = content.split(b"\n")
for i, line in enumerate(lines[1405:1413], start=1406):
    print(f"line {i}: {repr(line)}")
