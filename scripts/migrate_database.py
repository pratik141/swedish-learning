from sprakverkstan import create_app
from sprakverkstan.migrations import upgrade_all


app = create_app({"AUTO_CREATE_TABLES": False})
for result in upgrade_all(app):
    detail = "already applied" if result["already_applied"] else f"imported {result['imported']} records"
    print(f"Migration {result['revision']}: {detail}")