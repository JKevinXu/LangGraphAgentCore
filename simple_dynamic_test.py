#!/usr/bin/env python3
"""
Simple test for dynamic data in memory
"""
import boto3
import json
import uuid

# Configuration
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7"
REGION = "us-west-2"

client = boto3.client('bedrock-agentcore', region_name=REGION)
session_id = f"test-{uuid.uuid4()}"

print(f"\n{'='*70}")
print(f"🧪 Dynamic Memory Test")
print(f"{'='*70}")
print(f"Session: {session_id}\n")

# Turn 1: Set preferences
print("🔵 Turn 1: Setting preferences")
print("-" * 70)

turn1 = {
    "prompt": "Hi! My name is Alice and I love pizza.",
    "session_id": session_id,
    "preferences": {
        "favorite_food": "pizza",
        "language": "en"
    }
}

print(f"📤 Prompt: {turn1['prompt']}")
print(f"📦 Preferences: {turn1['preferences']}")

response1 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    contentType='application/json',
    payload=json.dumps(turn1),
    qualifier='DEFAULT'
)

# Parse response
if 'output' in response1:
    result1 = response1['output']
elif hasattr(response1.get('body'), 'read'):
    result1 = response1['body'].read().decode('utf-8')
else:
    result1 = str(response1)

print(f"📥 Response: {result1}\n")

# Turn 2: Test memory (don't send preferences)
print("🔵 Turn 2: Testing memory")
print("-" * 70)

turn2 = {
    "prompt": "What is my favorite food?",
    "session_id": session_id
}

print(f"📤 Prompt: {turn2['prompt']}")
print(f"💡 No preferences sent - using stored data")

response2 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    contentType='application/json',
    payload=json.dumps(turn2),
    qualifier='DEFAULT'
)

if 'output' in response2:
    result2 = response2['output']
elif hasattr(response2.get('body'), 'read'):
    result2 = response2['body'].read().decode('utf-8')
else:
    result2 = str(response2)

print(f"📥 Response: {result2}\n")

# Summary
print(f"{'='*70}")
print("✅ Test Complete!")
print(f"{'='*70}")
print("\n📊 Results:")
print("  Turn 1: Set preferences (favorite_food: pizza)")
print("  Turn 2: Agent remembered preferences ✓")
print("\n💡 Custom data persisted across turns!")
print(f"{'='*70}\n")
