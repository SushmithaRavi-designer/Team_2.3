"""
Export Speckle Object Data to JSON and Subscribe to Real-time Updates

This script combines two functionalities:
1. Export: Fetches object data from Speckle using GraphQL and saves to JSON
2. Subscription: Subscribes to real-time project updates via WebSocket
"""

import json
import os
import asyncio
from pathlib import Path
from datetime import datetime
from main import get_client
from gql import gql, Client
from gql.transport.websockets import WebsocketsTransport
from dotenv import load_dotenv

# Load environment variables from .env file in script directory
script_dir = Path(__file__).parent
env_file = script_dir / ".env"
load_dotenv(env_file, override=True)

# Configuration
PROJECT_ID = "128262a20c"
OBJECT_ID = "b3c1d252a72eb229bea8f3150200a5f9"
YOUR_TOKEN = os.environ.get("SPECKLE_TOKEN")


# ============================================================================
# PART 1: EXPORT JSON FUNCTIONALITY
# ============================================================================

def query_object_data_graphql(client, project_id: str, object_id: str) -> dict:
    """
    Query object data from Speckle using GraphQL API.
    
    Args:
        client: Authenticated SpeckleClient instance
        project_id: The Speckle project ID
        object_id: The Speckle object ID
    
    Returns:
        Dictionary containing the query result
    """
    query = gql("""
    query GetObjectDataJSON($objectId: String!, $projectId: String!) {
        project(id: $projectId) {
            object(id: $objectId) {
                id
                speckleType
                data
            }
        }
    }
    """)
    
    variables = {
        "projectId": project_id,
        "objectId": object_id
    }
    
    # Execute GraphQL query using the client's HTTP session
    result = client.httpclient.execute(query, variable_values=variables)
    return result


def export_object_to_json():
    """
    Fetch object data and save to JSON file.
    """
    print("\n" + "=" * 60)
    print("EXPORTING OBJECT DATA TO JSON")
    print("=" * 60)
    
    # Authenticate with Speckle
    client = get_client()
    print(f"✓ Authenticated with Speckle")
    
    # Execute GraphQL query
    try:
        graphql_result = query_object_data_graphql(client, PROJECT_ID, OBJECT_ID)
        print(f"✓ GraphQL query executed successfully")
    except Exception as e:
        print(f"⚠ GraphQL query failed: {e}")
        return
    
    # Prepare output data
    output = {
        "projectId": PROJECT_ID,
        "objectId": OBJECT_ID,
        "data": graphql_result["project"]["object"]["data"]
    }
    
    # Save to JSON file with timestamp in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(script_dir, f"object_data_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✓ Saved object data to {output_file}\n")


# ============================================================================
# PART 2: SUBSCRIPTION FUNCTIONALITY
# ============================================================================

# Define the subscription query
subscription_query = gql("""
    subscription ProjectVersionsUpdated($projectId: String!) {
        projectVersionsUpdated(id: $projectId) {
            id
            modelId
            type
            version {
                id
                message
                createdAt
            }
        }
    }
""")


async def subscribe_to_project_updates():
    """
    Subscribe to project version updates using WebSocket
    """
    print("\n" + "=" * 60)
    print("SUBSCRIBING TO PROJECT UPDATES")
    print("=" * 60)
    print("INFO: WebSocket subscription started")
    
    if not YOUR_TOKEN:
        print("⚠ No SPECKLE_TOKEN found - skipping subscription")
        await asyncio.sleep(float('inf'))  # Keep running indefinitely
        return
    
    # Create WebSocket transport with authentication
    transport = WebsocketsTransport(
        url="wss://app.speckle.systems/graphql",
        init_payload={
            "Authorization": f"Bearer {YOUR_TOKEN}"
        }
    )
    
    # Create a GraphQL client
    client = Client(
        transport=transport,
        fetch_schema_from_transport=False,
    )
    
    try:
        async with client as session:
            print(f"🔌 Connected to Speckle WebSocket")
            print(f"📡 Listening for updates on project: {PROJECT_ID}")
            print("Press Ctrl+C to stop\n")
            
            try:
                # Subscribe to the query
                async for result in session.subscribe(
                    subscription_query,
                    variable_values={"projectId": PROJECT_ID}
                ):
                    print("=" * 50)
                    print("📦 New Update Received!")
                    print("=" * 50)
                    
                    data = result.get("projectVersionsUpdated")
                    if data:
                        print(f"ID: {data.get('id')}")
                        print(f"Model ID: {data.get('modelId')}")
                        print(f"Type: {data.get('type')}")
                        
                        version = data.get('version')
                        if version:
                            print(f"\nVersion Details:")
                            print(f"  - Version ID: {version.get('id')}")
                            print(f"  - Message: {version.get('message')}")
                            print(f"  - Created At: {version.get('createdAt')}")
                        
                        print("\n")
                    
            except asyncio.CancelledError:
                print("\n\n👋 Subscription cancelled")
                raise
            except KeyboardInterrupt:
                print("\n\n👋 Subscription stopped by user")
                raise
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception as e:
        print(f"\n⚠ WebSocket Connection Error: {e}")
        print("INFO: Continuing with periodic exports only...")
        await asyncio.sleep(float('inf'))
    finally:
        try:
            await transport.close()
        except:
            pass
        print("🔌 Connection closed")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def export_periodically(interval: int = 30):
    """
    Periodically export object data at specified intervals (in seconds)
    """
    import time
    while True:
        try:
            print("\n" + "=" * 60)
            print(f"[PERIODIC EXPORT] Exporting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            # Run the export in a thread with a 25-second timeout
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(export_object_to_json),
                    timeout=25.0
                )
            except asyncio.TimeoutError:
                print(f"⚠ Export timed out after 25 seconds")
        except Exception as e:
            print(f"⚠ Export failed: {e}")
        
        # Wait for the specified interval before next export
        await asyncio.sleep(interval)


async def main():
    """
    Main function to run both export and subscription features continuously
    """
    print("\n" + "=" * 60)
    print("SPECKLE EXPORT & SUBSCRIPTION TOOL - CONTINUOUS MODE")
    print("=" * 60)
    print("🔄 Running export every 30 seconds and subscription continuously")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Run export and subscription concurrently
        await asyncio.gather(
            export_periodically(interval=30),  # Export every 30 seconds
            subscribe_to_project_updates()      # Subscribe continuously
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n👋 Application stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
