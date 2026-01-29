"""
Create a model in the CW26-Sessions project under homework/session03
"""

from main import get_client
from gql import gql

# The project ID from the URL
PROJECT_ID = "128262a20c"

"""
Create a model in the CW26-Sessions project under homework/session03
"""

from main import get_client

# The project ID from the URL
PROJECT_ID = "128262a20c"

def main():
    # Authenticate
    client = get_client()
    
    # Get the project
    project = client.project.get(PROJECT_ID)
    print(f"✓ Found project: {project.name}")
    
    # Create a model using the GraphQL mutation directly
    model_name = "homework/session03/team_02.3"
    
    # Use the low-level GraphQL API
    query = gql("mutation CreateModel($input: CreateModelInput!) { modelMutations { create(input: $input) { id name } } }")
    
    variables = {
        "input": {
            "projectId": PROJECT_ID,
            "name": model_name,
            "description": "Learning specklepy"
        }
    }
    
    try:
        result = client.httpclient.execute(query, variable_values=variables)
        model_id = result["data"]["modelMutations"]["create"]["id"]
    except Exception as e:
        # Try to extract error message from gql TransportQueryError
        error_msg = str(e)
        if hasattr(e, 'errors') and e.errors:
            error_msg = e.errors[0].get('message', error_msg)
        elif hasattr(e, 'message'):
            error_msg = e.message
        print(f"✗ Error creating model: {error_msg}")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()