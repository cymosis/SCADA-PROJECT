"""
Load SWaT Attack Data into InfluxDB
====================================

This script loads the July 19, 2019 SWaT dataset which contains
both normal operation and 6 cyber attacks.

Attack periods (from PDF documentation):
- Normal: 12:35 PM - 2:50 PM (GMT+8)
- Attacks: 3:08 PM - 4:16 PM (GMT+8)
"""

import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta
import pytz

# ============================================================================
# CONFIGURATION
# ============================================================================

INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "nt-scada-token-secret-key-12345"  # Update if different
INFLUXDB_ORG = "nt-scada"
INFLUXDB_BUCKET = "scada_data"  # Same bucket as your normal data

EXCEL_FILE = r"C:\Users\USER\Documents\SCADA PROJECT\SCADA-PROJECT\Swat Data\Attack Data 2019\SWaT_dataset_Jul 19 v2.xlsx"

# Attack time ranges (from PDF - July 20, 2019, GMT+8)
# Converting to UTC (GMT+0) for InfluxDB
# Attack time ranges - CONVERTED TO UTC (data is in UTC)
# Original times were GMT+8, subtract 8 hours to get UTC
ATTACK_PERIODS = [
    {
        'name': 'Attack_1_FIT401_Spoof',
        'start': '2019-07-20 07:08:46',  # Was 15:08:46 GMT+8, now UTC
        'end': '2019-07-20 07:10:31',
        'target': 'FIT401',
        'description': 'Spoof FIT401 from 0.8 to 0.5'
    },
    {
        'name': 'Attack_2_LIT301_Spoof',
        'start': '2019-07-20 07:15:00',  # Was 15:15:00 GMT+8, now UTC
        'end': '2019-07-20 07:19:32',
        'target': 'LIT301',
        'description': 'Spoof LIT301 from 835 to 1024'
    },
    {
        'name': 'Attack_3_P601_Manipulation',
        'start': '2019-07-20 07:26:57',  # Was 15:26:57 GMT+8, now UTC
        'end': '2019-07-20 07:30:48',
        'target': 'P601',
        'description': 'Switch P601 from OFF to ON'
    },
    {
        'name': 'Attack_4_MultiPoint',
        'start': '2019-07-20 07:38:50',  # Was 15:38:50 GMT+8, now UTC
        'end': '2019-07-20 07:46:20',
        'target': 'MV201_P101',
        'description': 'Multi-point: MV201 OPEN + P101 ON'
    },
    {
        'name': 'Attack_5_MV501_Manipulation',
        'start': '2019-07-20 07:54:00',  # Was 15:54:00 GMT+8, now UTC
        'end': '2019-07-20 07:56:00',
        'target': 'MV501',
        'description': 'Switch MV501 from OPEN to CLOSE'
    },
    {
        'name': 'Attack_6_P301_Manipulation',
        'start': '2019-07-20 08:02:56',  # Was 16:02:56 GMT+8, now UTC
        'end': '2019-07-20 08:16:18',
        'target': 'P301',
        'description': 'Switch P301 from ON to OFF'
    }
]
# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_timestamp(ts_str):
    """Parse various timestamp formats."""
    try:
        # Try parsing ISO format with microseconds
        if 'Z' in str(ts_str):
            return pd.to_datetime(ts_str, format='%Y-%m-%dT%H:%M:%S.%fZ', utc=True)
        elif '+' in str(ts_str):
            return pd.to_datetime(ts_str)
        else:
            return pd.to_datetime(ts_str)
    except:
        return pd.to_datetime(ts_str)


def label_attacks(timestamp):
    """
    Label each timestamp as normal or attack.
    
    Returns:
    --------
    tuple : (is_attack (bool), attack_name (str), attack_target (str))
    """
    import pytz
    
    for attack in ATTACK_PERIODS:
        # Parse attack times and make them timezone-aware (UTC)
        start = pd.to_datetime(attack['start']).tz_localize('UTC')
        end = pd.to_datetime(attack['end']).tz_localize('UTC')
        
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize('UTC')
        
        if start <= timestamp <= end:
            return True, attack['name'], attack['target']
    
    return False, 'Normal', 'None'

def normalize_column_names(df):
    """
    Normalize column names to match your existing data format.
    
    Maps: 'FIT 101' → 'FIT101.Pv'
          'P101 Status' → 'P101.Status'
    """
    column_mapping = {}
    
    for col in df.columns:
        if col == 'GMT +0':
            column_mapping[col] = 't_stamp'
        elif 'Status' in col:
            # 'P101 Status' → 'P101.Status'
            new_name = col.replace(' Status', '.Status').replace(' ', '')
            column_mapping[col] = new_name
        elif 'STATE' in col:
            # Keep as is
            column_mapping[col] = col.replace(' ', '_')
        else:
            # Sensor names: 'FIT 101' → 'FIT101.Pv'
            new_name = col.replace(' ', '') + '.Pv'
            column_mapping[col] = new_name
    
    return df.rename(columns=column_mapping)


