# teuthology-metrics
This document deploys opensearch for processing test run results data from paddles through OpenSearch.

## Getting Started

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) installed
- [Podman Compose](https://github.com/containers/podman-compose) installed
- Clone this repository
- Create directory `/data/{opensearch,dashboards}` on node

## Deployment Steps

1. **Change in directory permissions**
    ```sh
    sudo chown -R 1000:1000 /data && sudo chcon -Rt container_file_t /data
    ```

2. **Start the services:**
    ```sh
    OPENSEARCH_INITIAL_ADMIN_PASSWORD='<passwd>' podman-compose up -d
    ```

3. **Verify the deployment:**
    ```sh
    podman-compose ps
    ```

## Stopping the Services

To stop and remove the containers, run:
```sh
podman-compose down
```

## Configuration

- Edit the `container-compose.yml` file to adjust environment variables or service settings as needed.

## Troubleshooting

- Check logs with:
  ```sh
  podman-compose logs
  ```

## Additional Resources

- [Podman Compose Documentation](https://github.com/containers/podman-compose)
- [Project Wiki](../docs/)

## Getting data from Paddle

- Update `config.cfg` with paddle server `host` and `port`
- To get test results for `main` branch & `smoke` suite for date `July 31st, 2025` and executed by user `teuthology`
  ```sh 
  python api/paddle.py \
    --config=.config.cfg \
    --user=teuthology \
    --suite=smoke \
    --date=2025-07-31 \
    --output-dir=./testruns
  ```

## Updating test runs to opensearch
- Update `config.cfg` with opensearch server `host` and `port`
- To update opensearch with generated teuthology runs
  ```sh
  python api/opensearch.py \
    --config=./config.cfg \
    --testruns-dir=./testruns
  ```