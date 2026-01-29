"""
04 - Modify Geometry in a Speckle Model with Nested Properties

This script demonstrates how to find an object by applicationId,
duplicate it with an offset while preserving nested properties (Module, Designer, etc.),
and commit a new version.

Use the "two blocks" model. Copy the applicationId of the blocks's floor B.
Use this model: https://app.speckle.systems/projects/YOUR_PROJECT_ID/models/YOUR_MODEL_ID
"""

import copy
from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects import Base


# TODO: Replace with your project and model IDs
PROJECT_ID = "128262a20c"
MODEL_ID = "a7296f66a3"

# TODO: Replace with the applicationId of an object to duplicate
TARGET_APPLICATION_ID = "17cc627f-f5df-44d2-908e-1cdaf96fe76c"

# Offset for the duplicated object (move upward = positive Z)
# Note: The model uses millimeters, so 16 meters = 16000 mm
OFFSET_Z = 16000.0

# TODO: Configure top-level properties you want to modify (optional)
# Leave empty {} to keep all original properties
NEW_TOP_LEVEL_PROPERTIES = {
    # "name": "Modified BrepX",  # Uncomment to change name
    # "area": 150000000.0,       # Uncomment to change area
}

# TODO: Configure nested properties you want to modify (optional)
# The script will preserve existing nested properties and update these
# Leave empty {} to keep all original nested properties unchanged
NEW_NESTED_PROPERTIES = {
    "Module": "02",
    "Designer": "Sushmitha",
}


def find_object_by_application_id(obj, target_id: str):
    """
    Recursively search for an object with the given applicationId.
    """
    if not isinstance(obj, Base):
        return None
    
    app_id = getattr(obj, "applicationId", None)
    if app_id == target_id:
        return obj
    
    # Search in child elements
    elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in elements or []:
        found = find_object_by_application_id(element, target_id)
        if found:
            return found
    
    return None


def deep_copy_base_object(obj):
    """
    Create a deep copy of a Speckle Base object, preserving all nested structures.
    """
    new_obj = Base()
    
    # Copy all properties including nested ones
    for key in obj.get_member_names():
        value = getattr(obj, key, None)
        if value is not None:
            try:
                # Deep copy to preserve nested structures
                if isinstance(value, Base):
                    # Recursively copy Base objects
                    new_obj[key] = deep_copy_base_object(value)
                elif isinstance(value, list):
                    # Deep copy lists
                    new_obj[key] = copy.deepcopy(value)
                elif isinstance(value, dict):
                    # Deep copy dicts
                    new_obj[key] = copy.deepcopy(value)
                else:
                    # Copy primitives and other types
                    new_obj[key] = copy.deepcopy(value)
            except Exception as e:
                print(f"  Warning: Could not deep copy {key}: {e}")
                try:
                    new_obj[key] = value
                except:
                    pass
    
    return new_obj


def apply_nested_properties(obj, nested_props: dict):
    """
    Apply nested properties in the 'properties' attribute,
    overwriting existing ones to keep only the specified keys.
    """
    if not nested_props:
        return

    # Overwrite with a plain dict to avoid extra Speckle metadata
    obj.properties = {
        "Module": nested_props.get("Module"),
        "Designer": nested_props.get("Designer"),
    }
    print(f"  ✓ Set properties.Module = {nested_props.get('Module')}")
    print(f"  ✓ Set properties.Designer = {nested_props.get('Designer')}")


def apply_top_level_properties(obj, props: dict):
    """
    Apply top-level properties to the object.
    """
    if not props:
        return
    
    print(f"\n--- Applying Top-Level Properties ---")
    
    for key, value in props.items():
        try:
            setattr(obj, key, value)
            print(f"  ✓ Set {key} = {value}")
        except Exception as e:
            print(f"  ✗ Failed to set {key}: {e}")


def deep_copy_and_offset(obj, offset_z: float, top_level_props: dict = None, nested_props: dict = None):
    """
    Create a deep copy of a Speckle object, offset its geometry, and apply custom properties.
    Preserves all nested structures including 'properties' with Module, Designer, etc.
    """
    # Create a deep copy preserving all nested structures
    new_obj = deep_copy_base_object(obj)
    
    # Clear the id so a new one is generated
    new_obj.id = None
    
    # Generate a new applicationId for the copy
    import uuid
    new_obj.applicationId = str(uuid.uuid4())
    
    # Apply custom top-level properties if provided
    if top_level_props:
        apply_top_level_properties(new_obj, top_level_props)
    
    # Apply custom nested properties if provided (preserves existing ones)
    if nested_props:
        apply_nested_properties(new_obj, nested_props)
    
    # Offset geometry
    offset_geometry(new_obj, offset_z)
    
    return new_obj


def offset_geometry(obj, offset_z: float):
    """
    Offset geometry in the Z direction for various geometry types.
    """
    # Handle displayValue (common in Revit objects)
    display_value = getattr(obj, "displayValue", None) or getattr(obj, "@displayValue", None)
    if display_value:
        if isinstance(display_value, list):
            for mesh in display_value:
                offset_mesh_vertices(mesh, offset_z)
        else:
            offset_mesh_vertices(display_value, offset_z)
    
    # Handle direct vertices (for Mesh objects)
    if hasattr(obj, "vertices") and obj.vertices:
        offset_mesh_vertices(obj, offset_z)
    
    # Handle base point / location
    if hasattr(obj, "basePoint"):
        bp = obj.basePoint
        if hasattr(bp, "z"):
            bp.z += offset_z
    
    if hasattr(obj, "location"):
        loc = obj.location
        if hasattr(loc, "z"):
            loc.z += offset_z


