# DataHub-Airflow Integration Solution Guide

## Problem Overview

The initial setup had multiple issues:

1. **Package Installation**: The `datahub` Python package wasn't installed in the Airflow container
2. **Network Connectivity**: Separate Docker stacks couldn't communicate with each other
3. **API Compatibility**: DataHub API version issues caused schema/URN format errors
4. **Docker Images**: Using outdated image references
5. **Port Conflicts**: Conflicting port mappings

## Solution Architecture

We've implemented a solution with two Docker Compose stacks connected via a shared network:

```
┌─────────────────────┐     ┌─────────────────────┐
│  Airflow + Spark    │     │      DataHub        │
│  Stack              │     │      Stack          │
│                     │     │                     │
│ ┌─────────────────┐ │     │ ┌─────────────────┐ │
│ │airflow-webserver│ │     │ │   datahub-gms   │ │
│ └─────────────────┘ │     │ └─────────────────┘ │
│         │           │     │         │           │
│ ┌─────────────────┐ │     │ ┌─────────────────┐ │
│ │airflow-scheduler│ │     │ │datahub-frontend │ │
│ └─────────────────┘ │     │ └─────────────────┘ │
│         │           │     │         │           │
│ ┌─────────────────┐ │     │ ┌─────────────────┐ │
│ │    postgres     │ │     │ │   other deps    │ │
│ └─────────────────┘ │     │ └─────────────────┘ │
└─────────────────────┘     └─────────────────────┘
            │                         │
            │                         │
            ▼                         ▼
     ┌───────────────────────────────────┐
     │      shared_data_platform         │
     │         Docker Network            │
     └───────────────────────────────────┘
```

## Key Changes

### 1. Package Installation

Created a custom `Dockerfile.airflow` to install the DataHub client with the right user:

```dockerfile
FROM apache/airflow:2.7.1-python3.10
USER airflow
RUN pip install --user acryl-datahub==0.12.0.3 sqlalchemy pandas psycopg2-binary requests
```

### 2. Network Configuration

Added both stacks to a shared Docker network:

```yaml
networks:
  default:
  shared_network:
    external: true
    name: shared_data_platform
```

And created a script to ensure containers are properly connected to the network.

### 3. DataHub API Compatibility

Updated the DAG code to use the correct API format for DataHub v1.0.0rc3:

```python
# OLD approach (pre v1.0.0):
# datasetSnapshot = DatasetSnapshotClass(...)
# metadataChangeEvent = MetadataChangeEventClass(proposedSnapshot=datasetSnapshot)
# emitter.emit(metadataChangeEvent)

# NEW approach (v1.0.0+):
properties_mcp = MetadataChangeProposalClass(
    entityUrn=dataset_urn,
    entityType="dataset",
    changeType="UPSERT",
    aspectName="datasetProperties",
    aspect=DatasetPropertiesClass(...)
)
emitter.emit(properties_mcp)
```

### 4. Docker Image References

Updated images from `linkedin/` to `acryldata/` namespace to ensure availability:

```yaml
datahub-gms:
  image: acryldata/datahub-gms:head
  # ...
```

### 5. Port Conflict Resolution

Modified port mappings to avoid conflicts:

```yaml
ports:
  - "8082:8080"  # datahub-gms
  - "9002:9002"  # datahub-frontend
  - "8090:8080"  # airflow-webserver
```

## Troubleshooting

We created a diagnostic script (`scripts/datahub-connectivity.sh`) that:

1. Verifies the shared network exists
2. Checks which containers are on the network
3. Adds missing containers to the network if needed
4. Tests connectivity between Airflow and DataHub
5. Verifies package installation

The DAG itself tries multiple URLs for connecting to DataHub:

```python
datahub_gms_urls = [
    "http://datahub-gms:8080",       # Container name within shared network
    "http://localhost:8082",         # Port mapping on host
    # ...
]
```

## Deployment Guide

1. Create the shared network:
   ```bash
   docker network create shared_data_platform
   ```

2. Start the DataHub stack first:
   ```bash
   docker-compose -f datahub-docker-compose.yml up -d
   ```

3. Start the Airflow stack:
   ```bash
   docker-compose up -d
   ```

4. Run the connectivity diagnostic:
   ```bash
   ./scripts/datahub-connectivity.sh
   ```

5. Trigger the Airflow DAG through the UI

## API Reference

For future DataHub API updates, refer to:
- [DataHub REST API Docs](https://datahubproject.io/docs/api/rest/rest-api)
- [Metadata Change Proposal Format](https://datahubproject.io/docs/metadata-ingestion/mcp)
- [Python SDK Examples](https://datahubproject.io/docs/metadata-ingestion/sdk)

## Issue Summary
The issue was with the `emit_to_datahub` task in our Airflow DAG, which was failing to successfully ingest metadata into DataHub. The specific error was related to missing required fields in the SchemaMetadata aspect.

## Root Causes Identified
1. **Missing Required Fields**: The SchemaMetadata aspect was missing two required fields:
   - `hash`: Required field even if empty
   - `platformSchema`: Required field containing schema definition

2. **Proper API Endpoint Usage**: We needed to use the correct REST endpoint for metadata ingestion (`/aspects?action=ingestProposal`) with properly formatted JSON payloads.

## Solution Implemented

### 1. Direct REST API Approach
We replaced the DataHub client library approach with direct REST API calls to the DataHub GMS server, providing more control over the exact format of metadata being sent.

### 2. Complete SchemaMetadata Structure
We added the missing required fields to the SchemaMetadata aspect:
```json
{
    "schemaName": "employees_schema",
    "platform": "urn:li:dataPlatform:postgres",
    "version": 1,
    "created": { ... },
    "lastModified": { ... },
    "hash": "",
    "platformSchema": {
        "com.linkedin.schema.MySqlDDL": {
            "tableSchema": "CREATE TABLE employees (id INT, name VARCHAR(100), department VARCHAR(100));"
        }
    },
    "fields": [ ... ]
}
```

### 3. Network Connectivity
We ensured the Airflow containers could properly reach the DataHub GMS server by:
- Using a shared Docker network (`shared_data_platform`)
- Testing connectivity with curl commands
- Verifying the DataHub GMS service was accessible at `http://datahub-gms:8080`

### 4. Testing & Verification
We created testing scripts to verify:
- Network connectivity between containers
- API endpoint accessibility
- Ability to send and retrieve metadata

## Verification
- All aspects (datasetProperties, schemaMetadata, ownership) successfully ingested into DataHub
- Dataset is now visible in DataHub with complete metadata
- The Airflow DAG task `emit_to_datahub` completes successfully

## Lessons Learned
1. DataHub's API requires exact field structures with all required fields present
2. Direct REST API approach provides more control and debugging capabilities
3. Network connectivity and service discovery are crucial for inter-service communication
4. Proper testing with curl commands helps isolate API issues quickly 