# ============================================================================
# MAIN LOADING FUNCTION
# ============================================================================

def load_attack_data_to_influxdb():
    """Load SWaT attack data into InfluxDB with labels."""
    
    print("="*70)
    print("LOADING SWAT ATTACK DATA TO INFLUXDB")
    print("="*70)
    
    # Step 1: Load Excel data
    print(f"\n📥 Loading data from Excel...")
    df = pd.read_excel(EXCEL_FILE)
    print(f"   ✓ Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Step 2: Normalize column names
    print(f"\n🔧 Normalizing column names...")
    df = normalize_column_names(df)
    print(f"   ✓ Columns normalized")
    
    # Step 3: Parse timestamps
    print(f"\n⏰ Parsing timestamps...")
    df['t_stamp'] = df['t_stamp'].apply(parse_timestamp)
    print(f"   ✓ Time range: {df['t_stamp'].min()} to {df['t_stamp'].max()}")
    
    # Step 4: Label attacks
    print(f"\n🏷️  Labeling attack periods...")
    labels = df['t_stamp'].apply(label_attacks)
    df['is_attack'] = [x[0] for x in labels]
    df['attack_name'] = [x[1] for x in labels]
    df['attack_target'] = [x[2] for x in labels]
    
    attack_count = df['is_attack'].sum()
    normal_count = (~df['is_attack']).sum()
    print(f"   ✓ Normal data points: {normal_count}")
    print(f"   ✓ Attack data points: {attack_count}")
    print(f"   ✓ Attack periods detected:")
    for attack in ATTACK_PERIODS:
        count = (df['attack_name'] == attack['name']).sum()
        print(f"      • {attack['name']}: {count} points")
    
    # Step 5: Connect to InfluxDB
    print(f"\n🔌 Connecting to InfluxDB...")
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Step 6: Write data to InfluxDB
    print(f"\n📤 Writing data to InfluxDB bucket '{INFLUXDB_BUCKET}'...")
    
    batch_size = 1000
    total_written = 0
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        points = []
        
        for _, row in batch.iterrows():
            # Create point with measurement "swat_attack_data"
            point = Point("swat_attack_data") \
                .time(row['t_stamp'], WritePrecision.NS)
            
            # Add all sensor fields
            for col in df.columns:
                if col not in ['t_stamp', 'is_attack', 'attack_name', 'attack_target']:
                    if pd.notna(row[col]):
                        # Convert to appropriate type
                        if isinstance(row[col], (int, np.integer)):
                            point = point.field(col, int(row[col]))
                        elif isinstance(row[col], (float, np.floating)):
                            point = point.field(col, float(row[col]))
                        else:
                            point = point.field(col, str(row[col]))
            
            # Add attack labels as tags and fields
            point = point.tag("is_attack", str(row['is_attack']))
            point = point.tag("attack_name", row['attack_name'])
            point = point.tag("attack_target", row['attack_target'])
            point = point.field("attack_label", int(row['is_attack']))
            
            points.append(point)
        
        # Write batch
        write_api.write(bucket=INFLUXDB_BUCKET, record=points)
        total_written += len(batch)
        print(f"   ✓ Written batch {i//batch_size + 1}: {total_written}/{len(df)} points")
    
    client.close()
    
    print(f"\n✅ SUCCESS! {total_written} data points written to InfluxDB")
    print(f"   • Measurement name: 'swat_attack_data'")
    print(f"   • Bucket: '{INFLUXDB_BUCKET}'")
    print(f"   • Normal points: {normal_count}")
    print(f"   • Attack points: {attack_count}")
    
    # Save summary
    summary_file = 'swat_attack_data_summary.csv'
    summary = df.groupby('attack_name').agg({
        't_stamp': ['min', 'max', 'count']
    }).reset_index()
    summary.to_csv(summary_file, index=False)
    print(f"\n💾 Summary saved to: {summary_file}")
    
    print("\n" + "="*70)
    print("DATA LOADING COMPLETE!")
    print("="*70)
    print("\n📊 Next steps:")
    print("1. Verify data in InfluxDB Data Explorer")
    print("2. Run anomaly_detector.py")
    print("3. Build Anomaly Detection Dashboard")


def verify_data():
    """Quick verification that data was loaded."""
    print("\n🔍 Verifying data in InfluxDB...")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: 2019-07-20T00:00:00Z, stop: 2019-07-21T00:00:00Z)
      |> filter(fn: (r) => r._measurement == "swat_attack_data")
      |> count()
    '''
    
    result = query_api.query(query)
    
    for table in result:
        for record in table.records:
            print(f"   ✓ Total records: {record.get_value()}")
    
    client.close()


if __name__ == "__main__":
    try:
        load_attack_data_to_influxdb()
        verify_data()
    except FileNotFoundError:
        print(f"\n❌ ERROR: Excel file not found!")
        print(f"   Expected path: {EXCEL_FILE}")
        print(f"   Please update the EXCEL_FILE path in the script.")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
