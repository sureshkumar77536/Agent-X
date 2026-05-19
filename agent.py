#!/usr/bin/env python3
"""
  ────────────────────────────────────────────────────────
    ⚡ AGENT-X :: S-CLASS INFINITE LOOP EDITION ⚡
    True Autonomy | Clean UI | Continuous Execution
  ────────────────────────────────────────────────────────
"""
import json
import subprocess
import sys
import os
import time
from typing import List, Dict, Any

def _install_deps():
    print("Installing requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "rich", "requests", "cloudscraper", "--break-system-packages"], capture_output=True)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.prompt import Prompt
    from rich.syntax import Syntax
    from rich.theme import Theme
    import requests
    import cloudscraper
except ImportError:
    _install_deps()
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.prompt import Prompt
    from rich.syntax import Syntax
    from rich.theme import Theme
    import requests
    import cloudscraper

# Clean, professional S-Class Theme
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
    "max_iter" : 100, # Increased for deep continuous looping
    "sleep"    : 1.5  
}

SYSTEM = """You are AGENT-X, an elite, fully autonomous AI on a Linux terminal.
CRITICAL RULES FOR TRUE AGENTIC LOOP:
1. YOU MUST NEVER WRITE TOOL CALLS AS TEXT OR MARKDOWN (e.g., do not write ````tool_code`). YOU MUST USE THE NATIVE JSON TOOL CALLING API.
2. If you need to search, read, or execute, use the tools immediately.
3. NEVER stop after one tool call if the task isn't 100% complete. Analyze the output and chain the next tool call.
4. If a command fails, automatically run a new command to fix it. 
5. Only send a regular text response when you have fully achieved the user's end goal after multiple steps.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute terminal commands natively. Use for recon, file reading, nmap, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact shell command."}
                },
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
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        }
    }
]

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
    payload = {
        "model": CFG["model"], 
        "messages": messages, 
        "max_tokens": 4096, 
        "tools": TOOLS, 
        "tool_choice": "auto"
    }
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
        
        with Live(Spinner("bouncingBar", text=Text(f" Processing (Iter {loop_n})...", style="dim white")), refresh_per_second=15, console=console):
            try: 
                resp = api_call(history)
            except Exception as e:
                console.print(f"\n  [error]✗ Connection Error: {e}[/error]"); return
        
        msg = resp["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        history.append(msg)

        # AI directly talking to you
        if msg.get("content"):
            console.print(Panel(msg["content"].strip(), title="[bold white]AGENT-X[/bold white]", border_style="white", padding=(0,2)))

        # Break loop ONLY if no tools are called (Task actually finished)
        if not tool_calls:
            console.print(f"  [success]✓ Operation concluded in {loop_n} steps.[/success]\n")
            break

        # Execute Tools Continuously
        for tc in tool_calls:
            tc_name = tc["function"]["name"]
            try: tc_args = json.loads(tc["function"]["arguments"])
            except: tc_args = {"command": tc["function"]["arguments"]}
            
            # Clean Pro UI for command execution
            console.print(f"\n  [tool]▶ EXEC:[/tool] [bold]{tc_name}[/bold]")
            if tc_name == "bash":
                console.print(Syntax(tc_args.get("command",""), "bash", theme="ansi_dark", padding=(0,2), background_color="default"))
            else:
                console.print(f"    [dim]{tc_args}[/dim]")
            
            with Live(Spinner("dots", text=Text(f" Awaiting output...", style="cyan")), refresh_per_second=15, console=console):
                result = dispatch_tool(tc_name, tc_args)
            
            is_err = result.startswith("[ERROR]") or result.startswith("[exit")
            border = "red" if is_err else "cyan"
            
            # Show output cleanly
            console.print(Panel(result[:500] + ("\n...[truncated]" if len(result)>500 else ""), 
                                title="[error]STDERR[/error]" if is_err else "[dim]STDOUT[/dim]", border_style=border))
            
            # Feed result back to AI so it continues the loop
            history.append({"role": "tool", "tool_call_id": tc.get("id", f"call_{loop_n}"), "content": result})

if __name__ == "__main__":
    console.print("\n[bold white]  ────────────────────────────────────────────────────────[/bold white]")
    console.print("[bold cyan]    ⚡ AGENT-X :: S-CLASS INFINITE LOOP EDITION ⚡[/bold cyan]")
    console.print("[bold white]  ────────────────────────────────────────────────────────[/bold white]\n")
    
    CFG["base_url"] = Prompt.ask("  [system]◈[/system] Base URL", default="http://localhost:11434/v1").strip()
    CFG["model"] = Prompt.ask("  [system]◈[/system] Model", default="claude-3-5-sonnet-20240620").strip()
    
    history = [{"role": "system", "content": SYSTEM}]
    while True:
        try: user_input = Prompt.ask("\n  [bold cyan]❯[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError): sys.exit(0)
        if user_input: agent(user_input, history)
