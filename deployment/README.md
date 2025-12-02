# teuthology-metrics

This document deploys opensearch for processing test run results data from paddles through OpenSearch.

## Getting Started

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) installed
- [Podman Compose](https://github.com/containers/podman-compose) installed

## Deployment Steps

1. **Create required directories**
    ```sh
    mkdir -p /data/{opensearch,dashboards,scheduler}
    ```

2. **Create `config.cfg` with required details in `/data/scheduler`**

3. **Change directory permissions**
    ```sh
    sudo chown -R 1000:1000 /data && sudo chcon -Rt container_file_t /data
    ```

4. **Build container images**
    ```sh

    # Scheduler image
    podman build -f deployment/Containerfile -t scheduler-app:latest .
    
    # Dashboard-import image
    podman build -f deployment/dashboard-import/Containerfile -t dashboard-import:latest .
    ```

5. **Create environment file with OpenSearch & Scheduler configs**
    ```sh
    cat <<'EOF' > .env
    OPENSEARCH_INITIAL_ADMIN_PASSWORD='<passwd>'
    APP_ARGS='--config /usr/share/config.cfg --sha1-path /usr/share/sha1 --user teuthology'
    EOF
    ```

6. **Start the services**
    ```sh
     podman-compose --env-file .env -f deployment/podman-compose.yaml up -d
    ```

7. **Verify the deployment**
    ```sh
    podman-compose -f deployment/podman-compose.yaml ps
    ```
    
    All three containers should show "Up" status.

8. **Access OpenSearch Dashboards**
    - Open browser: `http://localhost:5601`
    - Username: `admin`
    - Password: The password you set in step 5

## Configuration

- Edit the `deployment/podman-compose.yml` file to adjust environment variables or service settings as needed

## Stopping the Services

- To stop and remove the containers, run
  ```sh
  podman-compose -f deployment/podman-compose.yaml down
  ```

## Troubleshooting

- Check logs with:
  ```sh
  podman-compose -f deployment/podman-compose.yaml logs
  ```

## Additional Resources

- [Podman Compose Documentation](https://github.com/containers/podman-compose)
