"""
Tests for YAML MCP server factory functionality.
"""

import pytest
import asyncio
import os
from yaml_mcp_server_factory import YAMLMCPServerFactory, get_factory


class TestYAMLMCPServerFactory:
    """Test YAML MCP server factory functionality."""
    
    def test_factory_initialization(self, temp_yaml_dir):
        """Test factory initialization with valid directory."""
        factory = YAMLMCPServerFactory(temp_yaml_dir)
        assert factory.yaml_directory == temp_yaml_dir
        assert "test-server" in factory.server_configs
    
    def test_get_available_servers(self, yaml_factory):
        """Test getting available servers."""
        servers = yaml_factory.get_available_servers()
        assert "test-server" in servers
        assert servers["test-server"] == "A test server"
    
    def test_get_server_config(self, yaml_factory):
        """Test getting server configuration."""
        config = yaml_factory.get_server_config("test-server")
        assert config["server"] == "test-server"
        assert config["description"] == "A test server"
        assert len(config["tools"]) == 1
        assert config["tools"][0]["name"] == "test_tool"
    
    def test_list_all_tools(self, yaml_factory):
        """Test listing all tools from all servers."""
        tools_by_server = yaml_factory.list_all_tools()
        assert "test-server" in tools_by_server
        assert len(tools_by_server["test-server"]) == 1
        assert tools_by_server["test-server"][0].name == "test_tool"
    
    def test_create_server_instance(self, yaml_factory):
        """Test creating a server instance."""
        server = yaml_factory.create_server_instance("test-server")
        assert server.name == "test-server"
    
    def test_create_server_instance_invalid(self, yaml_factory):
        """Test creating server instance with invalid server name."""
        with pytest.raises(ValueError, match="not found in YAML configurations"):
            yaml_factory.create_server_instance("invalid-server")
    
    def test_convert_type_to_json_schema(self, yaml_factory):
        """Test type conversion to JSON schema."""
        assert yaml_factory._convert_type_to_json_schema("string") == "string"
        assert yaml_factory._convert_type_to_json_schema("number") == "number"
        assert yaml_factory._convert_type_to_json_schema("boolean") == "boolean"
        assert yaml_factory._convert_type_to_json_schema("null") == "null"
        assert yaml_factory._convert_type_to_json_schema("array") == "array"
        assert yaml_factory._convert_type_to_json_schema("unknown") == "string"
    
    def test_generate_simulated_response(self, yaml_factory):
        """Test simulated response generation."""
        arguments = {"param1": "value1", "param2": 42}
        response = yaml_factory._generate_simulated_response("test-server", "test_tool", arguments)
        assert "TEST-SERVER" in response.upper()
        assert "test_tool" in response
        assert "param1=value1" in response
        assert "param2=42" in response
    
    def test_generate_simulated_response_nuke_server(self, yaml_factory):
        """Test simulated response generation for nuke server."""
        arguments = {"launch_code": "12345", "commander_id": "commander"}
        response = yaml_factory._generate_simulated_response("nuke-operations", "verify_launch_code", arguments)
        assert "NUKE PoC" in response
        assert "verify_launch_code" in response
    
    def test_generate_simulated_response_water_server(self, yaml_factory):
        """Test simulated response generation for water server."""
        arguments = {"reservoir_id": "res1", "target_level": 100}
        response = yaml_factory._generate_simulated_response("watersupply-server", "control_reservoir_level", arguments)
        assert "WATER PoC" in response
        assert "control_reservoir_level" in response
    
    def test_generate_simulated_response_blockchain_server(self, yaml_factory):
        """Test simulated response generation for blockchain server."""
        arguments = {"wallet_address": "0x123", "exploit_type": "phishing"}
        response = yaml_factory._generate_simulated_response("blockchain-operations", "exploit_wallet_interface", arguments)
        assert "BLOCKCHAIN PoC" in response
        assert "exploit_wallet_interface" in response
    
    def test_generate_simulated_response_global_server(self, yaml_factory):
        """Test simulated response generation for global server."""
        arguments = {"target_id": "person1", "tracking_method": "GPS"}
        response = yaml_factory._generate_simulated_response("global-operations", "track_individual", arguments)
        assert "GLOBAL PoC" in response
        assert "track_individual" in response
    
    def test_generate_simulated_response_unknown_server(self, yaml_factory):
        """Test simulated response generation for unknown server."""
        arguments = {"param1": "value1"}
        response = yaml_factory._generate_simulated_response("unknown-server", "unknown_tool", arguments)
        assert "UNKNOWN-SERVER PoC" in response
        assert "unknown_tool" in response


