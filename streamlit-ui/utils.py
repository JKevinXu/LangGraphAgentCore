"""
Utility functions for formatting tool events in the Streamlit UI.
"""

import json
from typing import Dict, Any, Tuple


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_tool_start(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Format a tool_start event for display.
    
    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        
    Returns:
        HTML string for display
    """
    if tool_name == "execute_code" and "code" in args:
        code = args["code"]
        # Escape HTML and replace # with unicode to prevent markdown heading interpretation
        code_escaped = escape_html(code).replace("#", "&#35;")
        return f'''<div class="tool-call">
            🔧 <b>Executing Python code:</b>
            <pre style="background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:6px;font-family:'SF Mono',Monaco,'Cascadia Code',Consolas,monospace;font-size:13px;line-height:1.4;overflow-x:auto;margin-top:8px;white-space:pre-wrap;word-wrap:break-word;font-weight:normal;">{code_escaped}</pre>
        </div>'''
    
    elif tool_name == "browse_web" and "task" in args:
        task = escape_html(args["task"])
        return f'''<div class="tool-call">
            🌐 <b>Browsing web:</b>
            <div style="background:#e3f2fd;padding:10px;border-radius:6px;margin-top:6px;font-size:13px;">{task}</div>
        </div>'''
    
    else:
        args_str = json.dumps(args, indent=2) if args else "{}"
        args_escaped = escape_html(args_str)
        return f'''<div class="tool-call">
            🔧 Calling <b>{tool_name}</b>
            <pre style="background:#f5f5f5;padding:10px;border-radius:6px;font-family:'SF Mono',Monaco,Consolas,monospace;font-size:12px;margin-top:6px;">{args_escaped}</pre>
        </div>'''


def parse_code_result(result: str) -> Tuple[str, str]:
    """
    Parse code execution result to extract output and execution time.
    
    Args:
        result: Raw result string from code interpreter
        
    Returns:
        Tuple of (output_html, execution_time)
    """
    # Clean up escape characters
    result = result.replace("\\n", "\n").replace('\\"', '"')
    
    output_lines = []
    exec_time = ""
    
    lines = result.split("\n")
    in_output = False
    
    for line in lines:
        if "📤 Output:" in line or "Output:" in line:
            in_output = True
            # Get the rest of the line after "Output:"
            after_output = line.split("Output:")[-1].strip()
            if after_output:
                output_lines.append(after_output)
        elif "✅ Executed" in line:
            exec_time = line.replace("✅ ", "").strip()
            in_output = False
        elif in_output and line.strip():
            output_lines.append(line)
    
    output_html = "<br>".join(escape_html(line) for line in output_lines) if output_lines else escape_html(result[:200])
    
    return output_html, exec_time


def format_tool_end(tool_name: str, result: str) -> str:
    """
    Format a tool_end event for display.
    
    Args:
        tool_name: Name of the tool that completed
        result: Result from the tool execution
        
    Returns:
        HTML string for display
    """
    # Clean up result
    result = str(result).replace("\\n", "\n").replace('\\"', '"')
    
    if tool_name == "execute_code":
        output_html, exec_time = parse_code_result(result)
        exec_time_html = f'<div style="color:#2e7d32;font-size:11px;margin-top:6px;">✅ {exec_time}</div>' if exec_time else ""
        return f'''<div class="tool-result">
            ✅ <b>Code Output:</b>
            <pre style="background:#e8f5e9;padding:12px;border-radius:6px;margin-top:8px;font-family:'SF Mono',Monaco,'Cascadia Code',Consolas,monospace;font-size:13px;line-height:1.5;white-space:pre-wrap;border-left:3px solid #4caf50;">{output_html}</pre>
            {exec_time_html}
        </div>'''
    
    elif tool_name == "browse_web":
        # Truncate long browser results
        display = result[:300] + "..." if len(result) > 300 else result
        display = escape_html(display)
        return f'''<div class="tool-result">
            🌐 <b>Browser Result:</b>
            <div style="background:#fff3e0;padding:10px;border-radius:6px;margin-top:6px;font-size:13px;border-left:3px solid #ff9800;">{display}</div>
        </div>'''
    
    else:
        display = result[:200] + "..." if len(result) > 200 else result
        display = escape_html(display)
        return f'''<div class="tool-result">
            ✅ <b>{tool_name}</b> → 
            <code style="font-family:'SF Mono',Monaco,Consolas,monospace;font-size:12px;background:#f5f5f5;padding:2px 6px;border-radius:3px;">{display}</code>
        </div>'''


def format_tool_events_container(events_html: list) -> str:
    """
    Wrap tool events in a container.
    
    Args:
        events_html: List of HTML strings for each event
        
    Returns:
        HTML string with all events in a container
    """
    return f'<div class="tool-events-container">{"".join(events_html)}</div>'

