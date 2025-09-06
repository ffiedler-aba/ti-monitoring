#!/usr/bin/env python3
"""
Test script for the OTP notification system.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mylibrary import *

def test_otp_system():
    """Test the OTP system functionality"""
    print("Testing OTP notification system...")
    
    try:
        # Initialize database schema
        print("Initializing database schema...")
        init_otp_database_schema()
        print("Database schema initialized successfully!")
        
        # Test user creation
        print("Testing user creation...")
        email = "test@example.com"
        user_id = create_user(email)
        if user_id:
            print(f"User created successfully with ID: {user_id}")
        else:
            print("Failed to create user")
            return False
            
        # Test OTP generation
        print("Testing OTP generation...")
        otp, otp_id = generate_otp_for_user(user_id)
        if otp and otp_id:
            print(f"OTP generated successfully: {otp} (ID: {otp_id})")
        else:
            print("Failed to generate OTP")
            return False
            
        # Test OTP validation
        print("Testing OTP validation...")
        if validate_otp(user_id, otp):
            print("OTP validation successful!")
        else:
            print("OTP validation failed")
            return False
            
        # Test profile creation
        print("Testing profile creation...")
        profile_id = create_notification_profile(
            user_id, 
            "Test Profile", 
            "whitelist", 
            ["CI-000001", "CI-000002"], 
            ["mailto://test@example.com"], 
            False, 
            None
        )
        if profile_id:
            print(f"Profile created successfully with ID: {profile_id}")
        else:
            print("Failed to create profile")
            return False
            
        print("All tests passed!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False

if __name__ == "__main__":
    if test_otp_system():
        print("OTP system test completed successfully!")
        sys.exit(0)
    else:
        print("OTP system test failed!")
        sys.exit(1)