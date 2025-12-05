#!/usr/bin/env python3
"""
Forward-fill missing device data in historical time buckets.

This script identifies time buckets where devices are missing and inserts
forward-filled values (last known value) to stabilize historical charts.

WARNING: This creates "estimated" data points. Use with caution.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from collections import defaultdict

def get_db_connection():
    """Create PostgreSQL/TimescaleDB connection"""
    host = os.getenv("POSTGRES_HOST", "timescaledb")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "gos_rem")
    user = os.getenv("POSTGRES_USER", "gos")
    password = os.getenv("POSTGRES_PASSWORD", "")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None


def get_all_devices(conn):
    """Get list of all devices that have data"""
    cursor = conn.cursor()
    query = """
    SELECT DISTINCT alias 
    FROM gos_rem 
    ORDER BY alias
    """
    cursor.execute(query)
    devices = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return devices


def get_time_range(conn):
    """Get the time range of data in the database"""
    cursor = conn.cursor()
    query = """
    SELECT 
        MIN(time) AS start_time,
        MAX(time) AS end_time
    FROM gos_rem
    """
    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    return result[0], result[1]


def find_gaps(conn, interval_minutes=1):
    """Find time buckets where devices are missing"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all devices
    devices = get_all_devices(conn)
    
    # Get time range
    start_time, end_time = get_time_range(conn)
    
    print(f"Analyzing data from {start_time} to {end_time}")
    print(f"Looking for gaps in {len(devices)} devices with {interval_minutes}-minute buckets")
    
    # Find all time buckets that should exist
    query = """
    SELECT 
        time_bucket(%s, time) AS bucket,
        alias,
        COUNT(*) AS reading_count,
        AVG(power_watts) AS avg_power
    FROM gos_rem
    WHERE time >= %s AND time <= %s
    GROUP BY time_bucket(%s, time), alias
    ORDER BY bucket, alias
    """
    
    interval_str = f"{interval_minutes} minute"
    cursor.execute(query, (interval_str, start_time, end_time, interval_str))
    results = cursor.fetchall()
    cursor.close()
    
    # Organize by time bucket - use datetime objects as keys
    buckets = {}
    bucket_times = []
    for row in results:
        bucket = row['bucket']
        # Store as datetime object
        if bucket not in buckets:
            buckets[bucket] = {}
            bucket_times.append(bucket)
        buckets[bucket][row['alias']] = row['avg_power']
    
    # Sort bucket times
    bucket_times.sort()
    
    # Find gaps: buckets where not all devices have data
    gaps = []
    expected_device_count = len(devices)
    
    for bucket_time in bucket_times:
        device_data = buckets[bucket_time]
        present_devices = set(device_data.keys())
        missing_devices = set(devices) - present_devices
        
        if missing_devices:
            gaps.append({
                'bucket': bucket_time,  # Keep as datetime object
                'missing_devices': list(missing_devices),
                'present_devices': list(present_devices)
            })
    
    print(f"Found {len(gaps)} time buckets with missing devices")
    return gaps, devices, start_time, end_time


def get_last_known_values(conn, device, before_time, max_lookback_minutes=60):
    """Get the last known value for a device before a given time"""
    cursor = conn.cursor()
    
    lookback = before_time - timedelta(minutes=max_lookback_minutes)
    
    query = """
    SELECT 
        time,
        power_watts,
        alias
    FROM gos_rem
    WHERE alias = %s
      AND time < %s
      AND time >= %s
    ORDER BY time DESC
    LIMIT 1
    """
    
    cursor.execute(query, (device, before_time, lookback))
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'time': result[0],
            'power_watts': result[1],
            'alias': result[2]
        }
    return None


def forward_fill_gaps(conn, gaps, devices, dry_run=True):
    """Fill gaps with forward-filled values (last known value)"""
    cursor = conn.cursor()
    
    inserts = []
    filled_count = 0
    
    for gap in gaps:
        bucket_time = gap['bucket']  # Already a datetime object
        
        for device in gap['missing_devices']:
            # Get last known value before this bucket
            last_known = get_last_known_values(conn, device, bucket_time)
            
            if last_known:
                # Use the last known value
                inserts.append({
                    'time': bucket_time,
                    'alias': device,
                    'power_watts': last_known['power_watts'],
                    'source': 'forward_filled',
                    'last_known_time': last_known['time']
                })
                filled_count += 1
            else:
                print(f"  ⚠️  No previous value found for {device} at {bucket_time}")
    
    if dry_run:
        print(f"\n[DRY RUN] Would insert {filled_count} forward-filled data points")
        if inserts:
            print(f"\nFirst 10 inserts:")
            for i, insert in enumerate(inserts[:10]):
                print(f"  {i+1}. {insert['alias']} at {insert['time']}: {insert['power_watts']:.2f}W (from {insert['last_known_time']})")
        return 0
    
    # Actually insert the data
    if inserts:
        print(f"\nInserting {filled_count} forward-filled data points...")
        
        values = []
        for insert in inserts:
            values.append((
                insert['time'],
                insert['alias'],
                insert['power_watts']
            ))
        
        from psycopg2.extras import execute_values
        execute_values(
            cursor,
            "INSERT INTO gos_rem (time, alias, power_watts) VALUES %s ON CONFLICT DO NOTHING",
            values
        )
        
        conn.commit()
        print(f"✅ Inserted {filled_count} forward-filled data points")
    else:
        print("No data points to insert")
    
    cursor.close()
    return filled_count


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Forward-fill missing device data in historical time buckets')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be filled without actually inserting')
    parser.add_argument('--interval', type=int, default=1, help='Time bucket interval in minutes (default: 1)')
    parser.add_argument('--max-lookback', type=int, default=60, help='Maximum minutes to look back for last known value (default: 60)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Forward-Fill Historical Data Tool")
    print("=" * 60)
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be modified")
    else:
        print("⚠️  LIVE MODE - Will insert forward-filled data points")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled")
            return
    print()
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to database")
        sys.exit(1)
    
    try:
        # Find gaps
        gaps, devices, start_time, end_time = find_gaps(conn, args.interval)
        
        if not gaps:
            print("✅ No gaps found - all devices have data for all time buckets")
            return
        
        print(f"\nGap summary:")
        print(f"  Time buckets with gaps: {len(gaps)}")
        
        # Show sample gaps
        if gaps:
            print(f"\nFirst 5 gaps:")
            for gap in gaps[:5]:
                bucket_str = gap['bucket'].isoformat() if hasattr(gap['bucket'], 'isoformat') else str(gap['bucket'])
                missing_preview = ', '.join(gap['missing_devices'][:3])
                if len(gap['missing_devices']) > 3:
                    missing_preview += f" (+{len(gap['missing_devices']) - 3} more)"
                print(f"  {bucket_str}: Missing {len(gap['missing_devices'])} devices ({missing_preview})")
        
        # Forward-fill gaps
        filled = forward_fill_gaps(conn, gaps, devices, dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"\n[DRY RUN] To actually fill gaps, run without --dry-run flag")
        else:
            print(f"\n✅ Forward-fill complete: {filled} data points inserted")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()

