from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects import Base
from specklepy.core.api.inputs.version_inputs import CreateVersionInput

PROJECT_ID = "128262a20c"
MODEL_ID = "0763ad7d28"
NEW_ROOT_NAME = "Specklepy"

client = get_client()
versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=10)
if not versions.items:
    print("No versions found")
    raise SystemExit(1)

latest = versions.items[0]
print(f"Using latest version: {latest.id}")
transport = ServerTransport(client=client, stream_id=PROJECT_ID)
root = operations.receive(latest.referenced_object, transport)

print(f"Current root name: {getattr(root,'name',None)}")
root.name = NEW_ROOT_NAME

object_id = operations.send(root, [transport])
version = client.version.create(CreateVersionInput(
    projectId=PROJECT_ID,
    modelId=MODEL_ID,
    objectId=object_id,
    message=f"Rename root -> {NEW_ROOT_NAME}"
))
print(f"Created version: {version.id}")
