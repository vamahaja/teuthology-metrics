# teuthology-metrics
This document deploys opensearch for processing test run results data from paddles through OpenSearch.

## Getting Started

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) installed
- [Podman Compose](https://github.com/containers/podman-compose) installed
- Clone this repository
- Create directory `/data/{opensearch,dashboads,scheduler}` on node

## Deployment Steps

1. **Create scheduler podman image**
    ```sh
    podman build -t scheduler-app:latest .
    ```

2. **Start the services**
    ```sh
    OPENSEARCH_INITIAL_ADMIN_PASSWORD='<passwd>' podman-compose up -d
    ```

3. **Verify the deployment**
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
- To update test results for `main` branch & `smoke` suite for date `July 31st, 2025` and executed by user `teuthology`
  ```sh 
  python run.py \
    --config=.config.cfg \
    --user=teuthology \
    --suite=smoke \
    --date=2025-07-31 \
    --output-dir=./testruns
  ```