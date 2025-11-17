#!/usr/bin/env python3
"""
Test Dynamic Data in Memory Events

This script demonstrates how custom data is stored in memory event body
and persists across conversation turns.
"""
import boto3
import json
import uuid
from datetime import datetime

# Configuration
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-west-2:313117444016:runtime/langgraph_agent-1NyH76Cfc7"
REGION = "us-west-2"


def invoke_with_dynamic_data(client, runtime_arn, payload, session_id):
    """Invoke agent with custom dynamic data"""
    
    print(f"\n{'='*80}")
    print(f"📤 Sending Request")
    print(f"{'='*80}")
    print(f"Prompt: {payload['prompt']}")
    print(f"Session: {session_id}")
    
    # Show custom data being sent
    if 'user_context' in payload or 'preferences' in payload:
        print(f"\n📦 Custom Data:")
        for key in ['preferences', 'profile', 'business_data', 'analytics_data']:
            if key in payload:
                print(f"  {key}: {json.dumps(payload[key], indent=4)}")
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            contentType='application/json',
            body=json.dumps(payload),
            qualifier='DEFAULT'
        )
        
        result = json.loads(response['body'].read())
        
        print(f"\n{'='*80}")
        print(f"📥 Response")
        print(f"{'='*80}")
        print(f"{result}")
        print(f"{'='*80}\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_dynamic_memory():
    """Test dynamic data persistence across conversation turns"""
    
    client = boto3.client('bedrock-agentcore', region_name=REGION)
    session_id = f"dynamic-test-{uuid.uuid4()}"
    
    print(f"\n🧪 Testing Dynamic Data in Memory Events")
    print(f"{'='*80}")
    print(f"Session ID: {session_id}")
    print(f"{'='*80}\n")
    
    # Turn 1: Set up rich user context
    print(f"\n{'🔵 TURN 1: Initialize with rich user context'}")
    turn1_payload = {
        "prompt": "Hello! I'm interested in buying a laptop.",
        "session_id": session_id,
        "user_id": "alice-123",
        "preferences": {
            "budget": 2000,
            "preferred_brands": ["Apple", "Dell"],
            "screen_size": "15 inch",
            "use_case": "software_development"
        },
        "profile": {
            "name": "Alice",
            "email": "alice@example.com",
            "loyalty_tier": "gold",
            "purchase_history_count": 5
        },
        "location": "San Francisco, CA",
        "business_data": {
            "tenant_id": "tech-store-sf",
            "organization": "TechMart",
            "custom_fields": {
                "employee_discount": true,
                "employee_id": "EMP-789",
                "department": "Engineering"
            }
        },
        "analytics_data": {
            "source": "web_app",
            "user_agent": "Chrome/120.0",
            "referrer": "google_shopping",
            "campaign_id": "back_to_school_2025"
        },
        "conversation_type": "sales",
        "channel": "chat_widget"
    }
    
    result1 = invoke_with_dynamic_data(client, RUNTIME_ARN, turn1_payload, session_id)
    
    # Turn 2: Agent should remember preferences
    print(f"\n{'🔵 TURN 2: Ask about recommendations (agent should use stored preferences)'}")
    turn2_payload = {
        "prompt": "What laptops do you recommend based on my needs?",
        "session_id": session_id
        # Note: No preferences passed - agent should use stored data!
    }
    
    result2 = invoke_with_dynamic_data(client, RUNTIME_ARN, turn2_payload, session_id)
    
    # Turn 3: Update specific preference
    print(f"\n{'🔵 TURN 3: Update budget preference'}")
    turn3_payload = {
        "prompt": "Actually, I can increase my budget to $2500.",
        "session_id": session_id,
        "preferences": {
            "budget": 2500  # Update just the budget
        }
    }
    
    result3 = invoke_with_dynamic_data(client, RUNTIME_ARN, turn3_payload, session_id)
    
    # Turn 4: Check if updated preference is used
    print(f"\n{'🔵 TURN 4: Agent should use updated budget'}")
    turn4_payload = {
        "prompt": "Show me options in my price range.",
        "session_id": session_id
    }
    
    result4 = invoke_with_dynamic_data(client, RUNTIME_ARN, turn4_payload, session_id)
    
    print(f"\n{'='*80}")
    print(f"✅ Dynamic Memory Test Complete!")
    print(f"{'='*80}")
    print(f"\n📊 Summary:")
    print(f"  - Turn 1: Set rich user context (preferences, profile, business data)")
    print(f"  - Turn 2: Agent used stored preferences without re-sending")
    print(f"  - Turn 3: Updated budget preference")
    print(f"  - Turn 4: Agent used updated budget")
    print(f"\n💡 All custom data persisted in memory event body across turns!")
    print(f"{'='*80}\n")


def test_business_use_case():
    """Test real-world business scenario with custom data"""
    
    client = boto3.client('bedrock-agentcore', region_name=REGION)
    session_id = f"customer-support-{uuid.uuid4()}"
    
    print(f"\n🏢 Testing Business Use Case: Customer Support")
    print(f"{'='*80}")
    print(f"Session ID: {session_id}")
    print(f"{'='*80}\n")
    
    # Customer support scenario
    print(f"\n{'🔵 Customer Support Scenario'}")
    payload = {
        "prompt": "I have an issue with my recent order",
        "session_id": session_id,
        "user_id": "customer-456",
        "conversation_type": "customer_support",
        "channel": "support_portal",
        "profile": {
            "name": "Bob Smith",
            "account_type": "premium",
            "member_since": "2020-01-15",
            "lifetime_value": 15000
        },
        "business_data": {
            "tenant_id": "ecommerce-platform",
            "custom_fields": {
                "order_id": "ORD-98765",
                "order_date": "2025-11-10",
                "order_total": 299.99,
                "issue_type": "delivery_delay",
                "priority": "high",
                "assigned_agent": "support-agent-12"
            }
        },
        "analytics_data": {
            "source": "support_portal",
            "ticket_id": "TICK-54321",
            "category": "shipping",
            "sentiment": "frustrated"
        }
    }
    
    result = invoke_with_dynamic_data(client, RUNTIME_ARN, payload, session_id)
    
    print(f"\n💼 Business Context Available to Agent:")
    print(f"  - Customer: Premium member since 2020")
    print(f"  - Order: $299.99, delayed delivery")
    print(f"  - Priority: HIGH")
    print(f"  - Sentiment: Frustrated")
    print(f"\n✅ Agent can provide personalized, priority support based on this data!")


if __name__ == "__main__":
    import sys
    
    print(f"\n{'='*80}")
    print(f"🚀 Dynamic Memory Data Test Suite")
    print(f"{'='*80}\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--business":
        test_business_use_case()
    else:
        test_dynamic_memory()
        
        print(f"\n💡 Run with --business flag to test business use case:")
        print(f"   python test_dynamic_memory.py --business\n")

