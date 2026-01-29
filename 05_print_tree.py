from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects import Base

PROJECT_ID = "128262a20c"
MODEL_ID = "a7296f66a3"


def walk_tree_print(root: Base, depth: int = 0):
    if not isinstance(root, Base):
        return
    indent = "  " * depth
    name = getattr(root, "name", "(no name)")
    s_type = getattr(root, "speckle_type", getattr(root, "_speckle_type", "(no type)"))
    app_id = getattr(root, "applicationId", None)
    print(f"{indent}- name: {name!s} | type: {s_type!s} | appId: {app_id}")

    elements = getattr(root, "@elements", None) or getattr(root, "elements", None) or []
    for el in elements or []:
        if isinstance(el, Base):
            walk_tree_print(el, depth + 1)

    for key in getattr(root, "get_member_names", lambda: [])():
        try:
            val = getattr(root, key)
        except Exception:
            val = None
        if isinstance(val, Base):
            walk_tree_print(val, depth + 1)


if __name__ == '__main__':
    client = get_client()
    versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=10)
    if not versions.items:
        print("No versions found")
        raise SystemExit(1)
    print("Recent versions:")
    for v in versions.items[:5]:
        print(f"  - {v.id}  referenced_object={v.referenced_object}")

    latest = versions.items[0]
    print(f"\nUsing latest version: {latest.id}\n")
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(latest.referenced_object, transport)

    print("--- Model tree (latest) ---")
    walk_tree_print(data)
