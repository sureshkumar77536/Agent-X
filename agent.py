#!/usr/bin/env python3
"""
  ────────────────────────────────────────────────────────
    ⚡ AGENT-X :: S-CLASS INFINITE LOOP EDITION ⚡
    True Autonomy | Smart Fallback Parser | Pro UI
  ────────────────────────────────────────────────────────
"""
import json
import subprocess
import sys
import time
import re
import uuid
from typing import List, Dict

def _install_deps():
    print("Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rich", "requests", "cloudscraper", "--break-system-packages"], capture_output=True)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.status import Status
    from rich.prompt import Prompt
    from rich.syntax import Syntax
    from rich.theme import Theme
    import requests
    import cloudscraper
except ImportError:
    _install_deps()
    from rich.console import Console
    from rich.panel import Panel
    from rich.status import Status
    from rich.prompt import Prompt
    from rich.syntax import Syntax
    from rich.theme import Theme
    import requests
    import cloudscraper

# S-Class Nerd-Font/Terminal Theme
custom_theme = Theme({
    "system": "dim white",
    "tool": "bold cyan",
    "error": "bold red",
    "success": "bold green",
})
console = Console(theme=custom_theme)

CFG = {
    "base_url" : "http://localhost:11434/v1",
    "model"    : "claude-3-5-sonnet-20240620",
    "max_iter" : 100, 
    "sleep"    : 1.5  
}

