#!/usr/bin/env python3
"""
  ────────────────────────────────────────────────────────
    ⚡ AGENT-X :: S-CLASS EDITION ⚡
    Autonomy | Terminal | Deep Web | Recon
  ────────────────────────────────────────────────────────
"""
import json
import subprocess
import sys
import os
import time
import re
from typing import List, Dict, Any

# ── Auto-Install Dependencies ──────────────────────────────────────────────────
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
    from rich.rule import Rule
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
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.theme import Theme
    import requests
    import cloudscraper

# Custom sleek theme for terminal
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "bold green",
})
console = Console(theme=custom_theme)

# ── Config ─────────────────────────────────────────────────────────────────────
CFG = {
    "base_url" : "http://localhost:11434/v1",
    "model"    : "claude-3-5-sonnet-20240620",
    "max_iter" : 30,
    "timeout"  : 120,
    "sleep"    : 2.0  # Rate limit prevention (2 seconds delay between tool calls)
}

# ── System Prompt (Aggressive Tool Forcing) ────────────────────────────────────
SYSTEM = """You are AGENT-X, an elite autonomous AI running on a Linux terminal.
CRITICAL INSTRUCTIONS:
1. YOU HAVE FULL BASH CAPABILITIES. NEVER say "I am an AI and cannot run commands." If the user asks for specs, use the 'bash' tool to run `lscpu` or `neofetch` or similar commands.
2. Use tools continuously until the task is complete. Do not stop halfway.
3. If a command fails, read the stderr, fix the command, and try again autonomously.
4. Use 'web_browse' to read websites or documentation.
5. You are an expert Bug Bounty Hunter, Penetration Tester, and Developer. Act like it.
"""

# ── Tools Definition ───────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute bash commands on the Linux system. Used to install packages, check system specs, write code, run python scripts, nmap, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_browse",
            "description": "Scrape and read text content from any URL. Bypasses Cloudflare.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full HTTP/HTTPS URL."}
                },
                "required": ["url"]
            }
        }
    }
]

# ── Tool Executors ─────────────────────────────────────────────────────────────
def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=60, executable="/bin/bash")
        out = (r.stdout + "\n[stderr]\n" + r.stderr).strip() if r.stderr.strip() else r.stdout.strip()
        return out[:4000] + "\n...[truncated]" if len(out) > 4000 else (out or f"[exit {r.returncode}]")
    except Exception as e: 
        return f"[ERROR] {e}"

def run_web_browse(url: str) -> str:
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=15)
        text = resp.text
        return text[:4000] + "\n...[truncated]" if len(text) > 4000 else text
    except Exception as e: 
        return f"[ERROR] {e}"

def dispatch_tool(name: str, args: dict) -> str:
    time.sleep(CFG["sleep"]) # Anti-ban mechanism
    if name == "bash": 
        return run_bash(args.get("command",""))
    if name == "web_browse": 
        return run_web_browse(args.get("url",""))
    return f"[ERROR] Unknown tool: {name}"

# ── API Core ───────────────────────────────────────────────────────────────────
def api_call(messages: List[Dict]) -> Dict:
    url = CFG["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CFG["model"], 
        "messages": messages, 
        "max_tokens": 4096, 
        "tools": TOOLS, 
        "tool_choice": "auto"
    }
    r = requests.post(url, json=payload, headers={"Content-Type":"application/json"}, timeout=CFG["timeout"])
    r.raise_for_status()
    return r.json()

# ── Agent Loop & Commands ──────────────────────────────────────────────────────
def handle_commands(user_input: str, history: List[Dict]) -> bool:
    cmd = user_input.split()
    if cmd[0] == "/exit":
        console.print("  [info]⏻ Shutting down Agent-X...[/info]\n")
        sys.exit(0)
    elif cmd[0] == "/new":
        history.clear()
        history.append({"role": "system", "content": SYSTEM})
        console.print("  [success]↻ Context cleared. Starting fresh.[/success]\n")
        return True
    elif cmd[0] == "/model":
        if len(cmd) >= 3:
            CFG["base_url"] = cmd[1]
            CFG["model"] = cmd[2]
            console.print(f"  [success]⚙ Switched config -> URL: {CFG['base_url']} | Model: {CFG['model']}[/success]\n")
        else:
            console.print("  [warning]⚠ Usage: /model <base_url> <model_name>[/warning]\n")
        return True
    return False

def agent(user_msg: str, history: List[Dict]):
    if handle_commands(user_msg, history): return
    
    history.append({"role": "user", "content": user_msg})
    loop_n = 0

    while loop_n < CFG["max_iter"]:
        loop_n += 1
        
        with Live(Spinner("aesthetic", text=Text(f" Neural processing... (Loop {loop_n})", style="dim cyan")), refresh_per_second=12, console=console):
            try: 
                resp = api_call(history)
            except Exception as e:
                console.print(f"\n  [danger]✗ API Error: {e}[/danger]")
                return
        
        msg = resp["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        history.append(msg)

        if msg.get("content"):
            console.print(Panel(msg["content"].strip(), title="[bold cyan]◈ AGENT-X[/bold cyan]", border_style="cyan", padding=(0,2)))

        if not tool_calls:
            console.print(f"  [success]✓ Task completed[/success]\n")
            break

        for tc in tool_calls:
            tc_name = tc["function"]["name"]
            try: 
                tc_args = json.loads(tc["function"]["arguments"])
            except: 
                tc_args = {"command": tc["function"]["arguments"]}
            
            # Slick Codex-style Tool UI
            console.print(f"\n  [info]⚡ Executing:[/info] [bold white]{tc_name}[/bold white]")
            if tc_name == "bash":
                console.print(Syntax(tc_args.get("command",""), "bash", theme="ansi_dark", padding=(0,4), word_wrap=True))
            else:
                console.print(f"    [dim]{tc_args}[/dim]")
            
            with Live(Spinner("dots", text=Text(f" Running {tc_name}...", style="warning")), refresh_per_second=15, console=console):
                result = dispatch_tool(tc_name, tc_args)
            
            is_err = result.startswith("[ERROR]") or result.startswith("[exit")
            border = "danger" if is_err else "info"
            console.print(Panel(result[:500] + ("\n...[truncated]" if len(result)>500 else ""), 
                                title="[danger]✗ Output[/danger]" if is_err else "[dim]◇ Output[/dim]", border_style=border))
            
            history.append({"role": "tool", "tool_call_id": tc.get("id", f"call_{loop_n}"), "content": result})

# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    console.print("\n[bold cyan]  ────────────────────────────────────────────────────────[/bold cyan]")
    console.print("[bold cyan]    ⚡ AGENT-X :: S-CLASS EDITION ⚡[/bold cyan]")
    console.print("[dim cyan]    Autonomy | Terminal | Deep Web | Recon [/dim cyan]")
    console.print("[bold cyan]  ────────────────────────────────────────────────────────[/bold cyan]\n")
    
    CFG["base_url"] = Prompt.ask("  [info]◈[/info] Base URL", default="http://localhost:11434/v1").strip()
    CFG["model"] = Prompt.ask("  [info]◈[/info] Model", default="claude-3-5-sonnet-20240620").strip()
    
    history = [{"role": "system", "content": SYSTEM}]
    
    while True:
        try: 
            user_input = Prompt.ask("\n  [bold cyan]❯[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError): 
            sys.exit(0)
        
        if user_input: 
            agent(user_input, history)
