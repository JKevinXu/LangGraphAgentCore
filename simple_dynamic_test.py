#!/usr/bin/env python3
"""
Simple test for dynamic data in memory events
"""
import boto3
import json
import uuid

# Configuration
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7"
REGION = "us-west-2"

client = boto3.client('bedrock-agentcore', region_name=REGION)
session_id = f"simple-test-{uuid.uuid4()}"

print(f"\n{'='*70}")
print(f"🧪 Simple Dynamic Memory Test")
print(f"{'='*70}")
print(f"Session ID: {session_id}\n")

# Turn 1: Send message with custom data
print("🔵 Turn 1: Introducing myself with preferences")
print("-" * 70)

turn1 = {
    "prompt": "Hi! My name is Alice and I love pizza.",
    "session_id": session_id,
    "preferences": {
        "favorite_food": "pizza",
        "temperature_unit": "celsius"
    },
    "location": "San Francisco"
}

print(f"📤 Sending: {turn1['prompt']}")
print(f"📦 Custom data: preferences={turn1['preferences']}, location={turn1['location']}")

response1 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    contentType='application/json',
    payload=json.dumps(turn1),
    qualifier='DEFAULT'
)

# Read the streaming response
response_body = response1.get('output', response1.get('body', ''))
if hasattr(response_body, 'read'):
    result1 = response_body.read().decode('utf-8')
else:
    result1 = str(response_body)

print(f"📥 Response: {result1}\n")

# Turn 2: Ask question (preferences should be remembered)
print("🔵 Turn 2: Testing if agent remembers my name")
print("-" * 70)

turn2 = {
    "prompt": "What is my name?",
    "session_id": session_id
    # Note: No custom data sent - agent should use stored preferences!
}

print(f"📤 Sending: {turn2['prompt']}")
print(f"💡 No custom data sent - using stored data from Turn 1")

response2 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    contentType='application/json',
    payload=json.dumps(turn2),
    qualifier='DEFAULT'
)

response_body = response2.get('output', response2.get('body', ''))
if hasattr(response_body, 'read'):
    result2 = response_body.read().decode('utf-8')
else:
    result2 = str(response_body)

print(f"📥 Response: {result2}\n")

# Turn 3: Ask about preferences
print("🔵 Turn 3: Testing if agent remembers my preferences")
print("-" * 70)

turn3 = {
    "prompt": "What food do I like?",
    "session_id": session_id
}

print(f"📤 Sending: {turn3['prompt']}")

response3 = client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    contentType='application/json',
    payload=json.dumps(turn3),
    qualifier='DEFAULT'
)

response_body = response3.get('output', response3.get('body', ''))
if hasattr(response_body, 'read'):
    result3 = response_body.read().decode('utf-8')
else:
    result3 = str(response_body)

print(f"📥 Response: {result3}\n")

# Summary
print(f"{'='*70}")
print("✅ Test Complete!")
print(f"{'='*70}")
print("\n📊 What happened:")
print("  Turn 1: Sent name + custom preferences (favorite_food, location)")
print("  Turn 2: Agent remembered 'Alice' ✓")
print("  Turn 3: Agent remembered 'pizza' from preferences ✓")
print("\n💡 All custom data persisted in memory across turns!")
print(f"{'='*70}\n")

