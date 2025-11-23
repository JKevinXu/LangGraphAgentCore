"""
AgentCore Browser Example - Following AWS Official Guide

This example demonstrates how to use the AgentCore Browser tool with LangGraph agents.
Based on: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-onboarding.html

Prerequisites:
1. AWS account with credentials configured
2. Python 3.10+ installed
3. IAM execution role with required permissions (see documentation)
4. Model access: Anthropic Claude Sonnet 4.0 enabled in Bedrock console
5. Region where Amazon Bedrock AgentCore is available

Setup:
    pip install -r requirements.txt
    playwright install chromium  # Install browser binaries
    
Usage:
    python browser_agent_example.py
"""

import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph.graph import StateGraph, MessagesState, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from browser_tool import get_browser_tool

# Configuration
REGION = os.environ.get("AWS_REGION", "us-west-2")


def create_browser_agent():
    """Create a LangGraph agent with AgentCore Browser capabilities."""
    
    # Initialize Bedrock LLM
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        model_kwargs={"temperature": 0.7}
    )
    
    # Get browser tool
    browser_tool = get_browser_tool()
    
    if not browser_tool:
        print("❌ Error: Browser tool could not be initialized.")
        print("   Please check:")
        print("   - Your AWS credentials are configured")
        print("   - IAM permissions are correct")
        print("   - AgentCore Browser is available in your region")
        return None
    
    # Bind tools to the LLM
    tools = [browser_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # System message
    system_message = """You are a helpful AI assistant with web browsing capabilities.
You can navigate websites, search for information, extract content, and interact with web elements.

When browsing:
- Navigate to the provided URL
- Extract the requested information accurately
- Summarize findings clearly
- Cite sources when possible"""
    
    # Define the chatbot node
    def chatbot(state: MessagesState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Create the graph
    graph_builder = StateGraph(MessagesState)
    
    # Add nodes
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))
    
    # Add edges
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")
    
    # Set entry point
    graph_builder.set_entry_point("chatbot")
    
    # Compile and return
    return graph_builder.compile()


def main():
    """Run example queries with the browser agent."""
    
    print("=" * 80)
    print("AgentCore Browser Example")
    print("=" * 80)
    print()
    
    # Create the agent
    print("🔧 Creating browser agent...")
    agent = create_browser_agent()
    
    if not agent:
        print("\n❌ Failed to create agent. Exiting.")
        return
    
    print("✅ Agent created successfully!")
    print()
    
    # Example 1: Browse AWS documentation
    print("-" * 80)
    print("Example 1: Browsing AWS Documentation")
    print("-" * 80)
    
    prompt1 = """What are the services offered by Bedrock AgentCore? 
Use this documentation link: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html"""
    
    print(f"\n📝 Prompt: {prompt1}\n")
    print("🌐 Agent is browsing the web...\n")
    
    try:
        response1 = agent.invoke({"messages": [HumanMessage(content=prompt1)]})
        print("🤖 Agent Response:")
        print(response1["messages"][-1].content)
        print()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
    
    # Example 2: Web search and information extraction
    print("-" * 80)
    print("Example 2: Information Extraction")
    print("-" * 80)
    
    prompt2 = """Navigate to https://aws.amazon.com/bedrock/ and tell me about 
the key features of Amazon Bedrock."""
    
    print(f"\n📝 Prompt: {prompt2}\n")
    print("🌐 Agent is browsing the web...\n")
    
    try:
        response2 = agent.invoke({"messages": [HumanMessage(content=prompt2)]})
        print("🤖 Agent Response:")
        print(response2["messages"][-1].content)
        print()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
    
    print("=" * 80)
    print("✅ Examples completed!")
    print()
    print("💡 Next Steps:")
    print("   - View live browser sessions in AWS Console")
    print("   - Check browser logs in CloudWatch")
    print("   - Review session recordings in S3")
    print("=" * 80)


if __name__ == "__main__":
    main()

