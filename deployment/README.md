# Deployment Guide for Podman Compose

This document provides instructions for deploying the opensearch & opensearch dashboard using Podman Compose.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) installed
- [Podman Compose](https://github.com/containers/podman-compose) installed
- Clone this repository

## Deployment Steps

1. **Navigate to the deployment directory:**
    ```sh
    cd deployment
    ```

2. **Start the services:**
    ```sh
    podman-compose up -d
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

- Edit the `docker-compose.yml` file to adjust environment variables or service settings as needed.

## Troubleshooting

- Check logs with:
  ```sh
  podman-compose logs
  ```

## Additional Resources

- [Podman Compose Documentation](https://github.com/containers/podman-compose)
- [Project Wiki](../docs/)

