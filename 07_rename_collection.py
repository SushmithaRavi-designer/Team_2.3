from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects import Base
from specklepy.core.api.inputs.version_inputs import CreateVersionInput

PROJECT_ID = "128262a20c"
MODEL_ID = "0763ad7d28"
TARGET_APPID = "7173a954-412b-4606-b14c-c2bdb579af98"  # node currently named 'Collection'


def find_by_appid(root: Base, appid: str):
    if not isinstance(root, Base):
        return None
    if getattr(root, "applicationId", None) == appid:
        return root
    elements = getattr(root, "@elements", None) or getattr(root, "elements", None) or []
    for el in elements or []:
        if isinstance(el, Base):
            found = find_by_appid(el, appid)
            if found:
                return found
    for key in getattr(root, "get_member_names", lambda: [])():
        try:
            val = getattr(root, key)
        except Exception:
            val = None
        if isinstance(val, Base):
            found = find_by_appid(val, appid)
            if found:
                return found
    return None


def rename_member_by_name(root: Base, target_name: str, new_name: str):
    if not isinstance(root, Base):
        return False
    if getattr(root, "name", None) == target_name:
        root.name = new_name
        return True
    elements = getattr(root, "@elements", None) or getattr(root, "elements", None) or []
    for el in elements or []:
        if isinstance(el, Base) and rename_member_by_name(el, target_name, new_name):
            return True
    for key in getattr(root, "get_member_names", lambda: [])():
        try:
            val = getattr(root, key)
        except Exception:
            val = None
        if isinstance(val, Base) and rename_member_by_name(val, target_name, new_name):
            return True
    return False


def rename_child_under_parent(root: Base, parent_name: str, child_name: str, new_child_name: str):
    if not isinstance(root, Base):
        return False
    if getattr(root, "name", None) == parent_name:
        elements = getattr(root, "@elements", None) or getattr(root, "elements", None) or []
        for el in elements or []:
            if isinstance(el, Base) and getattr(el, "name", None) == child_name:
                el.name = new_child_name
                return True
    elements = getattr(root, "@elements", None) or getattr(root, "elements", None) or []
    for el in elements or []:
        if isinstance(el, Base) and rename_child_under_parent(el, parent_name, child_name, new_child_name):
            return True
    for key in getattr(root, "get_member_names", lambda: [])():
        try:
            val = getattr(root, key)
        except Exception:
            val = None
        if isinstance(val, Base) and rename_child_under_parent(val, parent_name, child_name, new_child_name):
            return True
    return False


if __name__ == '__main__':
    client = get_client()
    versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=10)
    if not versions.items:
        print("No versions found")
        raise SystemExit(1)
    latest = versions.items[0]
    print(f"Using latest version: {latest.id}")

    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    root = operations.receive(latest.referenced_object, transport)

    print("\n--- Applying renames: root -> 'Specklypy model', 'Layer 01' -> 'old', child 'Layer' -> 'Collection' ---")
    root.name = "Specklypy model"
    renamed = rename_member_by_name(root, "Layer 01", "old")
    print(f"  ✓ Renamed 'Layer 01' -> 'old': {renamed}")
    child_renamed = rename_child_under_parent(root, "old", "Layer", "old")
    print(f"  ✓ Renamed child 'Layer' under 'old' -> 'old': {child_renamed}")

    node = find_by_appid(root, TARGET_APPID)
    if not node:
        print(f"Could not find node with applicationId {TARGET_APPID}")
        raise SystemExit(1)

    print(f"Found node: current name={getattr(node,'name',None)} type={getattr(node,'speckle_type',None)}")
    node.name = "old_modules"
    node.speckle_type = "Speckle.Core.Models.Collection"
    node._speckle_type = "Speckle.Core.Models.Collection"
    try:
        node["speckle_type"] = "Speckle.Core.Models.Collection"
    except Exception:
        pass

    # send
    object_id = operations.send(root, [transport])
    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=MODEL_ID,
        objectId=object_id,
        message=f"Rename collection {TARGET_APPID} -> old"
    ))
    print(f"Created version: {version.id}")
