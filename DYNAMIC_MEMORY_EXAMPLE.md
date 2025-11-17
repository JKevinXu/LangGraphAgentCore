# Dynamic Data in Memory Event Body - Complete Guide

Your agent now stores **custom dynamic data directly in the checkpoint body**! This means all your custom data persists across conversation turns and is available in the next invocation.

## 🎯 What's Different?

### Before: Only Metadata
```json
{
  "metadata": {"user_preferences": "..."},  // Separate from state
  "messages": [...]
}
```

### After: Data in Checkpoint Body
```json
{
  "channel_values": {
    "messages": [...],
    "user_context": {...},           // ✅ Your data here!
    "business_data": {...},          // ✅ Persisted!
    "analytics_data": {...},         // ✅ Available next turn!
    "conversation_metadata": {...}   // ✅ Part of state!
  }
}
```

## 📦 Available Fields in Memory Body

Your checkpoint now stores these custom fields:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `user_context` | dict | User profile, preferences, location | `{"user_id": "123", "preferences": {...}}` |
| `conversation_metadata` | dict | Conversation-level data | `{"type": "support", "language": "en"}` |
| `business_data` | dict | Custom business logic | `{"tenant_id": "acme", "subscription": "pro"}` |
| `analytics_data` | dict | Tracking and metrics | `{"source": "mobile", "campaign": "summer"}` |
| `session_summary` | str | Rolling conversation summary | `"User asking about pricing"` |
| `last_updated` | str | ISO timestamp | `"2025-11-17T15:30:00"` |

## 🚀 Usage Examples

### Example 1: Basic Usage with User Preferences

```bash
agentcore invoke '{
  "prompt": "What is the weather?",
  "session_id": "user-123-session",
  "user_id": "user-123",
  "preferences": {
    "temperature_unit": "celsius",
    "language": "en",
    "notification_enabled": true
  },
  "location": "San Francisco"
}'
```

**What gets stored:**
```json
{
  "channel_values": {
    "messages": [...],
    "user_context": {
      "user_id": "user-123",
      "preferences": {
        "temperature_unit": "celsius",
        "language": "en",
        "notification_enabled": true
      },
      "profile": {},
      "location": "San Francisco"
    },
    "last_updated": "2025-11-17T15:30:00"
  }
}
```

**Next turn - preferences are remembered:**
```bash
agentcore invoke '{
  "prompt": "Show me the forecast",
  "session_id": "user-123-session"
}'
# Agent automatically uses celsius (from user_context.preferences)
```

### Example 2: E-commerce with Business Data

```bash
agentcore invoke '{
  "prompt": "I want to buy a laptop",
  "session_id": "shopping-cart-456",
  "user_id": "customer-789",
  "preferences": {
    "budget": 1500,
    "preferred_brands": ["Apple", "Dell"]
  },
  "profile": {
    "name": "Alice",
    "loyalty_tier": "gold",
    "points": 5000
  },
  "business_data": {
    "tenant_id": "retail-store-1",
    "organization": "TechMart",
    "custom_fields": {
      "cart_id": "cart-123",
      "promo_code": "SUMMER25",
      "referral_source": "email_campaign"
    }
  }
}'
```

**Checkpoint stores:**
```json
{
  "user_context": {
    "user_id": "customer-789",
    "preferences": {"budget": 1500, "preferred_brands": ["Apple", "Dell"]},
    "profile": {"name": "Alice", "loyalty_tier": "gold", "points": 5000},
    "location": "unknown"
  },
  "business_data": {
    "tenant_id": "retail-store-1",
    "organization": "TechMart",
    "custom_fields": {
      "cart_id": "cart-123",
      "promo_code": "SUMMER25",
      "referral_source": "email_campaign"
    }
  }
}
```

**Agent behavior changes based on data:**
- Uses `budget` to filter recommendations
- Applies `promo_code` if eligible
- Mentions `loyalty_tier` benefits
- All data persists for multi-turn shopping experience