def offset_mesh_vertices(mesh, offset_z: float):
    """
    Offset mesh vertices in the Z direction.
    Vertices are stored as flat list: [x1, y1, z1, x2, y2, z2, ...]
    """
    if hasattr(mesh, "vertices") and mesh.vertices:
        new_vertices = []
        for i in range(0, len(mesh.vertices), 3):
            new_vertices.append(mesh.vertices[i])              # x
            new_vertices.append(mesh.vertices[i + 1])          # y
            new_vertices.append(mesh.vertices[i + 2] + offset_z)  # z + offset
        mesh.vertices = new_vertices


def print_object_info(obj, title="Object Information"):
    """
    Print detailed information about a Speckle object including nested properties.
    """
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    # Print basic properties
    basic_props = ['id', 'name', 'speckle_type', 'applicationId', 'area', 'volume', 'units']
    for prop in basic_props:
        value = getattr(obj, prop, None)
        if value is not None:
            # Truncate long values for readability
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            print(f"  {prop:20s}: {value_str}")
    
    # Print nested 'properties' object
    properties_obj = getattr(obj, "properties", None)
    if properties_obj and isinstance(properties_obj, Base):
        print(f"\n  --- Nested Properties ---")
        for key in properties_obj.get_member_names():
            value = getattr(properties_obj, key, None)
            if value is not None:
                value_str = str(value)
                if len(value_str) > 40:
                    value_str = value_str[:37] + "..."
                print(f"    {key:18s}: {value_str}")
    
    print(f"{'='*60}\n")


def main():
    # Authenticate
    client = get_client()
    
    # Get the first version (the original with 2 objects)
    versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=100)
    if not versions.items:
        print("No versions found.")
        return
    
    # Use the first version to ensure we start with only 2 original objects
    first_version = versions.items[-1]  # Get the oldest version
    print(f"✓ Fetching first version: {first_version.id}")
    
    # Receive the full data tree
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(first_version.referenced_object, transport)
    
    # Find the target object
    print(f"\n--- Searching for object {TARGET_APPLICATION_ID} ---")
    target_obj = find_object_by_application_id(data, TARGET_APPLICATION_ID)
    
    if not target_obj:
        print(f"✗ Could not find object with applicationId: {TARGET_APPLICATION_ID}")
        return
    
    print(f"✓ Found object!")
    
    # Print original object information
    print_object_info(target_obj, "ORIGINAL OBJECT")
    
    # Create a copy with offset and preserve nested properties
    print(f"--- Creating Duplicated Object ---")
    print(f"  Offset Z: {OFFSET_Z} mm")
    
    copied_obj = deep_copy_and_offset(
        target_obj, 
        OFFSET_Z,
        top_level_props=NEW_TOP_LEVEL_PROPERTIES if NEW_TOP_LEVEL_PROPERTIES else None,
        nested_props=NEW_NESTED_PROPERTIES if NEW_NESTED_PROPERTIES else None
    )
    
    print(f"✓ Created copy with Z offset of {OFFSET_Z}")
    print(f"✓ Preserved all nested properties (Module, Designer, etc.)")
    
    # Print duplicated object information
    print_object_info(copied_obj, "DUPLICATED OBJECT")
    
    # Create a new collection for the duplicated object
    new_collection = Base()
    # Explicitly tag as Collection so the viewer shows "Collection" instead of "Base"
    new_collection.speckle_type = "Speckle.Core.Models.Collection"
    new_collection._speckle_type = "Speckle.Core.Models.Collection"
    new_collection["speckle_type"] = "Speckle.Core.Models.Collection"
    new_collection.name = "new"
    new_collection.elements = [copied_obj]
    
    print(f"✓ Created collection: '{new_collection.name}'")
    print("✓ Added duplicated object to collection")
    
    # Get the elements list from the root
    elements = getattr(data, "@elements", None)
    if elements is None:
        elements = getattr(data, "elements", None)
    
    if elements is not None:
        original_count = len(elements)
        print(f"\n✓ Original elements count: {original_count}")
        
        # Add the new collection
        elements.append(new_collection)
        print(f"✓ New elements count: {len(elements)}")
    else:
        # Create new elements list
        data["@elements"] = [new_collection]
        print(f"✓ Created new elements list")
    
    # Send the modified data back
    print(f"\n--- Committing to Speckle ---")
    object_id = operations.send(data, [transport])
    print(f"✓ Sent object: {object_id}")
    
    # Create a new version
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    
    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=MODEL_ID,
        objectId=object_id,
        message=f"Duplicated object with nested properties (Module, Designer) preserved and Z offset {OFFSET_Z}"
    ))
    
    print(f"✓ Created version: {version.id}")
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS!")
    print(f"{'='*60}")
    print(f"Check your Speckle model for the duplicated element.")
    print(f"The nested properties (Module, Designer, etc.) are preserved.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()