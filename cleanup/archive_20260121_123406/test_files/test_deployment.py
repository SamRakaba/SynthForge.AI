"""Test script to check model deployments and agent creation."""
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

iac_endpoint = 'https://ifraforge.services.ai.azure.com/api/projects/infrasynth'

try:
    print('=== Checking ifraforge Project ===')
    print(f'Endpoint: {iac_endpoint}')
    print()
    
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        credential=credential,
        endpoint=iac_endpoint,
    )
    
    print('Connected to project')
    print()
    
    # Get agents client
    agents_client = project_client.agents
    
    # List connections
    print('=== Available Connections ===')
    try:
        connections = project_client.connections.list()
        count = 0
        for conn in connections:
            count += 1
            print(f'{count}. {conn.name}')
            conn_type = getattr(conn, 'connection_type', 'N/A')
            print(f'   Type: {conn_type}')
    except Exception as e:
        print(f'Unable to list connections: {e}')
    
    print()
    print('=== Testing Agent Creation ===')
    
    # Test with gpt-5.2-codex
    print()
    print('1. Testing with: gpt-5.2-codex')
    try:
        test_agent = agents_client.create(
            model='gpt-5.2-codex',
            name='test-deployment-gpt52codex',
            instructions='Test agent for deployment validation',
        )
        print(f'   SUCCESS - Agent ID: {test_agent.id}')
        agents_client.delete(test_agent.id)
        print('   Cleanup complete')
    except Exception as e:
        print(f'   FAILED: {e}')
        error_str = str(e)
        if 'approval denied' in error_str.lower():
            print()
            print('   APPROVAL POLICY BLOCKING AGENT CREATION')
            print('   This is a governance/policy issue, not a model issue')
            print('   The deployment exists but requires manual approval')
    
    # Test with fallback gpt-4.1
    print()
    print('2. Testing with: gpt-4.1')
    try:
        test_agent = agents_client.create(
            model='gpt-4.1',
            name='test-deployment-gpt41',
            instructions='Test agent for fallback model',
        )
        print(f'   SUCCESS - Agent ID: {test_agent.id}')
        agents_client.delete(test_agent.id)
        print('   Cleanup complete')
    except Exception as e:
        print(f'   FAILED: {e}')
    
    # Test with standard gpt-4o
    print()
    print('3. Testing with: gpt-4o')
    try:
        test_agent = agents_client.create(
            model='gpt-4o',
            name='test-deployment-gpt4o',
            instructions='Test agent for standard model',
        )
        print(f'   SUCCESS - Agent ID: {test_agent.id}')
        agents_client.delete(test_agent.id)
        print('   Cleanup complete')
    except Exception as e:
        print(f'   FAILED: {e}')

except Exception as e:
    print(f'Connection failed: {e}')
    import traceback
    traceback.print_exc()
