#!/usr/bin/env python3
"""
  ────────────────────────────────────────────────────────
    ⚡ AGENT-X v3 :: SMART AGENTIC LOOP ⚡
    True Autonomy | Smart Tool Detection | No Fake Tools
  ────────────────────────────────────────────────────────
"""

import json
import subprocess
import sys
import time
import re
import uuid
from typing import List, Dict, Optional

# ------------ AUTO-INSTALL DEPS ------------
def _install_deps():
    print("Installing requirements...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "rich", "requests", "cloudscraper", "--break-system-packages"],
        capture_output=True
    )

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.status import Status
    from rich.prompt import Prompt
    from rich.syntax import Syntax
    from rich.theme import Theme
    from rich.table import Table
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
    from rich.table import Table
    import requests
    import cloudscraper

# ------------ CONFIG & THEME ------------
custom_theme = Theme({
    "system": "dim white",
    "tool": "bold cyan",
    "error": "bold red",
    "success": "bold green",
    "waiting": "bold yellow",
    "info": "bold blue",
    "warning": "bold magenta",
})

console = Console(theme=custom_theme, force_terminal=True)

CFG = {
    "base_url": "http://localhost:11434/v1",
    "model": "claude-3-5-sonnet-20240620",
    "max_iter": 100,
    "sleep": 0.3,
    "verbose": True
}

AUTO = {"remaining": 0, "template": "continue"}

# Track if this is a new conversation
IS_NEW_TASK = True

SYSTEM = """You are AGENT-X, an elite, fully autonomous AI on a Linux terminal.

You have EXACTLY TWO tools available:

1. **bash** - Execute terminal commands (curl, nmap, python, ls, cat, etc.)
2. **web_browse** - Scrape text content from a URL, bypassing bot protections

CRITICAL RULES:
1. ONLY use tools when the user's request ACTUALLY requires them.
2. For greetings (hi, hello, hey) or simple questions - just respond normally, NO tools needed.
3. Use tools when user asks to: scan, analyze, investigate, fetch, check, run commands, etc.

4. Tool formats:
   ```bash
   ls -la
   ```
   
   ```web_browse
   https://example.com
   ```

5. DO NOT invent tools. Only "bash" and "web_browse" exist.

6. When user asks for analysis/investigation:
   - Run tool → Read output → Decide next step → Continue until FULLY complete
   - Only give final summary AFTER you have real data

7. DO NOT say "task completed" until you have actually executed tools and shown real results.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute terminal commands (curl, nmap, python, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Exact shell command to run"}
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
                    "url": {"type": "string", "description": "Absolute URL to fetch"}
                },
                "required": ["url"]
            }
        }
    }
]

# ------------ TOOL RUNNERS ------------
def run_bash(command: str) -> str:
    try:
        r = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=120,
            executable="/bin/bash"
        )
        parts = []
        if r.stdout.strip():
            parts.append(r.stdout.strip())
        if r.stderr.strip():
            parts.append(f"[STDERR]\n{r.stderr.strip()}")
        
        if not parts:
            out = f"[exit code: {r.returncode}]"
        else:
            out = "\n".join(parts)
            if r.returncode != 0:
                out = f"[exit code: {r.returncode}]\n{out}"
        
        return out[:5000] + "\n...[truncated]" if len(out) > 5000 else out
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out (120s)"
    except Exception as e:
        return f"[ERROR] {e}"

def run_web_browse(url: str) -> str:
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=20)
        text = resp.text
        return text[:5000] + "\n...[truncated]" if len(text) > 5000 else text
    except Exception as e:
        return f"[ERROR] {e}"

def dispatch_tool(name: str, args: dict) -> str:
    time.sleep(CFG["sleep"])
    if name == "bash":
        return run_bash(args.get("command", ""))
    if name == "web_browse":
        return run_web_browse(args.get("url", ""))
    return f"""[ERROR] Tool '{name}' does not exist!

You ONLY have these tools:
- bash: for terminal commands
- web_browse: for fetching URLs

Use this format:
```bash
your_command_here
```

or

