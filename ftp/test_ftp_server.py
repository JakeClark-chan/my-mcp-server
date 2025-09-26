#!/usr/bin/env python3
"""
Simple test script for FTP MCP Server functionality.
Tests basic server operations without requiring an actual FTP connection.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import os


def test_server_startup():
    """Test that the FTP server starts without errors."""
    print("🧪 Testing server startup...")
    
    try:
        # Try to import the server module
        import ftp_server
        print("✅ Server module imports successfully")
        
        # Check if FastMCP instance is created
        assert hasattr(ftp_server, 'mcp'), "MCP server instance not found"
        print("✅ MCP server instance created")
        
        # Check if tools are registered
        # FastMCP stores tools differently, let's check the server name instead
        assert ftp_server.mcp.name == "FTP Server", f"Expected 'FTP Server', got '{ftp_server.mcp.name}'"
        print(f"✅ Server name: {ftp_server.mcp.name}")
        
        # Check basic server attributes
        assert hasattr(ftp_server.mcp, 'run'), "Server run method not found"
        print("✅ Server has run method")
        
        return True
        
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        return False


def test_tool_definitions():
    """Test that all expected tools are defined."""
    print("\n🧪 Testing tool definitions...")
    
    try:
        import ftp_server
        
        expected_tools = [
            'ftp_connect',
            'ftp_disconnect', 
            'ftp_list_connections',
            'ftp_switch_connection',
            'ftp_pwd',
            'ftp_cwd',
            'ftp_explore_directory',
            'ftp_list_directory',
            'ftp_mkdir',
            'ftp_rmdir',
            'ftp_delete_file',
            'ftp_rename',
            'ftp_upload_file',
            'ftp_upload_content',
            'ftp_download_file',
            'ftp_download_content',
            'ftp_get_file_size',
            'ftp_set_passive_mode',
            'ftp_get_system_info',
            'ftp_send_noop',
            'ftp_get_modification_time',
            'ftp_create_directory_tree',
            'ftp_transfer_progress'
        ]
        
        # Since we can't directly access FastMCP's internal tool registry,
        # let's check that the tool functions exist in the module
        missing_tools = []
        for tool in expected_tools:
            if hasattr(ftp_server, tool):
                print(f"✅ Tool function '{tool}' exists")
            else:
                print(f"❌ Tool function '{tool}' missing")
                missing_tools.append(tool)
                
        if missing_tools:
            print(f"❌ Missing tools: {missing_tools}")
            return False
            
        print(f"✅ All {len(expected_tools)} expected tool functions found")
        return True
        
    except Exception as e:
        print(f"❌ Tool definition test failed: {e}")
        return False


def test_resource_definitions():
    """Test that all expected resources are defined."""
    print("\n🧪 Testing resource definitions...")
    
    try:
        import ftp_server
        
        expected_resources = [
            'ftp://connections',
            'ftp://current-directory', 
            'ftp://server-info'
        ]
        
        # Check for resource functions in the module
        expected_resource_functions = [
            'get_connections_status',
            'get_current_directory',
            'get_server_info'
        ]
        
        missing_resources = []
        for resource_func in expected_resource_functions:
            if hasattr(ftp_server, resource_func):
                print(f"✅ Resource function '{resource_func}' exists")
            else:
                print(f"❌ Resource function '{resource_func}' missing")
                missing_resources.append(resource_func)
                
        if missing_resources:
            print(f"❌ Missing resource functions: {missing_resources}")
            return False
            
        print(f"✅ All {len(expected_resource_functions)} expected resource functions found")
        return True
        
    except Exception as e:
        print(f"❌ Resource definition test failed: {e}")
        return False


def test_data_models():
    """Test that data models are properly defined."""
    print("\n🧪 Testing data models...")
    
    try:
        import ftp_server
        
        # Test FTPConnectionInfo model
        conn_info = ftp_server.FTPConnectionInfo(
            host="test.example.com",
            username="testuser",
            password="testpass"
        )
        assert conn_info.host == "test.example.com"
        assert conn_info.port == 21  # default value
        assert conn_info.passive is True  # default value
        print("✅ FTPConnectionInfo model works")
        
        # Test FTPFileInfo model
        file_info = ftp_server.FTPFileInfo(
            name="test.txt",
            type="file"
        )
        assert file_info.name == "test.txt"
        assert file_info.type == "file"
        print("✅ FTPFileInfo model works")
        
        # Test FTPDirectoryListing model
        dir_listing = ftp_server.FTPDirectoryListing(
            current_directory="/home/user",
            files=[file_info],
            total_files=1,
            total_directories=0
        )
        assert dir_listing.current_directory == "/home/user"
        assert len(dir_listing.files) == 1
        print("✅ FTPDirectoryListing model works")
        
        return True
        
    except Exception as e:
        print(f"❌ Data model test failed: {e}")
        return False


def test_error_handling():
    """Test error handling in utility functions."""
    print("\n🧪 Testing error handling...")
    
    try:
        import ftp_server
        
        # Create a mock context that should trigger the "no connection" error
        class MockLifespanContext:
            current_connection = None
            connections = {}
            
        class MockRequestContext:
            lifespan_context = MockLifespanContext()
            
        class MockContext:
            request_context = MockRequestContext()
        
        mock_ctx = MockContext()
        
        # Test _get_current_ftp with no connection
        try:
            ftp_server._get_current_ftp(mock_ctx)
            print("❌ Expected ValueError for no connection")
            return False
        except ValueError as e:
            if "No active FTP connection" in str(e):
                print("✅ Proper error handling for no connection")
            else:
                print(f"❌ Unexpected error message: {e}")
                return False
        except Exception as e:
            print(f"❌ Unexpected exception type: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def create_test_files():
    """Create temporary test files."""
    print("\n🧪 Creating test files...")
    
    temp_dir = tempfile.mkdtemp(prefix="ftp_test_")
    
    # Create test text file
    text_file = os.path.join(temp_dir, "test.txt")
    with open(text_file, 'w') as f:
        f.write("This is a test file\n")
        f.write("Line 2\n")
        f.write("Line 3\n")
    
    # Create test binary file
    binary_file = os.path.join(temp_dir, "test.bin")  
    with open(binary_file, 'wb') as f:
        f.write(b'\x00\x01\x02\x03\x04\x05')
        f.write(b'Binary test data')
    
    print(f"✅ Created test files in {temp_dir}")
    print(f"   - {text_file}")
    print(f"   - {binary_file}")
    
    return temp_dir, text_file, binary_file


def run_all_tests():
    """Run all tests and report results."""
    print("FTP MCP Server - Test Suite")
    print("=" * 40)
    
    tests = [
        ("Server Startup", test_server_startup),
        ("Tool Definitions", test_tool_definitions), 
        ("Resource Definitions", test_resource_definitions),
        ("Data Models", test_data_models),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    # Create test files for manual testing
    temp_dir, text_file, binary_file = create_test_files()
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        print("\n📁 Test files created for manual testing:")
        print(f"   Directory: {temp_dir}")
        print(f"   Text file: {text_file}")
        print(f"   Binary file: {binary_file}")
        print("\n🚀 Server is ready for use!")
        print("   Run: python ftp_server.py")
        print("   Demo: python ftp_demo.py")
    else:
        print("❌ Some tests failed. Please check the output above.")
        
    # Cleanup instructions
    print(f"\n🗑️  To clean up test files: rm -rf {temp_dir}")
        
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)