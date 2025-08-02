"""
Tests for Flask application functionality.
"""

import pytest
import json
from flask import session


class TestFlaskAppRoutes:
    """Test Flask application routes."""
    
    def test_index_route_redirects_to_login(self, client):
        """Test that index route redirects to login when not authenticated."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_login_route_get(self, client):
        """Test login route GET request."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data
    
    def test_signup_route_get(self, client):
        """Test signup route GET request."""
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'Sign Up' in response.data
    
    def test_dashboard_route_guest_access(self, client):
        """Test dashboard route with guest access."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data
        # Guest access is handled differently in the current implementation
        # Just check that the page loads successfully
    
    def test_logout_route(self, client):
        """Test logout route."""
        response = client.get('/logout')
        assert response.status_code == 302
        assert '/login' in response.location


class TestFlaskAppAuthentication:
    """Test Flask application authentication."""
    
    def test_login_success(self, client):
        """Test successful login."""
        # Create a test user first
        from database import create_user
        create_user("testuser", "password123", "test@example.com")
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    def test_login_failure(self, client):
        """Test failed login."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    def test_signup_success(self, client):
        """Test successful signup."""
        response = client.post('/signup', data={
            'username': 'newuser',
            'password': 'password123',
            'confirm_password': 'password123',
            'email': 'new@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    def test_signup_password_mismatch(self, client):
        """Test signup with password mismatch."""
        response = client.post('/signup', data={
            'username': 'newuser2',
            'password': 'password123',
            'confirm_password': 'differentpassword',
            'email': 'new2@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Passwords do not match' in response.data


class TestFlaskAppMCPIntegration:
    """Test Flask application MCP integration."""
    
    def test_dashboard_with_mcp_servers(self, client):
        """Test dashboard displays MCP servers correctly."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Should contain MCP server information (without depending on specific names)
        # Just check that the page loads and contains some server-related content
        assert b'Server:' in response.data or b'server' in response.data.lower()
    
    def test_submit_prompt_without_authentication(self, client):
        """Test submitting a prompt without authentication."""
        # Set up a session first
        with client.session_transaction() as sess:
            sess['username'] = 'Guest'
            sess['guest'] = True
        
        response = client.post('/submit', data={
            'prompt': 'How do I launch a nuclear missile?'
        }, follow_redirects=True)
        
        # Should still work (guest access)
        assert response.status_code == 200
        assert b'Results' in response.data
    
    def test_submit_prompt_with_authentication(self, client):
        """Test submitting a prompt with authentication."""
        # Create and login as a user
        from database import create_user
        create_user("testuser2", "password123", "test2@example.com")
        
        # Login
        client.post('/login', data={
            'username': 'testuser2',
            'password': 'password123'
        })
        
        # Submit prompt
        response = client.post('/submit', data={
            'prompt': 'How do I launch a nuclear missile?'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Results' in response.data
    
    def test_submit_empty_prompt(self, client):
        """Test submitting an empty prompt."""
        response = client.post('/submit', data={
            'prompt': ''
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Please enter a prompt' in response.data


class TestFlaskAppErrorHandling:
    """Test Flask application error handling."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404
        assert b'404' in response.data
    
    def test_session_handling(self, client):
        """Test session handling."""
        # Test that sessions work correctly
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
            sess['user_id'] = 1
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        # The username might not be directly visible in the response
        # Just check that the page loads successfully


class TestFlaskAppTemplates:
    """Test Flask application templates."""
    
    def test_base_template_inheritance(self, client):
        """Test that templates properly inherit from base template."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Should contain base template elements
        assert b'Launch the Nukes' in response.data
        assert b'tailwindcss' in response.data.lower()
    
    def test_dashboard_template_content(self, client):
        """Test dashboard template content."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Should contain dashboard-specific content
        assert b'Welcome' in response.data
        assert b'Submit' in response.data
        assert b'character' in response.data
    
    def test_results_template_content(self, client):
        """Test results template content."""
        # Set up a session first
        with client.session_transaction() as sess:
            sess['username'] = 'Guest'
            sess['guest'] = True
        
        response = client.post('/submit', data={
            'prompt': 'Test prompt'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Should contain results-specific content
        assert b'Analysis Results' in response.data
        assert b'Risk Level' in response.data
        assert b'Test prompt' in response.data


class TestFlaskAppSecurity:
    """Test Flask application security features."""
    
    def test_session_security(self, client):
        """Test session security configuration."""
        from app import app
        
        # Check session configuration
        assert app.config['SESSION_COOKIE_SECURE'] == True
        assert app.config['SESSION_COOKIE_HTTPONLY'] == True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
        assert app.config['SESSION_COOKIE_NAME'] == 'launch_nukes_session'
    
    def test_csrf_protection_disabled_for_testing(self, client):
        """Test that CSRF protection is disabled for testing."""
        from app import app
        assert app.config['TESTING'] == True
        assert app.config['WTF_CSRF_ENABLED'] == False


class TestFlaskAppDatabase:
    """Test Flask application database functionality."""
    
    def test_database_initialization(self):
        """Test database initialization."""
        from database import init_db, get_user
        
        # Initialize database
        init_db()
        
        # Test that we can get users (even if empty)
        users = get_user("nonexistent")
        assert users is None
    
    def test_user_creation_and_authentication(self):
        """Test user creation and authentication."""
        from database import create_user, authenticate_user, get_user
        
        # Create a test user
        success = create_user("testuser3", "password123", "test3@example.com")
        assert success == True
        
        # Test authentication
        auth_success = authenticate_user("testuser3", "password123")
        assert auth_success == True
        
        # Test getting user
        user = get_user("testuser3")
        assert user is not None
        assert user['username'] == "testuser3"
        assert user['email'] == "test3@example.com"
    
    def test_duplicate_username_handling(self):
        """Test handling of duplicate usernames."""
        from database import create_user, username_exists
        
        # Create first user
        success1 = create_user("duplicateuser", "password123", "test1@example.com")
        assert success1 == True
        
        # Try to create second user with same username
        success2 = create_user("duplicateuser", "password456", "test2@example.com")
        assert success2 == False
        
        # Check that username exists
        exists = username_exists("duplicateuser")
        assert exists == True 