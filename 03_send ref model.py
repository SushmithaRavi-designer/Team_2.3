from main import get_client
from specklepy.api.operations import receive, send
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.core.api.inputs.version_inputs import CreateVersionInput

PROJECT_ID       = "128262a20c"
SOURCE_MODEL_ID  = "a1014e4b32"
DEST_MODEL_ID    = "0763ad7d28"

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

    print("📤 Sending to destination...")

    new_obj_id = send(obj, [dest_transport])

    print(f"✅ Object sent with ID: {new_obj_id}")

    # 🔹 Create version using API helper
    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=DEST_MODEL_ID,
        objectId=new_obj_id,
        message="Model copied from homework/session02/_ref-geo"
    ))

    print(f"✅ Model copied successfully! Version ID: {version.id}")

if __name__ == "__main__":
    copy_model_data()