### Example 3: Customer Support with Analytics

```bash
agentcore invoke '{
  "prompt": "I have an issue with my order",
  "session_id": "support-ticket-789",
  "user_id": "customer-456",
  "conversation_type": "customer_support",
  "channel": "chat_widget",
  "profile": {
    "account_type": "premium",
    "order_history_count": 15
  },
  "business_data": {
    "tenant_id": "company-xyz",
    "custom_fields": {
      "order_id": "ORD-12345",
      "issue_type": "delivery_delay",
      "priority": "high"
    }
  },
  "analytics_data": {
    "request_source": "web_app",
    "user_agent": "Chrome/120.0",
    "referrer": "order_tracking_page",
    "campaign_id": "customer_retention_q4"
  }
}'
```

**Agent can:**
- See it's a `customer_support` conversation
- Know user is `premium` (provide better service)
- Reference `order_id` from business_data
- Track metrics via `analytics_data`

### Example 4: Multi-Step Task with Session Summary

```bash
# Turn 1: Initial request
agentcore invoke '{
  "prompt": "I need to plan a vacation",
  "session_id": "vacation-planning-001",
  "user_id": "traveler-123",
  "preferences": {
    "budget": 3000,
    "travel_dates": "2025-12-15 to 2025-12-22",
    "interests": ["beach", "culture", "food"]
  },
  "session_summary": ""
}'

# Turn 2: Follow-up (summary auto-updated)
agentcore invoke '{
  "prompt": "What about hotels?",
  "session_id": "vacation-planning-001",
  "session_summary": "User planning vacation to Paris, budget $3000, dates Dec 15-22"
}'

# Turn 3: More context added
agentcore invoke '{
  "prompt": "Book the Marriott",
  "session_id": "vacation-planning-001",
  "session_summary": "User planning Paris trip. Looking at hotels. Interested in Marriott."
}'
```

**State evolution:**
```json
// Turn 1
{
  "conversation_metadata": {
    "message_count": 1,
    "last_interaction": "2025-11-17T15:30:00"
  },
  "session_summary": "User planning vacation"
}

// Turn 2
{
  "conversation_metadata": {
    "message_count": 3,
    "last_interaction": "2025-11-17T15:32:00"
  },
  "session_summary": "User planning vacation to Paris, discussing hotels"
}

// Turn 3
{
  "conversation_metadata": {
    "message_count": 5,
    "last_interaction": "2025-11-17T15:35:00"
  },
  "analytics_data": {
    "total_turns": 3
  },
  "session_summary": "User planning Paris trip. Looking at hotels. Booking Marriott."
}
```

## 🎨 Advanced Use Cases

### Use Case 1: A/B Testing

```bash
agentcore invoke '{
  "prompt": "Show me products",
  "session_id": "user-session",
  "analytics_data": {
    "experiment_id": "pricing_test_v2",
    "variant": "B",
    "cohort": "new_users"
  }
}'
```

Agent can adjust behavior based on `variant` and track results.

### Use Case 2: Multi-Tenant SaaS

```bash
agentcore invoke '{
  "prompt": "Create a report",
  "session_id": "workspace-session",
  "business_data": {
    "tenant_id": "company-abc",
    "organization": "ACME Corp",
    "custom_fields": {
      "workspace_id": "ws-789",
      "role": "admin",
      "permissions": ["read", "write", "delete"]
    }
  }
}'
```

Agent respects tenant isolation and permission levels.

### Use Case 3: Personalized Learning

```bash
agentcore invoke '{
  "prompt": "Teach me Python",
  "session_id": "learning-path-123",
  "user_context": {
    "profile": {
      "skill_level": "beginner",
      "learning_style": "visual",
      "completed_lessons": ["intro", "variables"]
    },
    "preferences": {
      "pace": "slow",
      "examples": "practical"
    }
  },
  "session_summary": "Student learning Python basics. Completed intro and variables."
}'
```

Agent adapts teaching style based on learner profile.

