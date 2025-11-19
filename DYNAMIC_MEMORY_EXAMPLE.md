# Dynamic Data in Memory - Simple Guide

Your agent now stores **custom data directly in the checkpoint body**! This means your custom data persists across conversation turns.

## 🎯 What This Means

### Before: Only Messages
```json
{
  "channel_values": {
    "messages": [...]  // Only conversation history
  }
}
```

### After: Messages + Your Custom Data
```json
{
  "channel_values": {
    "messages": [...],
    "user_preferences": {...},  // ✅ Your data persists!
    "custom_data": {...}         // ✅ Any custom fields!
  }
}
```

## 📦 Available Custom Fields

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `user_preferences` | dict | User preferences and settings | `{"language": "en", "theme": "dark"}` |
| `custom_data` | dict | Any custom application data | `{"cart_id": "123", "session_start": "..."}` |

## 🚀 Usage Examples

### Example 1: User Preferences

**Turn 1: Set preferences**
```bash
agentcore invoke '{
  "prompt": "Hi! My name is Alice.",
  "session_id": "user-123",
  "preferences": {
    "language": "en",
    "temperature_unit": "celsius"
  }
}'
```

**Turn 2: Preferences are remembered**
```bash
agentcore invoke '{
  "prompt": "What's my preferred temperature unit?",
  "session_id": "user-123"
}'
# Agent responds: "celsius" (from stored preferences)
```

### Example 2: Custom Application Data

**Turn 1: Store custom data**
```bash
agentcore invoke '{
  "prompt": "I want to order a pizza",
  "session_id": "order-456",
  "preferences": {
    "favorite_topping": "pepperoni"
  },
  "custom_data": {
    "cart_id": "cart-789",
    "order_type": "delivery",
    "address": "123 Main St"
  }
}'
```

**Turn 2: Data is available**
```bash
agentcore invoke '{
  "prompt": "Add another pizza to my order",
  "session_id": "order-456"
}'
# Agent knows the cart_id, order_type, and preferences!
```

## 🔍 How It Works

### In Your Agent Code

```python
class CustomAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_preferences: dict      # Persists across turns
    custom_data: dict           # Persists across turns

def chatbot(state: CustomAgentState):
    # Access persisted data
    user_prefs = state.get("user_preferences", {})
    custom = state.get("custom_data", {})
    
    # Use it to customize behavior
    if user_prefs:
        # Include preferences in system message
        pass
    
    return {"messages": [response]}
```

### What Gets Stored

**Full checkpoint structure:**
```json
{
  "checkpoint_id": "...",
  "channel_values": {
    "messages": [
      {"type": "HumanMessage", "content": "Hi! My name is Alice."},
      {"type": "AIMessage", "content": "Hello Alice!"}
    ],
    "user_preferences": {
      "language": "en",
      "temperature_unit": "celsius"
    },
    "custom_data": {
      "cart_id": "cart-789",
      "order_type": "delivery"
    }
  }
}
```

## ✅ Key Benefits

1. **Persistent Context** - Data survives across conversation turns
2. **Simple API** - Just pass `preferences` or `custom_data` in payload
3. **Automatic Merging** - New data merges with existing state
4. **Type Safe** - TypedDict ensures correct structure
5. **No Overwriting** - Fields only update when explicitly provided

## 🚀 Quick Start

```bash
# Turn 1: Set data
agentcore invoke '{
  "prompt": "Hello",
  "session_id": "test-session",
  "preferences": {"theme": "dark", "lang": "en"}
}'

# Turn 2: Data is remembered (no need to resend!)
agentcore invoke '{
  "prompt": "What are my settings?",
  "session_id": "test-session"
}'
```

## 💡 Best Practices

1. **Use session_id** - Same session_id = same memory
2. **Only send what changes** - Don't resend unchanged data
3. **Keep data small** - Checkpoint size limit is 256KB
4. **Use meaningful keys** - Makes debugging easier
5. **Don't store secrets** - Memory is not encrypted

## 🎉 That's It!

Your agent now has persistent custom data storage. Just add `preferences` or `custom_data` to your payload, and it'll be available in all future turns of the same session!
