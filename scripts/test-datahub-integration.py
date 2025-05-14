#!/usr/bin/env python3
"""
Test DataHub integration by directly sending a metadata ingestion request
Run this script from the Airflow container to verify DataHub connectivity
"""

import requests
import json
import time

def test_datahub_ingest():
    """Test sending metadata to DataHub"""
    print("\n=== Testing DataHub Metadata Ingestion ===")
    
    # Create dataset URN
    dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,test_table,PROD)"
    gms_endpoint = "http://datahub-gms:8080"
    
    print(f"Using endpoint: {gms_endpoint}")
    print(f"Using dataset URN: {dataset_urn}")
    
    # Test simple dataset properties ingestion
    test_properties = {
        "description": "Test dataset created by integration test script",
        "customProperties": {
            "test_id": "integration-test-1",
            "created_at": str(int(time.time()))
        }
    }
    
    request_data = {
        "proposal": {
            "entityType": "dataset",
            "entityUrn": dataset_urn,
            "changeType": "UPSERT",
            "aspectName": "datasetProperties",
            "aspect": {
                "value": json.dumps(test_properties),
                "contentType": "application/json"
            }
        }
    }
    
    print(f"Sending test dataset properties to {gms_endpoint}/aspects?action=ingestProposal")
    
    try:
        response = requests.post(
            f"{gms_endpoint}/aspects?action=ingestProposal",
            headers={
                "Content-Type": "application/json",
                "X-RestLi-Protocol-Version": "2.0.0"
            },
            json=request_data
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Successfully ingested test dataset properties")
        else:
            print("❌ Failed to ingest test dataset properties")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Verify the ingestion by retrieving the dataset
    print("\nVerifying ingestion by retrieving dataset...")
    
    try:
        encoded_urn = dataset_urn.replace(":", "%3A").replace(",", "%2C")
        verify_url = f"{gms_endpoint}/entitiesV2/{encoded_urn}"
        
        response = requests.get(verify_url)
        
        if response.status_code == 200:
            print("✅ Successfully retrieved dataset")
            data = response.json()
            
            if "aspects" in data and "datasetProperties" in data["aspects"]:
                print("✅ Dataset properties aspect found")
                props = data["aspects"]["datasetProperties"]
                
                if "value" in props and isinstance(props["value"], dict):
                    if "description" in props["value"]:
                        print(f"Description: {props['value']['description']}")
                    
                    if "customProperties" in props["value"]:
                        print("Custom properties:")
                        for key, value in props["value"]["customProperties"].items():
                            print(f"  {key}: {value}")
            else:
                print("❌ Dataset properties aspect not found in response")
        else:
            print(f"❌ Failed to retrieve dataset: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error verifying ingestion: {str(e)}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_datahub_ingest() 