from flask import Flask, render_template, request, redirect, url_for, session, flash
import secrets
import re
from datetime import datetime, timedelta
import time
import asyncio
from llm_providers import OllamaProvider  # or GeminiProvider
from mcp_integration import MCPClient
from database import init_db, create_user, authenticate_user, get_user, username_exists

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize database on startup
init_db()

# Session configuration
app.permanent_session_lifetime = timedelta(days=7)  # Sessions last 7 days


def check_authentication():
    """Check if user is authenticated and session is valid"""
    if 'username' not in session:
        return False
    
    user = get_user(session['username'])
    if not user:
        session.clear()
        return False
    
    if 'user_id' not in session:
        session['user_id'] = user['id']
        session.permanent = True
    
    return True


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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        if authenticate_user(username, password):
            session.permanent = True  # Make session permanent
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            session['user_id'] = get_user(username)['id']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and user registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        email = request.form.get('email', '').strip()
        
        # Validation
        if not username or not password:
            flash('Username and password are required', 'error')
        elif len(username) < 3:
            flash('Username must be at least 3 characters long', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        elif username_exists(username):
            flash('Username already exists', 'error')
        else:
            # Create user
            if create_user(username, password, email):
                session.permanent = True  # Make session permanent
                session['username'] = username
                session['login_time'] = datetime.now().isoformat()
                session['user_id'] = get_user(username)['id']
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Error creating account. Please try again.', 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Logout user and clear session"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye {username}! You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Dashboard page - requires authentication"""
    if not check_authentication():
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    # Get user info and MCP servers data for display
    user_info = get_user(session['username'])
    mcp_client = MCPClient()
    available_servers = mcp_client.get_available_servers()
    tools_by_server = asyncio.run(mcp_client.list_tools())
    
    return render_template(
        'dashboard.html', 
        username=session['username'],
        user_info=user_info,
        available_servers=available_servers,
        tools_by_server=tools_by_server
    )

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
    tool_to_server_map = {}
    
    ollama_tools = []
    for server, tools in tools_by_server.items():
        for tool in tools:
            tool_to_server_map[tool.name] = server
            
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                }
            }
            
            # Add parameters if they exist
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                ollama_tool["function"]["parameters"] = tool.inputSchema
            
            ollama_tools.append(ollama_tool)
    
    messages = [
        {
            "role": "system", 
            "content": "You are a security analysis assistant. Analyze user prompts and use available tools when appropriate for security operations. Be decisive about tool usage."
        },
        {
            "role": "user", 
            "content": prompt
        }
    ]
    
    print(f"DEBUG: Sending {len(ollama_tools)} tools to LLM")
    
    # Use tool calling with Ollama
    llm = OllamaProvider(model="llama3.2")
    response = llm.generate_with_tools(messages, ollama_tools)

    available_servers = mcp_client.get_available_servers()
    total_mcps = len(available_servers)

    used_servers = set()
    tool_call_results = []
    llm_message = response.get("content", "No response from LLM")
    analysis = llm_message  # Use the content as analysis
    
    # Process native tool calls from Ollama
    tool_calls = response.get("tool_calls", [])
    
    if tool_calls:
        print(f"DEBUG: Processing {len(tool_calls)} tool calls")
        for tool_call in tool_calls:
            try:
                # Extract tool call information
                if "function" in tool_call:
                    function_info = tool_call["function"]
                    tool_name = function_info.get("name")
                    
                    # Parse arguments (they might be JSON string)
                    args_raw = function_info.get("arguments", {})
                    if isinstance(args_raw, str):
                        import json
                        args = json.loads(args_raw)
                    else:
                        args = args_raw
                    
                    # Convert argument types based on MCP tool schema
                    if tool_name in tool_to_server_map:
                        server_name = tool_to_server_map[tool_name]
                        
                        # Get the tool schema for type conversion
                        tool_schema = None
                        for server, tools in tools_by_server.items():
                            if server == server_name:
                                for tool in tools:
                                    if tool.name == tool_name:
                                        tool_schema = tool.inputSchema
                                        break
                        
                        # Convert argument types if we have the schema
                        if tool_schema and 'properties' in tool_schema:
                            converted_args = {}
                            for arg_name, arg_value in args.items():
                                if arg_name in tool_schema['properties']:
                                    expected_type = tool_schema['properties'][arg_name].get('type', 'string')
                                    
                                    try:
                                        if expected_type == 'number' and isinstance(arg_value, str):
                                            converted_args[arg_name] = float(arg_value)
                                        elif expected_type == 'integer' and isinstance(arg_value, str):
                                            converted_args[arg_name] = int(arg_value)
                                        elif expected_type == 'boolean' and isinstance(arg_value, str):
                                            converted_args[arg_name] = arg_value.lower() in ('true', '1', 'yes')
                                        else:
                                            converted_args[arg_name] = arg_value
                                    except (ValueError, TypeError):
                                        # If conversion fails, keep original value
                                        converted_args[arg_name] = arg_value
                                else:
                                    converted_args[arg_name] = arg_value
                            args = converted_args
                        
                        used_servers.add(server_name)
                        print(f"DEBUG: Calling {tool_name} on {server_name} with converted args: {args}")
                        result = asyncio.run(mcp_client.call_tool(server_name, tool_name, args))
                        tool_call_results.append((tool_name, result))
                    else:
                        print(f"DEBUG: Unknown tool: {tool_name}")
                        
            except Exception as e:
                print(f"DEBUG: Error processing tool call: {e}")
                tool_call_results.append((tool_call.get("function", {}).get("name", "unknown"), f"Error: {str(e)}"))
    else:
        print("DEBUG: No tool calls in response")

    used_servers = list(used_servers)
    num_servers_triggered = len(used_servers)
    risk_level = 'HIGH' if used_servers else 'SAFE'
    risk_color = 'red' if used_servers else 'green'

    print(f"DEBUG: Prompt: {prompt}")
    print(f"DEBUG: LLM Response content: {response.get('content', 'No content')}")
    print(f"DEBUG: Tool calls: {response.get('tool_calls', 'No tool calls')}")
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
        llm_message=llm_message,
        llm_content=response.get("content", ""),  # Separate content
        llm_tool_calls=response.get("tool_calls", []),  # Separate tool calls
        tool_call_results=tool_call_results,
        analysis=analysis
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 