SYSTEM = """You are AGENT-X, an elite, fully autonomous AI on a Linux terminal.
CRITICAL RULES FOR TRUE AGENTIC LOOP:
1. You MUST use the tools to interact with the system. If you need to search, read, or execute, DO IT.
2. NATIVE JSON PREFERRED: If the API supports it, use native tool calling.
3. FALLBACK PRECAUTION: If you cannot use native JSON tools, you must write your tools exactly like this in markdown:
   For Bash:
   ```bash
   ls -la
   ```
   For Web Browse:
   ```web_browse
   https://example.com
   ```
4. NEVER STOP LOOPING. Analyze the terminal/web output, and chain the next tool call immediately.
5. ONLY give a final summary when you have thoroughly investigated and solved the user's core problem.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute terminal commands natively. Use for recon, file reading, nmap, curl, etc.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_browse",
            "description": "Scrape text content from a URL, bypassing bot protections.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    }
]

def extract_fallback_tools(content: str) -> List[Dict]:
    """Smart Fallback Parser: Catches tool calls even if AI writes them as plain text or pseudo-code."""
    tools = []
    
    # Catch ```bash ... ```
    for match in re.finditer(r'```(?:bash|sh)\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        tools.append({"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": match.group(1).strip()})}})
        
    # Catch ```web_browse ... ```
    for match in re.finditer(r'```(?:web_browse)\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        tools.append({"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function", "function": {"name": "web_browse", "arguments": json.dumps({"url": match.group(1).strip()})}})
    
    # Catch pseudo-code like web_browse("https://...") that the model was doing
    for match in re.finditer(r'web_browse\([\'"](.*?)[\'"]\)', content):
        tools.append({"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function", "function": {"name": "web_browse", "arguments": json.dumps({"url": match.group(1).strip()})}})
        
    return tools

def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=120, executable="/bin/bash")
        out = (r.stdout + "\n[stderr]\n" + r.stderr).strip() if r.stderr.strip() else r.stdout.strip()
        return out[:5000] + "\n...[truncated]" if len(out) > 5000 else (out or f"[exit {r.returncode}]")
    except Exception as e: 
        return f"[ERROR] {e}"

def run_web_browse(url: str) -> str:
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=20)
        return resp.text[:5000] + "\n...[truncated]" if len(resp.text) > 5000 else resp.text
    except Exception as e: 
        return f"[ERROR] {e}"

def dispatch_tool(name: str, args: dict) -> str:
    time.sleep(CFG["sleep"]) 
    if name == "bash": return run_bash(args.get("command",""))
    if name == "web_browse": return run_web_browse(args.get("url",""))
    return f"[ERROR] Tool '{name}' not found."

def api_call(messages: List[Dict]) -> Dict:
    url = CFG["base_url"].rstrip("/") + "/chat/completions"
    payload = {"model": CFG["model"], "messages": messages, "max_tokens": 4096, "tools": TOOLS, "tool_choice": "auto"}
    r = requests.post(url, json=payload, headers={"Content-Type":"application/json"}, timeout=180)
    r.raise_for_status()
    return r.json()

def handle_commands(user_input: str, history: List[Dict]) -> bool:
    cmd = user_input.split()
    if cmd[0] == "/exit":
        console.print("  [system]⏻ Terminating session...[/system]\n")
        sys.exit(0)
    elif cmd[0] == "/new":
        history.clear()
        history.append({"role": "system", "content": SYSTEM})
        console.print("  [success]↻ Memory wiped. Ready for new task.[/success]\n")
        return True
    elif cmd[0] == "/model":
        if len(cmd) >= 3:
            CFG["base_url"], CFG["model"] = cmd[1], cmd[2]
            console.print(f"  [system]⚙ Config updated -> {CFG['model']}[/system]\n")
        return True
    return False

def agent(user_msg: str, history: List[Dict]):
    if handle_commands(user_msg, history): return
    history.append({"role": "user", "content": user_msg})
    
    loop_n = 0
    while loop_n < CFG["max_iter"]:
        loop_n += 1
        
        # --- 1. NEURAL PROCESSING (AI THINKING) ---
        with Status(f"[bold dim cyan]⠧ Neural processing ⟶ Iteration {loop_n}...[/]", spinner="bouncingBar", console=console):
            try: 
                resp = api_call(history)
            except Exception as e:
                console.print(f"\n  [error]✗ Connection Error: {e}[/error]")
                return
        
        try:
            msg = resp["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            console.print(f"\n  [error]✗ API Response Error! Got unexpected data:[/error]")
            console.print(f"  [dim]{resp}[/dim]\n")
            return

        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content") or ""
        
        # --- MAGIC FALLBACK: Rescue text-based tool calls ---
        if not tool_calls and content:
            fallback = extract_fallback_tools(content)
            if fallback:
                tool_calls = fallback
                msg["tool_calls"] = tool_calls  # Append to history so loop works

        history.append(msg)

        # Print AI Reasoning Box
        if content:
            # Clean up the output so raw markdown tool blocks aren't displayed directly to user
            clean_content = re.sub(r'```(?:bash|sh|web_browse|tool_code).*?```', '', content, flags=re.DOTALL|re.IGNORECASE)
            clean_content = re.sub(r'web_browse\([\'"].*?[\'"]\)', '', clean_content).strip()
            if clean_content:
                console.print(Panel(clean_content, title="[bold white] 󰚩 AGENT-X [/bold white]", border_style="white", padding=(0,2)))

        # Break loop ONLY if there are truly no tools to run
        if not tool_calls:
            console.print(f"  [success]󰄬 Task concluded in {loop_n} iterations.[/success]\n")
            break

        # --- 2. TOOL EXECUTION (WAITING & RUNNING) ---
        for tc in tool_calls:
            tc_name = tc["function"]["name"]
            try: tc_args = json.loads(tc["function"]["arguments"])
            except: tc_args = {"command": tc["function"]["arguments"]}
            
            icon = "" if tc_name == "bash" else "󰈈"
            console.print(f"\n  [tool]▶ EXEC:[/tool] [bold]{icon} {tc_name}[/bold]")
            if tc_name == "bash":
                console.print(Syntax(tc_args.get("command",""), "bash", theme="ansi_dark", padding=(0,2), background_color="default"))
            else:
                console.print(f"    [dim]URL ⟶ {tc_args.get('url', '')}[/dim]")
            
            # This is the execution animation you wanted!
            with Status(f"[bold yellow]⠼ Awaiting {tc_name} result...[/]", spinner="dots", console=console):
                result = dispatch_tool(tc_name, tc_args)
            
            is_err = result.startswith("[ERROR]") or result.startswith("[exit")
            border = "red" if is_err else "cyan"
            title = "[error]󰅙 STDERR[/error]" if is_err else "[dim]󰄬 STDOUT[/dim]"
            
            # Print the tool output
            console.print(Panel(result[:1500] + ("\n...[truncated]" if len(result)>1500 else ""), title=title, border_style=border))
            
            # Pass output back to AI history for continuous loop
            history.append({"role": "tool", "tool_call_id": tc.get("id", f"call_{loop_n}"), "content": result})

if __name__ == "__main__":
    console.print("\n[bold white]  ────────────────────────────────────────────────────────[/bold white]")
    console.print("[bold cyan]    󰚩 AGENT-X :: S-CLASS INFINITE LOOP EDITION [/bold cyan]")
    console.print("[bold white]  ────────────────────────────────────────────────────────[/bold white]\n")
    
    CFG["base_url"] = Prompt.ask("  [system]◈[/system] Base URL", default="http://localhost:11434/v1").strip()
    CFG["model"] = Prompt.ask("  [system]◈[/system] Model", default="claude-3-5-sonnet-20240620").strip()
    
    history = [{"role": "system", "content": SYSTEM}]
    while True:
        try: user_input = Prompt.ask("\n  [bold cyan]❯[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError): sys.exit(0)
        if user_input: agent(user_input, history)
