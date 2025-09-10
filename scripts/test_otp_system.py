#!/usr/bin/env python3
"""
Test script for the OTP notification system.
"""

import sys
import os
import pytest

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mylibrary import *


def test_otp_system():
    """Test the OTP system functionality"""
    # Nur im Docker/CI mit verfügbarer DB ausführen
    if os.environ.get("RUN_DB_TESTS") != "1":
        pytest.skip("DB-Integrationstest übersprungen (RUN_DB_TESTS!=1)")

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
        assert user_id, "Failed to create user"
        print(f"User created successfully with ID: {user_id}")

        # Test OTP generation
        print("Testing OTP generation...")
        otp, otp_id = generate_otp_for_user(user_id)
        assert otp and otp_id, "Failed to generate OTP"
        print(f"OTP generated successfully: {otp} (ID: {otp_id})")

        # Test OTP validation
        print("Testing OTP validation...")
        assert validate_otp(user_id, otp) is True, "OTP validation failed"
        print("OTP validation successful!")

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
        assert profile_id, "Failed to create profile"
        print(f"Profile created successfully with ID: {profile_id}")

        print("All tests passed!")

    except Exception as e:
        print(f"Error during testing: {e}")
        raise


if __name__ == "__main__":
    try:
        test_otp_system()
        print("OTP system test completed successfully!")
        sys.exit(0)
    except Exception:
        print("OTP system test failed!")
        sys.exit(1)