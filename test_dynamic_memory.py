#!/usr/bin/env python3
"""
Advanced test for dynamic data in memory
"""
import boto3
import json
import uuid

# Configuration
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7"
REGION = "us-west-2"


def invoke_agent(client, runtime_arn, payload, session_id):
    """Invoke agent and print results"""
    
    print(f"\n📤 Prompt: {payload['prompt']}")
    if 'preferences' in payload:
        print(f"📦 Preferences: {payload['preferences']}")
    if 'custom_data' in payload:
        print(f"📦 Custom Data: {payload['custom_data']}")
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            contentType='application/json',
            payload=json.dumps(payload),
            qualifier='DEFAULT'
        )
        
        if 'output' in response:
            result = response['output']
        elif hasattr(response.get('body'), 'read'):
            result = response['body'].read().decode('utf-8')
        else:
            result = str(response)
        
        print(f"📥 Response: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_basic_memory():
    """Test basic preference persistence"""
    
    client = boto3.client('bedrock-agentcore', region_name=REGION)
    session_id = f"basic-test-{uuid.uuid4()}"
    
    print(f"\n{'='*70}")
    print(f"🧪 Test 1: Basic Memory Persistence")
    print(f"{'='*70}")
    print(f"Session: {session_id}\n")
    
    # Turn 1
    print("🔵 Turn 1: Set user preferences")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "Hi! I'm Bob and I like coding.",
        "session_id": session_id,
        "preferences": {
            "hobby": "programming",
            "favorite_language": "python"
        }
    }, session_id)
    
    # Turn 2
    print("\n🔵 Turn 2: Test memory (no preferences sent)")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "What programming language do I prefer?",
        "session_id": session_id
    }, session_id)
    
    print(f"\n{'='*70}")
    print("✅ Basic test complete!")
    print(f"{'='*70}\n")


def test_custom_data():
    """Test custom data storage"""
    
    client = boto3.client('bedrock-agentcore', region_name=REGION)
    session_id = f"custom-test-{uuid.uuid4()}"
    
    print(f"\n{'='*70}")
    print(f"🧪 Test 2: Custom Data Storage")
    print(f"{'='*70}")
    print(f"Session: {session_id}\n")
    
    # Turn 1
    print("🔵 Turn 1: Store shopping cart data")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "I want to buy a laptop",
        "session_id": session_id,
        "preferences": {
            "budget": 2000
        },
        "custom_data": {
            "cart_id": "cart-123",
            "items": ["MacBook Pro"],
            "total": 1999
        }
    }, session_id)
    
    # Turn 2
    print("\n🔵 Turn 2: Add another item (data persists)")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "Add a mouse to my cart",
        "session_id": session_id
    }, session_id)
    
    print(f"\n{'='*70}")
    print("✅ Custom data test complete!")
    print(f"{'='*70}\n")


def test_data_update():
    """Test updating persisted data"""
    
    client = boto3.client('bedrock-agentcore', region_name=REGION)
    session_id = f"update-test-{uuid.uuid4()}"
    
    print(f"\n{'='*70}")
    print(f"🧪 Test 3: Update Persisted Data")
    print(f"{'='*70}")
    print(f"Session: {session_id}\n")
    
    # Turn 1
    print("🔵 Turn 1: Set initial budget")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "I have $1000 budget",
        "session_id": session_id,
        "preferences": {
            "budget": 1000
        }
    }, session_id)
    
    # Turn 2
    print("\n🔵 Turn 2: Update budget")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "Actually, I can increase it to $1500",
        "session_id": session_id,
        "preferences": {
            "budget": 1500
        }
    }, session_id)
    
    # Turn 3
    print("\n🔵 Turn 3: Verify updated budget")
    print("-" * 70)
    invoke_agent(client, RUNTIME_ARN, {
        "prompt": "What's my budget?",
        "session_id": session_id
    }, session_id)
    
    print(f"\n{'='*70}")
    print("✅ Update test complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import sys
    
    print(f"\n{'='*70}")
    print(f"🚀 Dynamic Memory Test Suite")
    print(f"{'='*70}\n")
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "basic":
            test_basic_memory()
        elif test_name == "custom":
            test_custom_data()
        elif test_name == "update":
            test_data_update()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: basic, custom, update")
    else:
        # Run all tests
        test_basic_memory()
        test_custom_data()
        test_data_update()
        
        print(f"\n{'='*70}")
        print("🎉 All tests complete!")
        print(f"{'='*70}\n")