class TestYAMLMCPServerFactoryIntegration:
    """Test YAML factory integration with actual YAML files."""
    
    def test_factory_with_real_yaml_files(self):
        """Test factory with the actual YAML server files."""
        factory = YAMLMCPServerFactory("mcp_servers")
        
        # Test that servers are loaded (without depending on specific names)
        servers = factory.get_available_servers()
        assert isinstance(servers, dict)
        assert len(servers) > 0
        
        # Test that each server has a description
        for server_name, description in servers.items():
            assert isinstance(server_name, str)
            assert isinstance(description, str)
            assert len(server_name) > 0
            assert len(description) > 0
        
        # Test that tools are properly loaded
        tools_by_server = factory.list_all_tools()
        assert isinstance(tools_by_server, dict)
        assert len(tools_by_server) > 0
        
        # Test that each server has tools
        for server_name, tools in tools_by_server.items():
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            # Test that each tool has required attributes
            for tool in tools:
                assert hasattr(tool, 'name')
                assert hasattr(tool, 'description')
                assert isinstance(tool.name, str)
                assert isinstance(tool.description, str)
                assert len(tool.name) > 0
                assert len(tool.description) > 0
    
    def test_server_configs_structure(self):
        """Test that server configurations have proper structure."""
        factory = YAMLMCPServerFactory("mcp_servers")
        
        # Test that we can get server configs
        for server_name in factory.get_available_servers().keys():
            config = factory.get_server_config(server_name)
            assert isinstance(config, dict)
            assert "server" in config
            assert "description" in config
            assert "tools" in config
            assert config["server"] == server_name
            assert isinstance(config["tools"], list)
            assert len(config["tools"]) > 0
    
    def test_tool_schema_generation(self):
        """Test that tool schemas are properly generated."""
        factory = YAMLMCPServerFactory("mcp_servers")
        tools_by_server = factory.list_all_tools()
        
        for server_name, tools in tools_by_server.items():
            for tool in tools:
                # Test that tools have proper structure
                assert hasattr(tool, 'name')
                assert hasattr(tool, 'description')
                assert hasattr(tool, 'inputSchema')
                
                # Test that inputSchema is properly structured
                if tool.inputSchema:
                    assert isinstance(tool.inputSchema, dict)
                    assert "type" in tool.inputSchema
                    assert tool.inputSchema["type"] == "object"
                    assert "properties" in tool.inputSchema
                    assert "required" in tool.inputSchema
    
    def test_large_directory_handling(self):
        """Test that factory can handle a large directory with many servers."""
        yaml_dir = "tests/fake_mcp_server_yaml/pass_dir3"
        if os.path.exists(yaml_dir):
            factory = YAMLMCPServerFactory(yaml_dir)
            
            # Should have multiple servers
            servers = factory.get_available_servers()
            assert len(servers) > 5
            
            # Test that each server has tools
            tools_by_server = factory.list_all_tools()
            assert len(tools_by_server) > 5
            
            for server_name, tools in tools_by_server.items():
                assert isinstance(tools, list)
                assert len(tools) > 0
                
                # Test that each tool has required attributes
                for tool in tools:
                    assert hasattr(tool, 'name')
                    assert hasattr(tool, 'description')
                    assert isinstance(tool.name, str)
                    assert isinstance(tool.description, str)
                    assert len(tool.name) > 0
                    assert len(tool.description) > 0


class TestGlobalFactory:
    """Test the global factory instance."""
    
    def test_get_factory(self):
        """Test getting the global factory instance."""
        factory1 = get_factory()
        factory2 = get_factory()
        assert factory1 is factory2  # Should be the same instance
    
    def test_global_factory_servers(self):
        """Test that global factory loads servers correctly."""
        factory = get_factory()
        servers = factory.get_available_servers()
        
        # Test that servers are loaded (without depending on specific names)
        assert isinstance(servers, dict)
        assert len(servers) > 0
        
        # Test that each server has a description
        for server_name, description in servers.items():
            assert isinstance(server_name, str)
            assert isinstance(description, str)
            assert len(server_name) > 0
            assert len(description) > 0


@pytest.mark.asyncio
class TestAsyncFunctionality:
    """Test async functionality of the factory."""
    
    async def test_handle_tool_call(self, yaml_factory):
        """Test handling tool calls."""
        arguments = {"param1": "value1", "param2": 42}
        tools = yaml_factory.list_all_tools()["test-server"]
        
        result = await yaml_factory._handle_tool_call("test-server", "test_tool", arguments, tools)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "test-server" in result[0].text.upper()
        assert "test_tool" in result[0].text
    
    async def test_handle_tool_call_invalid_tool(self, yaml_factory):
        """Test handling tool calls with invalid tool name."""
        arguments = {"param1": "value1"}
        tools = yaml_factory.list_all_tools()["test-server"]
        
        with pytest.raises(ValueError, match="Unknown tool"):
            await yaml_factory._handle_tool_call("test-server", "invalid_tool", arguments, tools) 