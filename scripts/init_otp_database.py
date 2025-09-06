#!/usr/bin/env python3
"""
Script to initialize the OTP database schema for the multi-user notification system.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mylibrary import init_otp_database_schema

def main():
    """Initialize the OTP database schema"""
    print("Initializing OTP database schema...")
    try:
        init_otp_database_schema()
        print("OTP database schema initialized successfully!")
    except Exception as e:
        print(f"Error initializing OTP database schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()