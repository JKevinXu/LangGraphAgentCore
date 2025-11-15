#!/usr/bin/env python3
"""
Test script for LangGraphAgentCore on AWS Bedrock Agent Core Runtime.

Usage:
    python test_runtime.py <runtime-arn>
    python test_runtime.py <runtime-arn> --prompt "Calculate 50 * 8"
"""

import boto3
import json
import argparse
import sys
import uuid
from datetime import datetime


def test_agent(runtime_arn: str, prompt: str, session_id: str = None):
    """Test the deployed LangGraph agent."""
    
    client = boto3.client('bedrock-agentcore', region_name='us-west-2')
    
    if not session_id:
        session_id = f"test-{uuid.uuid4()}"  # Generate UUID for proper length (minimum 33 chars)
    
    print("🤖 Testing LangGraphAgentCore")
    print("=" * 60)
    print(f"Runtime ARN: {runtime_arn}")
    print(f"Session ID:  {session_id}")
    print(f"Prompt:      {prompt}")
    print()
    
    try:
        # Prepare payload
        payload = json.dumps({"prompt": prompt})
        
        # Invoke agent
        print("⏳ Invoking agent...")
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier='DEFAULT'
        )
        
        # Parse response
        if 'response' in response:
            response_body = response['response']
            
            # Handle StreamingBody
            if hasattr(response_body, 'read'):
                result = response_body.read().decode('utf-8')
            else:
                result = str(response_body)
            
            print("✅ Agent Response:")
            print("-" * 60)
            print(result)
            print("-" * 60)
            
            return result
        else:
            print("❌ No response received")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_test_suite(runtime_arn: str):
    """Run a suite of test prompts."""
    
    test_cases = [
        {
            "name": "Calculator Test 1",
            "prompt": "What is 15 * 23?",
            "expected": "should call calculator and return 345"
        },
        {
            "name": "Calculator Test 2",
            "prompt": "Calculate sqrt(16) + 5",
            "expected": "should return 9"
        },
        {
            "name": "Weather Test",
            "prompt": "What's the weather in San Francisco?",
            "expected": "should call weather tool"
        },
        {
            "name": "Multi-step Test",
            "prompt": "What is 100 + 50, and then tell me the weather in Tokyo?",
            "expected": "should use both tools"
        },
        {
            "name": "Conversational Test",
            "prompt": "Hello! What can you help me with?",
            "expected": "should describe capabilities"
        }
    ]
    
    print("🧪 Running Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}/{len(test_cases)}: {test['name']}")
        print(f"Expected: {test['expected']}")
        print()
        
        result = test_agent(
            runtime_arn=runtime_arn,
            prompt=test['prompt'],
            session_id=f"test-suite-{i}-{uuid.uuid4()}"
        )
        
        results.append({
            "test": test['name'],
            "success": result is not None,
            "response": result
        })
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {result['test']}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


def main():
    parser = argparse.ArgumentParser(
        description="Test LangGraphAgentCore on AWS Bedrock Agent Core Runtime"
    )
    parser.add_argument(
        'runtime_arn',
        help='ARN of the AgentCore Runtime (e.g., arn:aws:bedrock-agentcore:us-west-2:...)'
    )
    parser.add_argument(
        '--prompt',
        default=None,
        help='Custom prompt to test (if not provided, runs full test suite)'
    )
    parser.add_argument(
        '--session-id',
        help='Session ID for conversation continuity'
    )
    parser.add_argument(
        '--test-suite',
        action='store_true',
        help='Run full test suite'
    )
    
    args = parser.parse_args()
    
    # Validate runtime ARN format
    if not args.runtime_arn.startswith('arn:aws:bedrock-agentcore:'):
        print("❌ Invalid Runtime ARN format")
        print("Expected format: arn:aws:bedrock-agentcore:REGION:ACCOUNT:agent-runtime/ID")
        sys.exit(1)
    
    if args.test_suite or not args.prompt:
        # Run test suite
        success = run_test_suite(args.runtime_arn)
        sys.exit(0 if success else 1)
    else:
        # Single prompt test
        result = test_agent(
            runtime_arn=args.runtime_arn,
            prompt=args.prompt,
            session_id=args.session_id
        )
        sys.exit(0 if result else 1)


if __name__ == '__main__':
    main()

