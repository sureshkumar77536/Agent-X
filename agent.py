#!/usr/bin/env python3
"""
  ────────────────────────────────────────────────────────
    ⚡ AGENT-X :: S-CLASS INFINITE LOOP EDITION ⚡
    True Autonomy | Smart Tool Detection | Pro Terminal UI
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
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "rich", "requests", "cloudscraper", "--break-system-packages"],
        capture_output=True
    )

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

# S-Class Theme
custom_theme = Theme({
    "system": "dim white",
    "tool": "bold cyan",
    "error": "bold red",
    "success": "bold green",
})
console = Console(theme=custom_theme, force_terminal=True)

CFG = {
    "base_url": "http://localhost:11434/v1",
    "model": "claude-3-5-sonnet-20240620",
    "max_iter": 100,
    "sleep": 1.5
}

SYSTEM = """You are AGENT-X, an elite, fully autonomous AI on a Linux terminal.

You have EXACTLY TWO tools:
- bash
- web_browse

RULES:
1. DO NOT invent tools like web_search or google_search.
2. Prefer native JSON tool calling if the API supports it.
3. If you cannot use JSON tools, use these markdown formats:

   ```bash
   ls -la
   ```

   ```web_browse
   https://example.com
   ```

4. Every time the user asks you to investigate something, you MUST actually use tools.
5. NEVER stop after just planning. You must:
   - run tools,
   - read outputs,
   - decide next tools,
   - repeat until the root problem is fully analyzed.
6. Only give a final summary AFTER you are satisfied you have gone deep enough.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute terminal commands natively (curl, nmap, python, etc.)",
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
        out = (r.stdout + "\n[stderr]\n" + r.stderr).strip() if r.stderr.strip() else r.stdout.strip()
        if not out:
            out = f"[exit {r.returncode}]"
        return out[:5000] + "\n...[truncated]" if len(out) > 5000 else out
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
    # hallucinated tool
    return f"[ERROR] Tool '{name}' does not exist. You ONLY have 'bash' and 'web_browse'. Fix your tool usage."

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
    """Detects tools from markdown / pseudo-code, including `tool_code` blocks."""
    tools: List[Dict] = []

    # ```bash ... ```
    for match in re.finditer(r'```(?:bash|sh)\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        cmd = match.group(1).strip()
        tools.append({
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": json.dumps({"command": cmd})
            }
        })

    # ```web_browse ... ```
    for match in re.finditer(r'```web_browse\n(.*?)\n```', content, re.DOTALL | re.IGNORECASE):
        url = match.group(1).strip()
        tools.append({
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": "web_browse",
                "arguments": json.dumps({"url": url})
            }
        })

    # ```tool_code  bash\n <cmd> ```
    for match in re.finditer(r'```tool_code\s*bash\s*(.*?)```', content, re.DOTALL | re.IGNORECASE):
        block = match.group(1)
        # first non-empty line is command
        cmd = block.strip()
        tools.append({
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": json.dumps({"command": cmd})
            }
        })

    # ```tool_code ... web_browse("url") ... ```
    for match in re.finditer(r'```tool_code\s*(.*?)```', content, re.DOTALL | re.IGNORECASE):
        block = match.group(1)
        m = re.search(r'web_browse\(["\'](.*?)["\']\)', block)
        if m:
            url = m.group(1).strip()
            tools.append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": "web_browse",
                    "arguments": json.dumps({"url": url})
                }
            })

    # standalone web_browse("...")
    for match in re.finditer(r'web_browse\(["\'](.*?)["\']\)', content):
        url = match.group(1).strip()
        tools.append({
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": "web_browse",
                "arguments": json.dumps({"url": url})
            }
        })

    # remove duplicates
    unique: List[Dict] = []
    seen = set()
    for t in tools:
        sig = t["function"]["name"] + t["function"]["arguments"]
        if sig not in seen:
            seen.add(sig)
            unique.append(t)

    return unique

# ------------ COMMAND HANDLING ------------

