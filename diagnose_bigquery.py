#!/usr/bin/env python3
"""
BigQuery Connection Diagnostic Script

This script helps diagnose whether connection issues are due to:
1. Network/firewall problems
2. Credentials configuration issues
3. Permission problems
"""

import os
import sys
import json
import socket
from pathlib import Path

def check_network_connectivity():
    """Test basic network connectivity to Google Cloud endpoints"""
    print("=" * 60)
    print("1. NETWORK CONNECTIVITY CHECK")
    print("=" * 60)

    endpoints = [
        ("oauth2.googleapis.com", 443),
        ("bigquery.googleapis.com", 443),
        ("www.googleapis.com", 443),
    ]

    for host, port in endpoints:
        try:
            print(f"\nTesting {host}:{port}...", end=" ")
            socket.setdefaulttimeout(5)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                print("✅ CONNECTED")
            else:
                print(f"❌ FAILED (error code: {result})")
                if result == 113:
                    print("   -> Error 113: No route to host (firewall blocking)")
                elif result == 110:
                    print("   -> Error 110: Connection timed out")
        except socket.gaierror as e:
            print(f"❌ DNS FAILED: {e}")
        except Exception as e:
            print(f"❌ ERROR: {e}")

def check_credentials_file():
    """Verify credentials file exists and is valid JSON"""
    print("\n" + "=" * 60)
    print("2. CREDENTIALS FILE CHECK")
    print("=" * 60)

    # Check environment variable
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not cred_path:
        print("\n❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        print("\nLooking for common credential file locations...")

        common_paths = [
            "/workspace/.bigquery_credentials.json",
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
            "/workspace/credentials.json",
        ]

        for path in common_paths:
            if os.path.exists(path):
                print(f"✅ Found: {path}")
                cred_path = path
                break

        if not cred_path:
            print("\n❌ No credential file found in common locations")
            return False
    else:
        print(f"\n✅ GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")

    # Check file exists
    if not os.path.exists(cred_path):
        print(f"\n❌ Credential file does not exist: {cred_path}")
        return False

    print(f"✅ File exists: {cred_path}")

    # Check file permissions
    stat_info = os.stat(cred_path)
    print(f"✅ File permissions: {oct(stat_info.st_mode)[-3:]}")

    # Check file is valid JSON
    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
        print("✅ Valid JSON format")

        # Check required fields for service account
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        missing_fields = [f for f in required_fields if f not in creds]

        if missing_fields:
            print(f"\n❌ Missing required fields: {', '.join(missing_fields)}")
            return False

        print(f"✅ Credential type: {creds.get('type')}")
        print(f"✅ Project ID: {creds.get('project_id')}")
        print(f"✅ Client email: {creds.get('client_email')}")

        # Check private key format
        private_key = creds.get('private_key', '')
        if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
            print("❌ Private key appears malformed")
            return False

        print("✅ Private key format looks valid")

        return True

    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error reading file: {e}")
        return False

def check_bigquery_import():
    """Test if BigQuery libraries can be imported"""
    print("\n" + "=" * 60)
    print("3. BIGQUERY LIBRARY CHECK")
    print("=" * 60)

    try:
        print("\nImporting google.cloud.bigquery...", end=" ")
        from google.cloud import bigquery
        print("✅ SUCCESS")
        print(f"   Version: {bigquery.__version__}")

        print("Importing google.auth...", end=" ")
        import google.auth
        print("✅ SUCCESS")

        return True
    except ImportError as e:
        print(f"❌ FAILED: {e}")
        print("\nRun: poetry add google-cloud-bigquery google-auth")
        return False

def test_authentication():
    """Test authentication without making API calls"""
    print("\n" + "=" * 60)
    print("4. AUTHENTICATION TEST")
    print("=" * 60)

    try:
        from google.oauth2 import service_account
        import google.auth

        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if cred_path and os.path.exists(cred_path):
            print(f"\nUsing service account: {cred_path}")
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    cred_path,
                    scopes=["https://www.googleapis.com/auth/bigquery"]
                )
                print("✅ Service account credentials loaded successfully")
                print(f"   Service account email: {credentials.service_account_email}")
                print(f"   Project ID: {credentials.project_id}")
                return True
            except Exception as e:
                print(f"❌ Failed to load service account: {e}")
                return False
        else:
            print("\nTrying Application Default Credentials (ADC)...")
            try:
                credentials, project = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/bigquery"]
                )
                print("✅ ADC credentials loaded successfully")
                print(f"   Project ID: {project}")
                return True
            except Exception as e:
                print(f"❌ Failed to load ADC: {e}")
                return False

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_bigquery_connection():
    """Attempt actual BigQuery connection"""
    print("\n" + "=" * 60)
    print("5. BIGQUERY CONNECTION TEST")
    print("=" * 60)

    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        import google.auth

        # Get credentials
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if cred_path and os.path.exists(cred_path):
            print(f"\nConnecting with service account: {cred_path}")
            credentials = service_account.Credentials.from_service_account_file(
                cred_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            project_id = json.load(open(cred_path))['project_id']
        else:
            print("\nConnecting with Application Default Credentials...")
            credentials, project_id = google.auth.default(
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )

        print(f"Project ID: {project_id}")

        # Create client with short timeout
        print("\nCreating BigQuery client...", end=" ")
        client = bigquery.Client(credentials=credentials, project=project_id)
        print("✅ Client created")

        # Test simple query on public dataset
        print("\nTesting query on public dataset (timeout: 10s)...")
        query = """
            SELECT 'connection_test' as status
            LIMIT 1
        """

        try:
            query_job = client.query(query, timeout=10)
            results = list(query_job.result(timeout=10))

            if results:
                print("✅ CONNECTION SUCCESSFUL!")
                print(f"   Query returned: {dict(results[0])}")
                return True
            else:
                print("⚠️  Query completed but returned no results")
                return False

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Query failed: {error_msg}")

            # Diagnose specific errors
            if "403" in error_msg or "Permission denied" in error_msg:
                print("\n🔍 DIAGNOSIS: Permission issue")
                print("   - Service account may lack BigQuery permissions")
                print("   - Required roles: BigQuery Data Viewer, BigQuery Job User")
            elif "No route to host" in error_msg or "111" in error_msg or "113" in error_msg:
                print("\n🔍 DIAGNOSIS: Network/Firewall issue")
                print("   - Cannot reach Google Cloud APIs")
                print("   - Check firewall rules and network connectivity")
            elif "timeout" in error_msg.lower():
                print("\n🔍 DIAGNOSIS: Timeout issue")
                print("   - Connection is hanging")
                print("   - Likely firewall blocking without explicit rejection")

            return False

    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        return False

def main():
    print("\n" + "🔍" * 30)
    print("BigQuery Connection Diagnostic Tool")
    print("🔍" * 30 + "\n")

    results = {
        "network": False,
        "credentials": False,
        "libraries": False,
        "auth": False,
        "connection": False,
    }

    # Run all checks
    check_network_connectivity()
    results["credentials"] = check_credentials_file()
    results["libraries"] = check_bigquery_import()

    if results["libraries"]:
        results["auth"] = test_authentication()

        if results["auth"]:
            results["connection"] = test_bigquery_connection()

    # Final summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    print(f"\n{'✅' if results['credentials'] else '❌'} Credentials file valid")
    print(f"{'✅' if results['libraries'] else '❌'} BigQuery libraries installed")
    print(f"{'✅' if results['auth'] else '❌'} Authentication successful")
    print(f"{'✅' if results['connection'] else '❌'} BigQuery connection working")

    if all(results.values()):
        print("\n✅ ALL CHECKS PASSED - BigQuery is fully functional!")
        return 0
    else:
        print("\n❌ Some checks failed - review output above for details")
        return 1

if __name__ == "__main__":
    sys.exit(main())
