# AgentCore Browser Tool Integration Plan

**Status**: Ready for Implementation  
**Timeline**: 4 days  
**Last Updated**: November 20, 2025

---

## Current State

**Existing:**
- ✅ `bedrock/browser_tool.py` - Browser tool wrapper (ready to use)
- ✅ `bedrock/browser_agent_example.py` - Standalone example
- ❌ Not integrated into `bedrock/agent_runtime.py` (main runtime)
- ❌ Missing dependencies in `requirements.txt`

**Gap:** Browser tool exists but isn't part of the deployed agent runtime.

---

## Implementation Plan

### Phase 1: Dependencies (Day 1)

**1.1 Update `bedrock/requirements.txt`**
```diff
+ # AgentCore Browser Tool
+ strands-tools>=0.1.0
+ playwright>=1.40.0
```

**1.2 Update `bedrock/Dockerfile`**
```diff
  RUN pip install --no-cache-dir -r requirements.txt
  
+ # Install Playwright browser binaries
+ RUN playwright install chromium --with-deps
```

**1.3 IAM Permissions**
Add to `LangGraphAgentCoreRole`:
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:InvokeBrowser",
    "bedrock-agentcore:GetBrowserSession",
    "bedrock-agentcore:CreateBrowserSession",
    "bedrock-agentcore:CloseBrowserSession"
  ],
  "Resource": "*"
}
```

### Phase 2: Runtime Integration (Day 1-2)

**2.1 Update `bedrock/agent_runtime.py`**

Add import:
```python
from browser_tool import get_browser_tool
```

Update `create_agent()` function (~line 109):
```python
# Get browser tool (optional - gracefully degrades if unavailable)
browser_tool = get_browser_tool()

# Bind tools to the LLM
tools = [calculator, get_weather]
if browser_tool:
    tools.append(browser_tool)
    print("✅ Browser tool enabled")
else:
    print("ℹ️  Browser tool not available")

llm_with_tools = llm.bind_tools(tools)
```

Update system message (~line 113):
```python
system_message = """You're a helpful assistant with the following capabilities:
- Perform mathematical calculations
- Check weather information
- Browse websites and extract information (when available)"""
```

### Phase 3: Testing (Day 2-3)

**Quick Test:**
```bash
cd bedrock
pip install -r requirements.txt
playwright install chromium
python agent_runtime.py
```

**Manual Test Cases:**
- [ ] Agent initializes with browser tool
- [ ] Browser tool works with real URL
- [ ] Agent works when browser unavailable (graceful degradation)
- [ ] Docker container builds successfully

### Phase 4: Documentation (Day 3)

**Update `README.md`:**
- Add browser tool to features list
- Add browser usage example
- Link to browser tool guide

**Create `BROWSER_TOOL_GUIDE.md`:**
- Prerequisites and permissions
- Configuration options
- Usage examples
- Troubleshooting

### Phase 5: Deployment (Day 4)

**Deploy:**
```bash
cd bedrock
# Build and deploy
bedrock-agentcore deploy --config .bedrock_agentcore.yaml --wait
```

**Smoke Test:**
```python
payload = {
    "prompt": "What are AWS Bedrock features? Check https://aws.amazon.com/bedrock/"
}
```

---

## Key Features

✅ **Graceful Degradation** - Agent works even if browser unavailable  
✅ **Optional** - Toggle with `BROWSER_ENABLED` env var  
✅ **No Breaking Changes** - Existing functionality preserved  

---

## Rollback Plan

If issues occur:
1. Set `BROWSER_ENABLED=false` (1 min)
2. Deploy previous Docker image (5 min)

---

## Success Criteria

- [ ] Browser tool integrated in agent_runtime.py
- [ ] Dependencies added and working
- [ ] Dockerfile updated with Playwright
- [ ] Local testing passes
- [ ] Deployed to Bedrock AgentCore
- [ ] Documentation updated

---

## Quick Start

```bash
# 1. Add dependencies
cd bedrock
vim requirements.txt  # Add strands-tools and playwright

# 2. Install locally
pip install -r requirements.txt
playwright install chromium

# 3. Update agent_runtime.py
# Add browser tool import and integration (see Phase 2)

# 4. Test
python agent_runtime.py

# 5. Deploy
bedrock-agentcore deploy --config .bedrock_agentcore.yaml
```

---

## References

- [AWS Browser Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-onboarding.html)
- [Strands Tools](https://github.com/aws/strands-tools)
- [Playwright Docs](https://playwright.dev/python/)
