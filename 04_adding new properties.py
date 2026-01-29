"""
03 - Add Properties to Objects/Elements in a Speckle Model

This script demonstrates how to receive objects from Speckle,
add custom properties to individual elements based on their position,
and send them back as a new version.

Use this model: https://app.speckle.systems/projects/YOUR_PROJECT_ID/models/YOUR_MODEL_ID
"""

from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects.base import Base


# TODO: Replace with your project, model, and version IDs
PROJECT_ID = "128262a20c"
MODEL_ID = "9da8725bf2"

# Define module numbers and designers for each Z-height range
# Based on Z-height: Bottom elements, Middle elements (blue), Top elements
ELEMENT_PROPERTIES = [
    {"Module": "01", "Designer": "Nihan"},      # Bottom elements
    {"Module": "02", "Designer": "Sushmitha"},  # Middle elements (blue)
    {"Module": "03", "Designer": "Marina"}      # Top elements
]


def find_all_elements(obj, elements=None):
    """
    Recursively find all objects/elements in the tree.
    """
    if elements is None:
        elements = []
    
    if not isinstance(obj, Base):
        return elements
    
    # Check if this object has geometric properties (likely an element)
    has_geometry = (
        hasattr(obj, "displayValue") or 
        hasattr(obj, "@displayValue") or
        hasattr(obj, "basePoint") or
        hasattr(obj, "location") or
        hasattr(obj, "vertices")
    )
    
    # Add if it's not a Collection but has geometric properties
    speckle_type = getattr(obj, "speckle_type", "")
    if has_geometry and "Collection" not in speckle_type:
        elements.append(obj)
    
    # Search in child elements
    child_elements = getattr(obj, "@elements", None) or getattr(obj, "elements", [])
    for element in child_elements or []:
        find_all_elements(element, elements)
    
    # Also check for collections property and search within them
    colls = getattr(obj, "collections", None)
    if colls:
        for coll in colls:
            find_all_elements(coll, elements)
    
    return elements


def get_z_position(obj):
    """Extract Z coordinate from object for sorting"""
    # Try direct properties first
    if hasattr(obj, "basePoint") and hasattr(obj.basePoint, "z"):
        return obj.basePoint.z
    if hasattr(obj, "location") and hasattr(obj.location, "z"):
        return obj.location.z
    
    # Try to get from displayValue mesh vertices
    display_value = getattr(obj, "displayValue", None) or getattr(obj, "@displayValue", None)
    if display_value:
        meshes = display_value if isinstance(display_value, list) else [display_value]
        for mesh in meshes:
            if hasattr(mesh, "vertices") and mesh.vertices and len(mesh.vertices) >= 3:
                # Get Z coordinates (every 3rd value starting from index 2)
                z_coords = [mesh.vertices[i] for i in range(2, min(len(mesh.vertices), 30), 3)]
                if z_coords:
                    return sum(z_coords) / len(z_coords)
    
    return 0  # Default if no Z found


def assign_properties_by_z_ranges(elements):
    """
    Assign properties to elements based on their Z-position.
    Divides elements into equal groups based on Z-height.
    """
    if not elements:
        return
    
    # Get Z positions for all elements
    element_z_pairs = [(elem, get_z_position(elem)) for elem in elements]
    
    # Find min and max Z values
    z_values = [z for _, z in element_z_pairs]
    min_z = min(z_values)
    max_z = max(z_values)
    
    # Calculate Z-range boundaries for each group
    z_range = max_z - min_z
    num_groups = len(ELEMENT_PROPERTIES)
    
    print(f"✓ Z-range: {min_z:.2f} to {max_z:.2f}")
    
    # Assign properties based on Z-position
    property_counts = [0] * num_groups

    for element, z_pos in element_z_pairs:
        if z_range == 0:
            group_index = 0
        else:
            # Calculate which third (or group) the element falls into
            normalized_z = (z_pos - min_z) / z_range
            group_index = min(int(normalized_z * num_groups), num_groups - 1)
        
        # Overwrite properties with a plain dict (keeps only Module and Designer)
        element.properties = {
            "Module": ELEMENT_PROPERTIES[group_index]["Module"],
            "Designer": ELEMENT_PROPERTIES[group_index]["Designer"],
        }
        
        property_counts[group_index] += 1

    # Print summary
    for i, count in enumerate(property_counts):
        z_start = min_z + (i * z_range / num_groups)
        z_end = min_z + ((i + 1) * z_range / num_groups)
        print(f"  ✓ Group {i+1} (Z: {z_start:.2f} to {z_end:.2f}): {count} elements - Module={ELEMENT_PROPERTIES[i]['Module']}, Designer={ELEMENT_PROPERTIES[i]['Designer']}")


def main():
    # Authenticate
    client = get_client()

    # Get the latest version
    versions = client.version.get_versions(MODEL_ID, PROJECT_ID, limit=1)
    if not versions.items:
        print("No versions found.")
        return
    
    latest_version = versions.items[0]
    print(f"✓ Fetching version: {latest_version.id}")

    # Receive the data
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(latest_version.referenced_object, transport)

    # Find all elements in the model
    elements = find_all_elements(data)
    
    if not elements:
        print("✗ No elements found in the model")
        return
    
    print(f"✓ Found {len(elements)} elements")

    # Assign properties to elements based on their Z-position
    assign_properties_by_z_ranges(elements)

    print(f"✓ Added Module and Designer properties to {len(elements)} elements")

    # Add custom properties at the root level (do not alter other data)
    data["custom_property"] = "Hello from specklepy!"
    data["analysis_date"] = "2026-01-29"
    data["processed_by"] = "Team_02.3"

    # Send the modified data back to Speckle
    object_id = operations.send(data, [transport])
    print(f"✓ Sent object: {object_id}")

    # Create a new version with the modified data
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput

    version = client.version.create(CreateVersionInput(
        projectId=PROJECT_ID,
        modelId=MODEL_ID,
        objectId=object_id,
        message="Added Module and Designer properties to individual elements based on Z-position"
    ))

    print(f"✓ Created version: {version.id}")


if __name__ == "__main__":
    main()