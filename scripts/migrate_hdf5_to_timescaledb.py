#!/usr/bin/env python3
"""
Migration script to move from HDF5-only to TimescaleDB-only setup.

This script helps existing installations migrate their HDF5 data to TimescaleDB
and update their configuration for the new TimescaleDB-only approach.

Usage:
    python scripts/migrate_hdf5_to_timescaledb.py [--config config.yaml] [--hdf5-file data/data.hdf5] [--dry-run]
"""

import argparse
import os
import sys
import yaml
import json
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import mylibrary
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mylibrary import (
    load_config, 
    init_timescaledb_schema, 
    get_db_conn,
    ingest_hdf5_to_timescaledb,
    update_ci_metadata
)

def backup_config(config_path):
    """Create a backup of the current configuration file."""
    backup_path = f"{config_path}.backup.{int(time.time())}"
    print(f"📋 Creating config backup: {backup_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return backup_path

def update_config_for_timescaledb_only(config_path, dry_run=False):
    """Update configuration to remove HDF5 references and ensure TimescaleDB is enabled."""
    print(f"🔧 Updating configuration: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Remove HDF5 file reference
    if 'core' in config and 'file_name' in config['core']:
        old_file_name = config['core']['file_name']
        print(f"   Removing HDF5 file reference: {old_file_name}")
        del config['core']['file_name']
    
    # Ensure TimescaleDB is enabled
    if 'core' not in config:
        config['core'] = {}
    if 'timescaledb' not in config['core']:
        config['core']['timescaledb'] = {}
    
    config['core']['timescaledb']['enabled'] = True
    print(f"   Ensuring TimescaleDB is enabled: {config['core']['timescaledb']['enabled']}")
    
    if not dry_run:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print(f"✅ Configuration updated successfully")
    else:
        print(f"🔍 DRY RUN: Would update configuration")
    
    return config

def migrate_hdf5_data(hdf5_path, dry_run=False):
    """Migrate HDF5 data to TimescaleDB."""
    if not os.path.exists(hdf5_path):
        print(f"⚠️  HDF5 file not found: {hdf5_path}")
        return 0
    
    print(f"📊 Migrating HDF5 data: {hdf5_path}")
    
    if not dry_run:
        # Initialize TimescaleDB schema
        init_timescaledb_schema()
        
        # Migrate data
        migrated_rows = ingest_hdf5_to_timescaledb(hdf5_path)
        print(f"✅ Migrated {migrated_rows} rows to TimescaleDB")
        return migrated_rows
    else:
        # Dry run - just check file size
        file_size = os.path.getsize(hdf5_path)
        print(f"🔍 DRY RUN: Would migrate HDF5 file ({file_size} bytes)")
        return 0

def create_migration_report(config_path, hdf5_path, migrated_rows, backup_path):
    """Create a migration report."""
    report = {
        "migration_date": datetime.now().isoformat(),
        "config_file": config_path,
        "hdf5_file": hdf5_path,
        "migrated_rows": migrated_rows,
        "backup_config": backup_path,
        "status": "completed" if migrated_rows > 0 else "no_data",
        "next_steps": [
            "Restart the application containers",
            "Verify TimescaleDB data in the web interface",
            "Remove HDF5 file after verification (optional)",
            "Update any custom scripts to use TimescaleDB"
        ]
    }
    
    report_path = f"migration_report_{int(time.time())}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Migration report created: {report_path}")
    return report_path

def main():
    parser = argparse.ArgumentParser(description='Migrate from HDF5 to TimescaleDB-only setup')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('--hdf5-file', default='data/data.hdf5', help='HDF5 file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    print("🚀 TI-Monitoring HDF5 to TimescaleDB Migration")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)
    
    # Load current config
    try:
        config = load_config()
        print(f"✅ Configuration loaded: {args.config}")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)
    
    # Check TimescaleDB configuration
    tsdb_config = config.get('core', {}).get('timescaledb', {})
    if not tsdb_config.get('enabled', False):
        print("⚠️  TimescaleDB is not enabled in configuration")
        print("   The migration will enable TimescaleDB automatically")
    
    print()
    
    # Step 1: Backup configuration
    backup_path = backup_config(args.config)
    
    # Step 2: Update configuration
    updated_config = update_config_for_timescaledb_only(args.config, args.dry_run)
    
    # Step 3: Migrate HDF5 data
    migrated_rows = migrate_hdf5_data(args.hdf5_file, args.dry_run)
    
    # Step 4: Create migration report
    report_path = create_migration_report(args.config, args.hdf5_file, migrated_rows, backup_path)
    
    print()
    print("🎉 Migration completed!")
    print("=" * 50)
    print(f"📊 Migrated rows: {migrated_rows}")
    print(f"📋 Config backup: {backup_path}")
    print(f"📄 Report: {report_path}")
    print()
    print("Next steps:")
    print("1. Restart your Docker containers: docker compose restart")
    print("2. Verify data in the web interface")
    print("3. Remove HDF5 file after verification (optional)")
    print("4. Update any custom scripts to use TimescaleDB")

if __name__ == "__main__":
    main()