## 🔍 Accessing Data in Your Agent

The chatbot function can access all custom data:

```python
def chatbot(state: CustomAgentState):
    # Access custom data
    user_context = state.get("user_context", {})
    business_data = state.get("business_data", {})
    analytics_data = state.get("analytics_data", {})
    
    # Use it to customize behavior
    if user_context.get("preferences", {}).get("temperature_unit") == "celsius":
        # Use celsius in weather responses
        pass
    
    if business_data.get("custom_fields", {}).get("priority") == "high":
        # Provide priority service
        pass
    
    # Update data for next turn
    return {
        "messages": [response],
        "analytics_data": {
            **analytics_data,
            "total_turns": analytics_data.get("total_turns", 0) + 1
        }
    }
```

## 📊 What Gets Stored in Checkpoint

**Full checkpoint structure:**
```json
{
  "checkpoint_id": "checkpoint-uuid",
  "channel_values": {
    "messages": [
      {"type": "HumanMessage", "content": "..."},
      {"type": "AIMessage", "content": "..."}
    ],
    "user_context": {
      "user_id": "user-123",
      "preferences": {"temperature_unit": "celsius"},
      "profile": {"name": "Alice", "tier": "gold"},
      "location": "San Francisco"
    },
    "conversation_metadata": {
      "session_start": "2025-11-17T15:00:00",
      "conversation_type": "general",
      "channel": "api",
      "language": "en",
      "last_interaction": "2025-11-17T15:30:00",
      "message_count": 5
    },
    "business_data": {
      "tenant_id": "company-abc",
      "organization": "ACME Corp",
      "custom_fields": {"cart_id": "cart-123"}
    },
    "analytics_data": {
      "request_source": "mobile_app",
      "user_agent": "iOS/16.0",
      "referrer": "home_screen",
      "campaign_id": "summer_2025",
      "total_turns": 3,
      "last_model_used": "claude-3-5-sonnet"
    },
    "session_summary": "User shopping for laptops, discussed MacBook Pro",
    "last_updated": "2025-11-17T15:30:00"
  },
  "channel_versions": {...},
  "pending_writes": []
}
```

## ✅ Benefits

1. **Rich Context** - Agent has full user context every turn
2. **Business Logic** - Store tenant, org, custom business data
3. **Analytics** - Track user journey and behavior
4. **Personalization** - Adapt to user preferences automatically
5. **State Management** - Complex multi-turn workflows
6. **Debugging** - Full visibility into conversation state
7. **Compliance** - Track data lineage and consent

## 🚀 Deploy & Test

```bash
# Deploy updated agent
cd /Users/kx/ws/LangGraphAgentCore/bedrock
source ../.venv/bin/activate
agentcore launch

# Test with custom data
agentcore invoke '{
  "prompt": "Hello",
  "session_id": "test-session",
  "user_id": "alice",
  "preferences": {"theme": "dark", "language": "en"},
  "profile": {"name": "Alice", "role": "admin"},
  "business_data": {"tenant_id": "acme"},
  "analytics_data": {"source": "web"}
}'

# Check next turn - data is remembered!
agentcore invoke '{
  "prompt": "What are my preferences?",
  "session_id": "test-session"
}'
```

## 💡 Best Practices

1. **Start Simple** - Begin with `user_context`, add more as needed
2. **Keep Data Structured** - Use consistent schemas
3. **Update Incrementally** - Only update fields that changed
4. **Size Limits** - Keep total checkpoint under 256KB
5. **Privacy** - Don't store sensitive data (PII, passwords)
6. **Schema Evolution** - Plan for data structure changes

## 🎉 Summary

Your agent now stores **everything** in the memory event body:
- ✅ User context and preferences
- ✅ Business and organizational data  
- ✅ Analytics and tracking info
- ✅ Conversation metadata
- ✅ Session summaries

**All data persists across turns and is available in the next invocation!**

This enables truly stateful, context-aware AI agents that remember not just conversations, but your entire business context. 🚀

