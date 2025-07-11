from flask import Flask, render_template, request, redirect, url_for, session, flash
import secrets
import re
from datetime import datetime
import time
import asyncio
from shardguard.core.coordination import CoordinationService
from shardguard.core.planning import PlanningLLM
from shardguard.core.mcp_integration import MCPClient

planner = PlanningLLM()
coordinator = CoordinationService(planner)

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
    """Process prompt submission and show results"""
    if not check_authentication():
        flash('Please log in to submit prompts', 'error')
        return redirect(url_for('login'))
    
    prompt = request.form.get('prompt', '').strip()
    
    if not prompt:
        flash('Please enter a prompt', 'error')
        return redirect(url_for('dashboard'))
    

 
    plan = asyncio.run(coordinator.handle_prompt(prompt))
    print("DEBUG: Plan from backend:", plan)
  
    used_tools = set()
    for sub in plan.sub_prompts:
        used_tools.update(sub.suggested_tools)
    used_tools = list(used_tools)

    # Extract unique MCP servers from the tools
    used_servers = set()
    for tool in used_tools:
        server = tool.split(' - ')[0] if ' - ' in tool else tool
        used_servers.add(server)
    used_servers = list(used_servers)
    num_servers_triggered = len(used_servers)

    # Use backend results for risk level
    risk_level = 'HIGH' if used_tools else 'SAFE'
    risk_color = 'red' if used_tools else 'green'

    mcp_client = MCPClient()
    tools_by_server = asyncio.run(mcp_client.list_tools())
    total_mcps = sum(len(tools) for tools in tools_by_server.values())

    return render_template(
        'results.html',
        prompt=prompt,
        risk_level=risk_level,
        risk_color=risk_color,
        username=session['username'],
        total_mcps=total_mcps,
        used_servers=used_servers,
        num_servers_triggered=num_servers_triggered
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 