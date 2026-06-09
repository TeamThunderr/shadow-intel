import os
import re

backend_dir = "backend"

for root, dirs, files in os.walk(backend_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Replace "from backend." with "from "
            new_content = re.sub(r"^(\s*)from backend\.", r"\1from ", content, flags=re.MULTILINE)
            
            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Fixed {path}")

print("Done.")
