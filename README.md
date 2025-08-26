# teuthology-metrics
This document deploys opensearch for processing test run results data from paddles through OpenSearch.

## Getting Started

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) installed
- [Podman Compose](https://github.com/containers/podman-compose) installed
- Clone this repository

## Deployment Steps

1. **Create required directories**
    ```sh
    mkdir -p /data/{opensearch,dashboards,scheduler}
    ```

2. **Create `config.cfg` with `paddle` and `opensearch` details in `/data/scheduler`**

3. **Change directory permissions**
    ```sh
    sudo chown -R 1000:1000 /data && sudo chcon -Rt container_file_t /data
    ```

4. **Build scheduler container image**
    ```sh
    podman build -t scheduler-app:latest .
    ```

5. **Start the services**
    ```sh
    OPENSEARCH_INITIAL_ADMIN_PASSWORD='<passwd>' podman-compose up -d
    ```

6. **Verify the deployment**
    ```sh
    podman-compose ps
    ```

## Configuration

- Edit the `container-compose.yml` file to adjust environment variables or service settings as needed

## Stopping the Services

- To stop and remove the containers, run
  ```sh
  podman-compose down
  ```

## Troubleshooting

- Check logs with:
  ```sh
  podman-compose logs
  ```

## Update OpenSearch with test runs manually

- Create `config.cfg` with `paddle` and `opensearch`
- Update test results for `main` branch & `smoke` suite for date `July 31st, 2025` and executed by user `teuthology` to OpenSearch
  ```sh 
  python run.py \
    --config=config.cfg \
    --user=teuthology \
    --suite=smoke \
    --date=2025-07-31
  ```

## Additional Resources

- [Podman Compose Documentation](https://github.com/containers/podman-compose)
- [Project Wiki](../docs/)