#!/usr/bin/env python3
"""
Test script for DataHub connectivity from Airflow
Run this script inside the Airflow container to test DataHub connectivity
"""

import requests
import json
import sys
import time
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import MetadataChangeProposalClass
import socket

def test_network_connectivity(urls):
    """Test basic network connectivity to DataHub GMS"""
    print("\n=== Testing Basic Network Connectivity ===")
    for url in urls:
        try:
            print(f"Testing URL: {url}")
            response = requests.get(url, timeout=5)
            print(f"  Status: {response.status_code}")
            print(f"  Headers: {response.headers}")
            
            # Try to resolve the hostname
            hostname = url.split("://")[1].split(":")[0]
            try:
                ip = socket.gethostbyname(hostname)
                print(f"  Hostname {hostname} resolves to {ip}")
            except socket.gaierror:
                print(f"  ERROR: Cannot resolve hostname {hostname}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ERROR: {str(e)}")

def test_datahub_api(urls):
    """Test DataHub API functionality"""
    print("\n=== Testing DataHub API ===")
    
    # Test authentication
    for url in urls:
        base_url = url.rstrip("/")
        try:
            print(f"Testing authentication at {base_url}/credentials")
            auth_response = requests.post(
                f"{base_url}/credentials",
                json={
                    "actor_type": "USER",
                    "actor_id": "admin",
                    "password": "admin",
                    "type": "PERSONAL"
                },
                timeout=5
            )
            print(f"  Status: {auth_response.status_code}")
            print(f"  Response: {auth_response.text[:150]}")
            
            if auth_response.status_code == 200:
                token = auth_response.json().get("value")
                if token:
                    print("  ✅ Successfully obtained token")
                    # Try to use the token
                    try:
                        print(f"Testing API call with token to {base_url}/entities")
                        headers = {"Authorization": f"Bearer {token}"}
                        entity_response = requests.get(f"{base_url}/entities", headers=headers, timeout=5)
                        print(f"  Status: {entity_response.status_code}")
                        print(f"  Response: {entity_response.text[:150]}")
                    except requests.exceptions.RequestException as e:
                        print(f"  ERROR accessing entities: {str(e)}")
            else:
                print("  ❌ Failed to obtain token")
                
        except requests.exceptions.RequestException as e:
            print(f"  ERROR: {str(e)}")

def test_datahub_emitter(urls):
    """Test DataHub emitter functionality"""
    print("\n=== Testing DataHub Emitter ===")
    
    for url in urls:
        try:
            print(f"Testing DataHub emitter with URL: {url}")
            
            # Create a test MCP
            dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,test.table,PROD)"
            
            # First create the emitter
            emitter = DatahubRestEmitter(gms_server=url)
            
            # Try a simple properties dict
            print("Testing MCP with direct dict aspect...")
            properties_mcp = MetadataChangeProposalClass(
                entityUrn=dataset_urn,
                entityType="dataset",
                changeType="UPSERT",
                aspectName="datasetProperties"
            )
            
            properties_dict = properties_mcp.to_obj()
            properties_dict["aspect"] = {
                "description": "Test dataset",
                "customProperties": {"key": "value"}
            }
            
            properties_mcp = MetadataChangeProposalClass.from_obj(properties_dict)
            
            # Print the JSON representation to verify it looks correct
            print(f"  MCP JSON: {json.dumps(properties_mcp.to_obj())[:200]}")
            
            # Try to emit
            try:
                emitter.emit_mcp(properties_mcp)
                print("  ✅ Successfully emitted MCP")
            except Exception as e:
                print(f"  ❌ Failed to emit MCP: {str(e)}")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    # URLs to test
    urls = [
        "http://datahub-gms:8080",
        "http://datahub-datahub-gms:8080",
        "http://datahub-datahub-gms-1:8080",
        "http://localhost:8082"
    ]
    
    print("=== DataHub Connectivity Test from Airflow ===")
    print(f"Testing URLs: {urls}")
    
    test_network_connectivity(urls)
    test_datahub_api(urls)
    test_datahub_emitter(urls)
    
    print("\n=== Test Complete ===") 