```web_browse
https://example.com
```"""

# ------------ API CALL ------------
def api_call(messages: List[Dict]) -> Dict:
    url = CFG["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CFG["model"],
        "messages": messages,
        "max_tokens": 4096,
        "tools": TOOLS,
        "tool_choice": "auto"
    }
    r = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=180
    )
    r.raise_for_status()
    return r.json()

# ------------ FALLBACK PARSER ------------
def extract_fallback_tools(content: str) -> List[Dict]:
    tools = []
    
    # 1. ```bash ... ```
    for match in re.finditer(r'```(?:bash|sh)\s*\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        cmd = match.group(1).strip()
        if cmd:
            tools.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": "bash", "arguments": json.dumps({"command": cmd})}
            })
    
    # 2. ```web_browse ... ```
    for match in re.finditer(r'```web_browse\s*\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        url = match.group(1).strip()
        if url:
            tools.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": "web_browse", "arguments": json.dumps({"url": url})}
            })
    
    # 3. ```tool_code bash ... ```
    for match in re.finditer(r'```tool_code\s+bash\s*\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        cmd = match.group(1).strip()
        if cmd:
            tools.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": "bash", "arguments": json.dumps({"command": cmd})}
            })
    
    # 4. JSON blocks
    for match in re.finditer(r'```(?:tool_code|json)?\s*\n(\{.*?\})\s*\n```', content, re.DOTALL | re.IGNORECASE):
        json_str = match.group(1).strip()
        try:
            obj = json.loads(json_str)
            cmd = None
            url = None
            
            if "command" in obj:
                cmd = obj["command"]
            elif "url" in obj:
                url = obj["url"]
            elif "input" in obj and isinstance(obj["input"], dict):
                if "command" in obj["input"]:
                    cmd = obj["input"]["command"]
                if "url" in obj["input"]:
                    url = obj["input"]["url"]
            elif "tool_code" in obj:
                if obj.get("tool_code") in ["shell_command", "bash", "run_command"]:
                    if "input" in obj and isinstance(obj["input"], dict) and "command" in obj["input"]:
                        cmd = obj["input"]["command"]
            
            if cmd:
                tools.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {"name": "bash", "arguments": json.dumps({"command": cmd})}
                })
            if url:
                tools.append({
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {"name": "web_browse", "arguments": json.dumps({"url": url})}
                })
        except json.JSONDecodeError:
            pass
    
    # 5. Inline: shell_command("...")
    for match in re.finditer(r'(?:shell_command|run_command|execute)\s*\(\s*["\']([^"\']+)["\']\s*\)', content):
        cmd = match.group(1).strip()
        if cmd:
            tools.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": "bash", "arguments": json.dumps({"command": cmd})}
            })
    
    # 6. Inline: web_browse("...")
    for match in re.finditer(r'web_browse\s*\(\s*["\']([^"\']+)["\']\s*\)', content):
        url = match.group(1).strip()
        if url:
            tools.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": "web_browse", "arguments": json.dumps({"url": url})}
            })
    
    # Remove duplicates
    unique = []
    seen = set()
    for t in tools:
        sig = t["function"]["name"] + t["function"]["arguments"]
        if sig not in seen:
            seen.add(sig)
            unique.append(t)
    
    return unique

# ------------ COMMAND HANDLING ------------
def handle_commands(user_input: str, history: List[Dict]) -> bool:
    global IS_NEW_TASK
    cmd = user_input.split()
    if not cmd:
        return False
    
    if cmd[0] == "/exit":
        console.print("  [system]⏻ Terminating session...[/system]\n")
        sys.exit(0)
    
    if cmd[0] == "/new":
        history.clear()
        history.append({"role": "system", "content": SYSTEM})
        AUTO["remaining"] = 0
        IS_NEW_TASK = True
        console.print("  [success]↻ Memory wiped. Ready for new task.[/success]\n")
        return True
    
    if cmd[0] == "/model" and len(cmd) >= 3:
        CFG["base_url"], CFG["model"] = cmd[1], cmd[2]
        console.print(f"  [system]⚙ Config updated -> {CFG['model']}[/system]\n")
        return True
    
    if cmd[0].startswith("/continue"):
        parts = cmd[0].split("-")
        if len(parts) == 2 and parts[1].isdigit():
            AUTO["remaining"] = int(parts[1])
            AUTO["template"] = "continue"
            console.print(f"  [system]▶ Auto-continue armed for {AUTO['remaining']} steps.[/system]\n")
            return True
    
    if cmd[0] == "/verbose":
        CFG["verbose"] = not CFG["verbose"]
        console.print(f"  [system]Verbose mode: {CFG['verbose']}[/system]\n")
        return True
    
    if cmd[0] == "/help":
        table = Table(title="Available Commands", border_style="cyan")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_row("/exit", "Terminate session")
        table.add_row("/new", "Clear memory, start fresh")
        table.add_row("/model <url> <name>", "Change base URL and model")
        table.add_row("/continue-N", "Auto-continue for N steps")
        table.add_row("/verbose", "Toggle verbose output")
        table.add_row("/help", "Show this help")
        console.print(table)
        return True
    
    return False

# ------------ CHECK IF TASK NEEDS TOOLS ------------
def task_requires_tools(user_msg: str) -> bool:
    """
    Check if the user's message actually requires tool execution.
    Returns True if tools are needed, False for simple chat.
    """
    msg_lower = user_msg.lower().strip()
    
    # Greetings - no tools needed
    greetings = ["hi", "hii", "hiii", "hello", "hey", "yo", "sup", "howdy", "namaste", " Salaam", "good morning", "good evening", "good afternoon"]
    if msg_lower in greetings:
        return False
    
    # Short messages that are clearly chat
    if len(msg_lower.split()) <= 2 and not any(c in msg_lower for c in ["$", ">", "|", "&"]):
        # Check if it's just a greeting or acknowledgment
        chat_words = ["ok", "okay", "thanks", "thank", "yes", "no", "sure", "done", "cool", "nice", "great", "awesome"]
        if msg_lower in chat_words:
            return False
    
    # Questions that don't need tools (general knowledge)
    general_questions = ["who are you", "what can you do", "what is your name", "how are you", "what's up"]
    if any(q in msg_lower for q in general_questions):
        return False
    
    # Action keywords that REQUIRE tools
    action_keywords = [
        "scan", "analyze", "analyse", "check", "fetch", "get", "run", "execute",
        "investigate", "explore", "find", "search", "lookup", "download",
        "install", "remove", "delete", "create", "make", "build", "compile",
        "test", "debug", "fix", "hack", "exploit", "enum", "enumerate",
        "curl", "wget", "nmap", "python", "bash", "shell", "terminal",
        "command", "script", "file", "directory", "folder", "list files",
        "show me", "give me", "tell me about", "what is in", "read the",
        "cat ", "ls ", "grep ", "find ", "open ", "visit", "browse",
        "website", "url", "http", "api", "endpoint", "server"
    ]
    
    if any(kw in msg_lower for kw in action_keywords):
        return True
    
    # Contains command-like syntax ($, |, >, &)
    if any(c in user_msg for c in ["$", "|", ">", "&", "./", "~/", "/"]):
        return True
    
    # Contains code-like patterns
    if "```" in user_msg or "`" in user_msg:
        return True
    
    # Default: doesn't need tools (simple chat)
    return False

# ------------ CHECK IF SHOULD CONTINUE ------------
def should_continue(content: str, tool_calls: List[Dict], iteration: int, total_tools_executed: int, needs_tools: bool) -> tuple:
    """
    Decide if agent should continue looping.
    Returns (should_continue, reason)
    """
    # If we have tool calls, execute them
    if tool_calls:
        return True, "tools_detected"
    
    # If no content, just stop
    if not content:
        return False, "no_content"
    
    low = content.lower()
    
    # If task doesn't need tools, just respond normally
    if not needs_tools:
        # Check if AI is done responding
        completion_phrases = ["task completed", "operation concluded", "done", "finished", "that's all"]
        if any(phrase in low for phrase in completion_phrases):
            return False, "chat_complete"
        # If we've had one response without tools for a chat message, we're done
        return False, "chat_response"
    
    # FOR TASKS THAT NEED TOOLS:
    
    # Completion phrases - only stop if tools were actually executed
    completion_phrases = [
        "task completed", "task is complete", "operation concluded",
        "here is the final", "final answer", "in conclusion",
        "to summarize", "summary:", "i have completed", "done", "finished"
    ]
    
    if any(phrase in low for phrase in completion_phrases):
        # If no tools executed yet, this is fake completion
        if total_tools_executed == 0:
            return True, "fake_completion_no_tools"
        if iteration <= 2:
            return True, "fake_completion_too_early"
        return False, "genuine_completion"
    
    # Check for planning-only language
    planning_phrases = [
        "i will", "i'm going to", "let me", "i'll start",
        "i need to", "first, i'll", "i should", "i can help"
    ]
    
    if any(phrase in low for phrase in planning_phrases):
        # Only prompt for action if we haven't executed any tools yet
        if total_tools_executed == 0:
            return True, "planning_phase"
        return True, "still_planning"
    
    # If we've executed tools but AI is still talking, let it finish
    if total_tools_executed > 0 and iteration > 3:
        if len(content) < 100:  # Short message, probably done
            return False, "short_message_after_tools"
    
    # Default for tool-requiring tasks
    if iteration < 3 and total_tools_executed == 0:
        return True, "need_tools"
    
    return False, "default_stop"

# ------------ CORE AGENT LOOP ------------
def agent(user_msg: str, history: List[Dict]):
    global IS_NEW_TASK
    
    if handle_commands(user_msg, history):
        return
    
    # Check if this task needs tools
    needs_tools = task_requires_tools(user_msg)
    
    # Mark as no longer new task after first message
    if IS_NEW_TASK:
        IS_NEW_TASK = False
    
    history.append({"role": "user", "content": user_msg})
    
    loop_n = 0
    total_tools_executed = 0
    consecutive_no_tools = 0
    
    while loop_n < CFG["max_iter"]:
        loop_n += 1
        tools_executed_in_iter = 0
        
        # THINKING PHASE
        with Status(
            f"[bold cyan]⠧ Processing iteration {loop_n}...[/]",
            spinner="dots",
            console=console
        ):
            try:
                resp = api_call(history)
            except Exception as e:
                console.print(f"\n  [error]✗ API Error: {e}[/error]")
                return
        
        try:
            msg = resp["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            console.print("\n  [error]✗ API Response format unexpected.[/error]\n")
            return
        
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        
        # FALLBACK: detect tools from text / markdown
        if not tool_calls and content:
            fb = extract_fallback_tools(content)
            if fb:
                tool_calls = fb
                msg["tool_calls"] = tool_calls
                if CFG["verbose"]:
                    console.print("  [waiting]⚠ Detected tool calls in text format[/waiting]")
        
        history.append(msg)
        
        # SHOW AI THOUGHTS (cleaned text)
        if content and CFG["verbose"]:
            clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
            if clean:
                console.print(
                    Panel(
                        clean[:800] + ("..." if len(clean) > 800 else ""),
                        title="[bold white]🤖 AGENT-X[/bold koonwhite]",
                        border_style="white",
                        padding=(0, 2)
                    )
                )
        
        # NO TOOLS: decide whether to stop or keep looping
        if not tool_calls:
            should_cont, reason = should_continue(content, tool_calls, loop_n, total_tools_executed, needs_tools)
            
            if not should_cont:
                if CFG["verbose"]:
                    console.print(f"  [success]✓ Done ({reason})[/success]\n")
                
                # Show final summary if available
                if content and not CFG["verbose"]:
                    clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
                    if clean:
                        console.print(Panel(clean[:500], title="[bold green]Response[/bold green]", border_style="green"))
                
                # Auto-follow-up
                time.sleep(1)
                if AUTO["remaining"] > 0:
                    AUTO["remaining"] -= 1
                    console.print(f"  [system]⟶ Auto follow-up: {AUTO['template']} (remaining {AUTO['remaining']})[/system]")
                    agent(AUTO["template"], history)
                return
            else:
                consecutive_no_tools += 1
                
                # Only prompt AI to execute tools if:
                # 1. Task actually needs tools
                # 2. We haven't executed any yet
                # 3. AI is in planning phase or faking completion
                if needs_tools and total_tools_executed == 0 and reason in ["fake_completion_no_tools", "planning_phase", "need_tools"]:
                    if CFG["verbose"]:
                        console.print(f"  [warning]⚠ Prompting AI to execute tools...[/warning]")
                    history.append({
                        "role": "user",
                        "content": "CRITICAL: This task requires tool execution. Use bash or web_browse to actually DO something. DO NOT just plan - EXECUTE a command now."
                    })
                    continue
                elif consecutive_no_tools >= 3:
                    # Stuck without tools
                    if needs_tools:
                        console.print(f"  [error]✗ Agent stuck after {loop_n} iterations without tool use.[/error]\n")
                    return
        else:
            consecutive_no_tools = 0
        
        # TOOL EXECUTION PHASE
        for tc in tool_calls:
            tc_name = tc["function"]["name"]
            try:
                tc_args = json.loads(tc["function"]["arguments"])
            except Exception:
                tc_args = {"command": tc["function"]["arguments"]}
            
            icon = "💻" if tc_name == "bash" else "🌐"
            console.print(f"\n  [tool]▶ EXEC:[/tool] [bold]{icon} {tc_name}[/bold]")
            
            if tc_name == "bash":
                console.print(
                    Syntax(
                        tc_args.get("command", ""),
                        "bash",
                        theme="ansi_dark",
                        padding=(0, 2),
                        background_color="default"
                    )
                )
            else:
                console.print(f"    [dim]ARG ⟶ {list(tc_args.values())[0] if tc_args else 'None'}[/dim]")
            
            # WAITING animation
            with Status(
                f"[bold yellow]⠼ Running {tc_name}...[/]",
                spinner="dots",
                console=console
            ):
                result = dispatch_tool(tc_name, tc_args)
            
            tools_executed_in_iter += 1
            total_tools_executed += 1
            
            is_err = result.startswith("[ERROR]") or ("exit code:" in result and "0]" not in result)
            border = "red" if is_err else "green"
            title = "[error]❌ ERROR[/error]" if is_err else "[success]✓ RESULT[/success]"
            
            console.print(
                Panel(
                    result[:1500] + ("\n...[truncated]" if len(result) > 1500 else ""),
                    title=title,
                    border_style=border,
                    padding=(0, 1)
                )
            )
            
            # tool output -> model
            history.append({
                "role": "tool",
                "tool_call_id": tc.get("id", f"call_{loop_n}"),
                "content": result
            })
        
        # After executing tools, continue loop to process results
        if tools_executed_in_iter > 0:
            continue

# ------------ MAIN ------------
if __name__ == "__main__":
    console.print("\n[bold white]  ────────────────────────────────────────────────────────[/bold white]")
    console.print("[bold cyan]    ⚡ AGENT-X v3 :: SMART AGENTIC LOOP ⚡[/bold cyan]")
    console.print("[bold white]  ────────────────────────────────────────────────────────[/bold white]\n")
    
    CFG["base_url"] = Prompt.ask("  [system]◈[/system] Base URL", default="http://localhost:11434/v1").strip()
    CFG["model"] = Prompt.ask("  [system]◈[/system] Model", default="claude-3-5-sonnet-20240620").strip()
    
    console.print("\n  [info]Type /help for available commands[/info]\n")
    
    history: List[Dict] = [{"role": "system", "content": SYSTEM}]
    
    while True:
        try:
            if AUTO["remaining"] > 0:
                user_input = AUTO["template"]
                AUTO["remaining"] -= 1
                console.print(f"\n  [system]⟶ Auto: {user_input} (remaining {AUTO['remaining']})[/system]")
            else:
                user_input = Prompt.ask("\n  [bold cyan]❯[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n  [system]👋 Goodbye![/system]\n")
            sys.exit(0)
        
        if user_input:
            agent(user_input, history)


