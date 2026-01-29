from main import get_client
from specklepy.api.operations import receive, send
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.core.api.inputs.version_inputs import CreateVersionInput
import copy
from specklepy.objects.base import Base

PROJECT_ID       = "128262a20c"
SOURCE_MODEL_ID  = "a1014e4b32"
DEST_MODEL_ID    = "9da8725bf2"
TARGET_CHILD_APPID = "7173a954-412b-4606-b14c-c2bdb579af98"

def copy_model_data():
    client = get_client()

    # 🔹 Get latest version from source model using API helper
    versions = client.version.get_versions(model_id=SOURCE_MODEL_ID, project_id=PROJECT_ID, limit=1)
    if not versions.items:
        print("❌ No versions found in source model")
        return

    latest_version = versions.items[0]
    ref_object = getattr(latest_version, "referenced_object", None) or getattr(latest_version, "referencedObject", None)

    print(f"📥 Receiving version {latest_version.id}: {getattr(latest_version, 'message', '')}")

    source_transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    dest_transport   = ServerTransport(client=client, stream_id=PROJECT_ID)

    obj = receive(ref_object, source_transport)

    # Ensure we send a fresh object that preserves all top-level properties
    def deep_copy_base(src: Base) -> Base:
        dst = Base()
        for name in src.get_member_names():
            try:
                val = getattr(src, name)
                if isinstance(val, Base):
                    dst[name] = deep_copy_base(val)
                else:
                    dst[name] = copy.deepcopy(val)
            except Exception:
                try:
                    dst[name] = getattr(src, name)
                except Exception:
                    pass
        dst.id = None
        return dst

    send_obj = deep_copy_base(obj)

    # Ensure specific root-level metadata/properties are preserved
    root_props_to_copy = ["custom_property", "analysis_date", "processed_by"]
    for p in root_props_to_copy:
        if hasattr(obj, p):
            try:
                setattr(send_obj, p, copy.deepcopy(getattr(obj, p)))
                print(f"✓ Preserved root property: {p} = {getattr(send_obj, p)}")
            except Exception:
                pass

    # Rename root collection and specific child layers as requested
    try:
        send_obj.name = "python model"
        print("✓ Renamed root collection to 'python model'")
    except Exception:
        pass

    def rename_member_by_name(o, target, new_name):
        if not isinstance(o, Base):
            return False
        try:
            if getattr(o, "name", None) == target:
                setattr(o, "name", new_name)
                return True
        except Exception:
            pass
        children = getattr(o, "@elements", None) or getattr(o, "elements", None) or []
        for c in children:
            if rename_member_by_name(c, target, new_name):
                return True
        return False

    if rename_member_by_name(send_obj, "Layer 01", "old"):
        print("✓ Renamed 'Layer 01' to 'old'")

    # Additionally rename any child collections/layers by speckle_type
    def rename_by_speckle_type(o, substrings, new_name):
        if not isinstance(o, Base):
            return
        stype = getattr(o, "speckle_type", "") or getattr(o, "_speckle_type", "")
        if any(s in str(stype) for s in substrings):
            try:
                setattr(o, "name", new_name)
            except Exception:
                pass
        children = getattr(o, "@elements", None) or getattr(o, "elements", None) or []
        for c in children:
            rename_by_speckle_type(c, substrings, new_name)

    rename_by_speckle_type(send_obj, ["Layer", "Collection"], "old")
    print("✓ Renamed child collections/layers with matching speckle_type to 'old'")

    # Specifically set any child whose speckle_type contains 'Layer' to have name 'Collection'
    def set_name_for_speckle_substring(o, substring, new_name):
        if not isinstance(o, Base):
            return
        stype = getattr(o, "speckle_type", "") or getattr(o, "_speckle_type", "")
        if substring in str(stype):
            try:
                setattr(o, "name", new_name)
                # also set speckle type to a Collection so viewer treats it as collection
                setattr(o, "speckle_type", "Speckle.Core.Models.Collection")
                try:
                    setattr(o, "_speckle_type", "Speckle.Core.Models.Collection")
                except Exception:
                    pass
                try:
                    o["speckle_type"] = "Speckle.Core.Models.Collection"
                except Exception:
                    pass
            except Exception:
                pass
        children = getattr(o, "@elements", None) or getattr(o, "elements", None) or []
        for c in children:
            set_name_for_speckle_substring(c, substring, new_name)

    set_name_for_speckle_substring(send_obj, "Layer", "Collection")
    print("✓ Set name 'Collection' for nodes with speckle_type containing 'Layer'")

    # Targeted rename: find child by applicationId and rename to 'old'
    def set_name_by_appid(o, appid, new_name):
        if not isinstance(o, Base):
            return False
        try:
            if getattr(o, "applicationId", None) == appid:
                setattr(o, "name", new_name)
                try:
                    setattr(o, "speckle_type", "Speckle.Core.Models.Collection")
                except Exception:
                    pass
                try:
                    setattr(o, "_speckle_type", "Speckle.Core.Models.Collection")
                except Exception:
                    pass
                try:
                    o["speckle_type"] = "Speckle.Core.Models.Collection"
                except Exception:
                    pass
                return True
        except Exception:
            pass
        children = getattr(o, "@elements", None) or getattr(o, "elements", None) or []
        for c in children:
            if set_name_by_appid(c, appid, new_name):
                return True
        return False

    if set_name_by_appid(send_obj, TARGET_CHILD_APPID, "old"):
        print(f"✓ Renamed child with applicationId {TARGET_CHILD_APPID} to 'old'")

    # Rename any child named 'Layer' that is directly under a parent named 'old' to 'Collection'
    def rename_child_under_parent(o, parent_name, child_name, new_name):
        if not isinstance(o, Base):
            return False
        # if this node is the parent, rename its child
        try:
            if getattr(o, 'name', None) == parent_name:
                children = getattr(o, '@elements', None) or getattr(o, 'elements', None) or []
                changed = False
                for c in children:
                    try:
                        if getattr(c, 'name', None) == child_name:
                            setattr(c, 'name', new_name)
                            try:
                                setattr(c, 'speckle_type', 'Speckle.Core.Models.Collection')
                            except Exception:
                                pass
                            try:
                                setattr(c, '_speckle_type', 'Speckle.Core.Models.Collection')
                            except Exception:
                                pass
                            try:
                                c['speckle_type'] = 'Speckle.Core.Models.Collection'
                            except Exception:
                                pass
                            changed = True
                    except Exception:
                        pass
                return changed
        except Exception:
            pass
        # otherwise recurse
        children = getattr(o, '@elements', None) or getattr(o, 'elements', None) or []
        for c in children:
            if rename_child_under_parent(c, parent_name, child_name, new_name):
                return True
        return False

    if rename_child_under_parent(send_obj, 'old', 'Layer', 'Collection'):
        print("✓ Renamed child 'Layer' under parent 'old' to 'Collection'")
    # Ensure root keeps the desired name (override any blanket renames)
    try:
        send_obj.name = "python model"
        print("✓ Ensured root collection is named 'python model'")
    except Exception:
        pass

    print("📤 Sending to destination...")

    # Rename any child currently named 'Layer' to 'Collection'
    if rename_member_by_name(send_obj, "Layer", "Collection"):
        print("✓ Renamed 'Layer' to 'Collection'")

    new_obj_id = send(send_obj, [dest_transport])

    print(f"✅ Object sent with ID: {new_obj_id}")

    # 🔹 Create version using API helper
    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=DEST_MODEL_ID,
        objectId=new_obj_id,
        message="Model copied from homework/session02/_ref-geo"
    ))

    print(f"✅ Model copied successfully! Version ID: {version.id}")

    # --- Verify: receive the destination version root and print its top-level properties
    try:
        ref_new = getattr(version, "referenced_object", None) or getattr(version, "referencedObject", None)
        if ref_new:
            received_root = receive(ref_new, dest_transport)
            print("\n--- Destination root properties ---")
            if isinstance(received_root, Base):
                for name in received_root.get_member_names():
                    try:
                        val = getattr(received_root, name)
                        print(f"{name}: {val}")
                    except Exception:
                        pass
            else:
                print(received_root)
    except Exception as e:
        print(f"Could not fetch/print destination root properties: {e}")

if __name__ == "__main__":
    copy_model_data()