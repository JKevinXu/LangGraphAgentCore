# LangGraph Agent Chat UI

Streamlit-based chat interface for the LangGraphAgentCore BFF.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the UI (connects to local BFF)
streamlit run app.py

# Or connect to deployed BFF
streamlit run app.py -- --server.port 8501
```

## Configuration

The UI can be configured via the sidebar:

| Setting | Description | Default |
|---------|-------------|---------|
| BFF Endpoint | URL of the BFF API | `http://localhost:8000` |
| Session ID | Unique session identifier | Auto-generated |
| Enable Streaming | Use SSE streaming | `true` |

## Features

- 💬 **Chat Interface** - Modern chat bubbles with user/assistant messages
- ⚡ **Streaming** - Real-time response streaming via SSE
- 🔗 **Session Management** - Persistent conversation sessions
- 🎨 **Dark/Light Theme** - Follows Streamlit theme settings
- 🔧 **Connection Test** - Verify BFF connectivity

## Usage

### Local Development

1. Start the BFF locally:
   ```bash
   cd ../
   uvicorn app.main:app --reload --port 8000
   ```

2. Start the UI:
   ```bash
   streamlit run app.py
   ```

3. Open http://localhost:8501

### Connect to Deployed BFF

1. Start the UI:
   ```bash
   streamlit run app.py
   ```

2. In the sidebar, update the BFF Endpoint:
   ```
   http://LangGr-BffSe-aO1aJ7AQgiMd-1474248023.us-west-2.elb.amazonaws.com
   ```

3. Click "Test Connection" to verify

## Screenshots

```
┌─────────────────────────────────────────────┐
│  🤖 LangGraph Agent                         │
│  Chat with your AI agent powered by Bedrock │
├─────────────────────────────────────────────┤
│  👤 User: What is 5 + 5?                    │
│                                             │
│  🤖 Assistant: The result of 5 + 5 is 10.   │
│                                             │
│  👤 User: Explain quantum computing         │
│                                             │
│  🤖 Assistant: Quantum computing is...      │
├─────────────────────────────────────────────┤
│  [Type your message...              ] [Send]│
└─────────────────────────────────────────────┘
```

## Environment Variables

```bash
# Optional: Set default BFF URL
export BFF_URL=http://localhost:8000
```

## Troubleshooting

### Connection Failed
- Ensure BFF is running
- Check the endpoint URL
- Verify network connectivity

### Session ID Too Short
- Session ID must be at least 33 characters
- Use the auto-generated ID or enter a longer one

### Streaming Not Working
- Toggle "Enable Streaming" off for blocking mode
- Check BFF logs for errors

