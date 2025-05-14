#!/bin/bash

echo "=== DataHub-Airflow Connectivity Diagnostic Tool ==="
echo

# Check if shared network exists
echo "Checking for shared network..."
if docker network ls | grep -q shared_data_platform; then
    echo "✅ shared_data_platform network exists"
else
    echo "❌ shared_data_platform network does not exist"
    echo "Creating network..."
    docker network create shared_data_platform
    echo "✅ Network created"
fi

# Check which containers are on the shared network
echo
echo "Checking containers on shared network..."
CONTAINERS=$(docker network inspect shared_data_platform -f '{{range .Containers}}{{.Name}} {{end}}')
echo "Containers on shared network: $CONTAINERS"

# Check if Airflow containers are running
echo
echo "Checking Airflow containers..."
if docker ps | grep -q airflow-webserver; then
    echo "✅ airflow-webserver is running"
    
    # Add to network if not already there
    if ! echo "$CONTAINERS" | grep -q airflow-webserver; then
        echo "Adding airflow-webserver to shared network..."
        docker network connect shared_data_platform airflow-webserver
        echo "✅ Added to network"
    fi
else
    echo "❌ airflow-webserver is not running"
fi

if docker ps | grep -q airflow-scheduler; then
    echo "✅ airflow-scheduler is running"
    
    # Add to network if not already there
    if ! echo "$CONTAINERS" | grep -q airflow-scheduler; then
        echo "Adding airflow-scheduler to shared network..."
        docker network connect shared_data_platform airflow-scheduler
        echo "✅ Added to network"
    fi
else
    echo "❌ airflow-scheduler is not running"
fi

# Check if DataHub GMS is running
echo
echo "Checking DataHub containers..."
if docker ps | grep -q datahub-gms; then
    echo "✅ datahub-gms is running"
    
    # Add to network if not already there
    if ! echo "$CONTAINERS" | grep -q datahub-gms; then
        echo "Adding datahub-gms to shared network..."
        docker network connect shared_data_platform datahub-gms
        echo "✅ Added to network"
    fi
else
    echo "❌ datahub-gms is not running"
fi

if docker ps | grep -q datahub-frontend; then
    echo "✅ datahub-frontend is running"
    
    # Add to network if not already there
    if ! echo "$CONTAINERS" | grep -q datahub-frontend; then
        echo "Adding datahub-frontend to shared network..."
        docker network connect shared_data_platform datahub-frontend
        echo "✅ Added to network"
    fi
else
    echo "❌ datahub-frontend is not running"
fi

# Test connectivity from Airflow to DataHub
echo
echo "Testing connectivity from Airflow to DataHub..."
if docker ps | grep -q airflow-webserver && docker ps | grep -q datahub-gms; then
    # Test curl connectivity to datahub-gms from airflow
    echo "Testing HTTP connectivity to datahub-gms:8080..."
    STATUS=$(docker exec airflow-webserver curl -s -o /dev/null -w "%{http_code}" http://datahub-gms:8080/)
    if [ "$STATUS" = "401" ] || [ "$STATUS" = "200" ]; then
        echo "✅ HTTP connectivity OK (status: $STATUS)"
    else
        echo "❌ Cannot connect to datahub-gms:8080 from airflow-webserver (status: $STATUS)"
    fi
    
    # Test authentication
    echo "Testing DataHub authentication..."
    AUTH_RESULT=$(docker exec airflow-webserver curl -s -X POST -H "Content-Type: application/json" \
        -d '{"actor_type":"USER","actor_id":"admin","password":"admin","type":"PERSONAL"}' \
        http://datahub-gms:8080/credentials)
    
    if echo "$AUTH_RESULT" | grep -q "value"; then
        echo "✅ Authentication successful"
    else
        echo "❌ Authentication failed: $AUTH_RESULT"
    fi
    
    # Try alternate container names
    echo "Testing alternate container names..."
    ALT_STATUS=$(docker exec airflow-webserver curl -s -o /dev/null -w "%{http_code}" http://datahub-datahub-gms:8080/ 2>/dev/null || echo "failed")
    if [ "$ALT_STATUS" = "401" ] || [ "$ALT_STATUS" = "200" ]; then
        echo "✅ Container 'datahub-datahub-gms' is reachable (status: $ALT_STATUS)"
    else
        echo "❌ Container 'datahub-datahub-gms' is not reachable (status: $ALT_STATUS)"
    fi
else
    echo "Cannot test connectivity: both containers need to be running"
fi

# Verify DataHub python package installation in Airflow
echo
echo "Checking DataHub package installation in Airflow..."
if docker ps | grep -q airflow-webserver; then
    docker exec airflow-webserver python -c "import pkg_resources; print([p.version for p in pkg_resources.working_set if 'datahub' in p.project_name.lower()])"
    
    # Test DataHub package functionality
    echo "Testing DataHub package functionality..."
    docker exec airflow-webserver python -c "
from datahub.emitter.rest_emitter import DatahubRestEmitter;
from datahub.metadata.schema_classes import MetadataChangeProposalClass;
import json;

print('✅ Successfully imported DataHub packages')
try:
    mcp = MetadataChangeProposalClass(
        entityUrn='test',
        entityType='dataset',
        changeType='UPSERT',
        aspectName='test'
    )
    print('✅ Successfully created MetadataChangeProposalClass object')
    json_str = json.dumps(mcp.to_obj())
    print('✅ Successfully converted to JSON')
except Exception as e:
    print(f'❌ Error testing DataHub packages: {str(e)}')
"
else
    echo "Cannot check package: airflow-webserver container is not running"
fi

echo
echo "=== Diagnostic Complete ==="
echo "If you're still experiencing issues, please check the logs with:"
echo "docker logs datahub-gms"
echo "docker logs airflow-scheduler"
echo
echo "To manually add containers to shared network, use:"
echo "docker network connect shared_data_platform CONTAINER_NAME" 