def handle_commands(user_input: str, history: List[Dict]) -> bool:
    cmd = user_input.split()
    if not cmd:
        return False
    if cmd[0] == "/exit":
        console.print("  [system]⏻ Terminating session...[/system]\n")
        sys.exit(0)
    if cmd[0] == "/new":
        history.clear()
        history.append({"role": "system", "content": SYSTEM})
        console.print("  [success]↻ Memory wiped. Ready for new task.[/success]\n")
        return True
    if cmd[0] == "/model" and len(cmd) >= 3:
        CFG["base_url"], CFG["model"] = cmd[1], cmd[2]
        console.print(f"  [system]⚙ Config updated -> {CFG['model']}[/system]\n")
        return True
    return False

# ------------ CORE AGENT LOOP ------------

def agent(user_msg: str, history: List[Dict]):
    if handle_commands(user_msg, history):
        return

    history.append({"role": "user", "content": user_msg})
    loop_n = 0

    while loop_n < CFG["max_iter"]:
        loop_n += 1

        # THINKING PHASE
        with Status(
            f"[bold cyan]⠧ Neural Processing ⟶ Iteration {loop_n}...[/]",
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
            console.print(f"  [dim]{resp}[/dim]")
            return

        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        # FALLBACK: detect tools from text / markdown
        if not tool_calls and content:
            fb = extract_fallback_tools(content)
            if fb:
                tool_calls = fb
                msg["tool_calls"] = tool_calls

        history.append(msg)

        # SHOW AI THOUGHTS (text cleaned of raw code blocks)
        if content:
            clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
            if clean:
                console.print(
                    Panel(
                        clean,
                        title="[bold white] 󰚩 AGENT-X [/bold white]",
                        border_style="white",
                        padding=(0, 2)
                    )
                )

        # NO TOOLS: decide whether to stop or force another iteration
        if not tool_calls:
            low = content.lower()
            if any(word in low for word in ["final", "summary", "recommendation", "conclusion", "in short"]):
                console.print(f"  [success]󰄬 Task concluded in {loop_n} iterations.[/success]\n")
                break
            else:
                # Model sirf planning kar raha hai, force another thinking step
                continue

        # TOOL EXECUTION PHASE
        for tc in tool_calls:
            tc_name = tc["function"]["name"]
            try:
                tc_args = json.loads(tc["function"]["arguments"])
            except Exception:
                tc_args = {"command": tc["function"]["arguments"]}

            icon = "" if tc_name == "bash" else "󰈈"
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

            with Status(
                f"[bold yellow]⠼ Awaiting {tc_name} result...[/]",
                spinner="dots",
                console=console
            ):
                result = dispatch_tool(tc_name, tc_args)

            is_err = result.startswith("[ERROR]") or result.startswith("[exit")
            border = "red" if is_err else "cyan"
            title = "[error]󰅙 STDERR / ERROR[/error]" if is_err else "[dim]󰄬 STDOUT / RESPONSE[/dim]"

            console.print(
                Panel(
                    result[:1500] + ("\n...[truncated]" if len(result) > 1500 else ""),
                    title=title,
                    border_style=border
                )
            )

            # tool output goes back to model
            history.append({
                "role": "tool",
                "tool_call_id": tc.get("id", f"call_{loop_n}"),
                "content": result
            })

# ------------ MAIN ------------

if __name__ == "__main__":
    console.print("\n[bold white]  ────────────────────────────────────────────────────────[/bold white]")
    console.print("[bold cyan]    󰚩 AGENT-X :: S-CLASS INFINITE LOOP EDITION [/bold cyan]")
    console.print("[bold white]  ────────────────────────────────────────────────────────[/bold white]\n")

    CFG["base_url"] = Prompt.ask("  [system]◈[/system] Base URL", default="http://localhost:11434/v1").strip()
    CFG["model"] = Prompt.ask("  [system]◈[/system] Model", default="claude-3-5-sonnet-20240620").strip()

    history: List[Dict] = [{"role": "system", "content": SYSTEM}]
    while True:
        try:
            user_input = Prompt.ask("\n  [bold cyan]❯[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
        if user_input:
            agent(user_input, history)
