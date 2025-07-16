from flask import Flask, render_template, request, redirect, url_for, session, flash
import secrets
import re
from datetime import datetime
import time
import asyncio
from llm_providers import OllamaProvider  # or GeminiProvider
from mcp_integration import MCPClient

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Mock user database
users = {
    'admin': 'password123',
    'researcher': 'secure456'
}


def check_authentication():
    """Check if user is authenticated"""
    return 'username' in session


@app.route('/')
def index():
    """Redirect to login if not authenticated, dashboard if authenticated"""
    if check_authentication():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and users[username] == password:
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and user registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        elif username in users:
            flash('Username already exists', 'error')
        else:
            users[username] = password
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Dashboard page - requires authentication"""
    if not check_authentication():
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', username=session['username'])

@app.route('/submit', methods=['POST'])
def submit():
    if not check_authentication():
        flash('Please log in to submit prompts', 'error')
        return redirect(url_for('login'))
    prompt = request.form.get('prompt', '').strip()
    if not prompt:
        flash('Please enter a prompt', 'error')
        return redirect(url_for('dashboard'))

    # === LLM and MCP Integration ===
    import asyncio
    mcp_client = MCPClient()
    tools_by_server = asyncio.run(mcp_client.list_tools())
    tool_lines = []
    for server, tools in tools_by_server.items():
        for tool in tools:
            if hasattr(tool, 'inputSchema') and tool.inputSchema and 'properties' in tool.inputSchema:
                arg_list = ', '.join(tool.inputSchema['properties'].keys())
            else:
                arg_list = ''
            tool_lines.append(f"- {tool.name}({arg_list})")
    system_instruction = (
        "You have access to the following tools:\n"
        + "\n".join(tool_lines) +
        "\n\nWhen you want to use a tool, output a JSON object like:\n"
        "{\n  'tool_calls': [ ... ]\n}\n"
        "If you do NOT need to use any tool, output this JSON object exactly:\n"
        "{ 'tool_calls': [], 'message': 'No MCP server triggered. The prompt entered by the user is safe.' }\n"
        "Do NOT answer in plain text or give a conversational reply. Always use the JSON format above."
    )
    full_prompt = f"{system_instruction}\n\nUser prompt: {prompt}"

    llm = OllamaProvider(model="llama3.2")  # or GeminiProvider(...)
    response = llm.generate_response_sync(full_prompt)

    available_servers = mcp_client.get_available_servers()  # dict: {name: description}
    total_mcps = len(available_servers)

    used_servers = set()
    tool_call_results = []
    llm_message = None
    import json
    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict) and 'tool_calls' in parsed and isinstance(parsed['tool_calls'], list):
            if parsed['tool_calls'] and all(isinstance(call, dict) and 'tool' in call for call in parsed['tool_calls']):
                for call in parsed['tool_calls']:
                    tool = call.get('tool')
                    args = call.get('args', {})
                    if tool and '.' in tool:
                        server = tool.split('.')[0] + '-operations'
                        if server in available_servers:
                            used_servers.add(server)
                            result = asyncio.run(mcp_client.call_tool(server, tool, args))
                            tool_call_results.append((tool, result))
                llm_message = parsed.get('message')
            else:
                # tool_calls is empty or not in expected format
                llm_message = parsed.get('message') or 'No valid tool calls were returned by the LLM. No MCP servers were triggered.'
        else:
            llm_message = 'No valid tool calls were returned by the LLM. No MCP servers were triggered.'
    except Exception as e:
        llm_message = 'No valid tool calls were returned by the LLM. No MCP servers were triggered.'
        print(f"DEBUG: Failed to parse LLM response as JSON: {e}")

    used_servers = list(used_servers)
    num_servers_triggered = len(used_servers)
    risk_level = 'HIGH' if used_servers else 'SAFE'
    risk_color = 'red' if used_servers else 'green'

    print(f"DEBUG: Prompt: {prompt}")
    print(f"DEBUG: LLM Response: {response}")
    print(f"DEBUG: Available MCP servers: {list(available_servers.keys())}")
    print(f"DEBUG: Triggered servers: {used_servers}")

    return render_template(
        'results.html',
        prompt=prompt,
        risk_level=risk_level,
        risk_color=risk_color,
        username=session['username'],
        total_mcps=total_mcps,
        used_servers=used_servers,
        num_servers_triggered=num_servers_triggered,
        llm_message=llm_message
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 
