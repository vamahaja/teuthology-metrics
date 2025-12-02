# teuthology-metrics

`teuthology-metrics` is a toolset designed to process and analyze Teuthology test run results using OpenSearch. It indexes test data to allow rich querying and generates summarized reports that can be emailed to stakeholders.

This project is designed to provide deeper insights and uncover historical trends for users working with Ceph's Teuthology test framework, enabling a more comprehensive understanding and analysis of their test run data.

## Features
- Ingest Teuthology test run results into OpenSearch indices for fast search and analytics.
- Generate and email test summary reports for specified branches, time periods, and commit SHAs.
- Flexible logging options for debugging and monitoring.
- PEP 8 code style enforcement using Ruff.

## Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation) CLI installed for running scripts and managing dependencies.
- OpenSearch DB & Dashboard deployed and accessible (see [deployment documentation](https://github.com/vamahaja/teuthology-metrics/tree/main/deployment/README.md)).
- A configured `config.cfg` file with settings such as OpenSearch endpoint, user credentials, email SMTP server, and other required details.

### Configuration file (`config.cfg`)

Create a `config.cfg` with necessary configuration parameters. An example minimal configuration might include:
```
[paddle]
api_url = your-paddle-endpoint

[opensearch]
api_url = your-opensearch-endpoint
user = your_user
password = your_password

[email]
host = smtp.example.com
port = 587
username = your_username
password = your_email_password
sender = your_email@example.com

[report]
opensearch_index = opensearch_index
results_server = results_server_url

[scheduler]
branches = <ceph-branches>
suites = <ceph-teuthology-suites>, ....
cron_report = <report-cron-expr>
cron_task = <task-cron-expr>
email = <your-email-addr>
```

## Usage

### Update OpenSearch with test runs

Ingest test results for a specific user, suite, and date:
```sh 
uv run python runner.py \
  --config config.cfg \
  --user teuthology \
  --suite smoke \
  --date 2025-11-21
```

### Trigger report email

Send summary reports for a branch over a date range via email:
```sh
uv run python report.py \
  --config config.cfg \
  --branch main \
  --start-date 2025-11-21 \
  --end-date 2025-11-23 \
  --email-address vaibhavsm04@gmail.com \
  --sha-id a6c7445ba1ccce82c5afae9856e2fa4ea693cd86
```

### Start scheduler

Start scheduler for teuthology triggered runs
```sh
uv run python scheduler.py \
  --config config.cfg \
  --sha1-path ./sha1 \
  --user teuthology
```

### Logging options

Add these optional flags to increase log detail and save logs in a specific directory: 
```sh
  uv run python runner.py \
    --config config.cfg \
    --user teuthology \
    --suite smoke \
    --date 2025-11-21 \
    --log-level debug \
    --log-path ./logs
```

## Development

This project uses [Ruff](https://docs.astral.sh/ruff) as the Python linter to enforce PEP 8 rules.
- Check all files:
  ```sh
  uv run ruff check .
  ```
- Check a single file:
  ```sh
  uv run ruff check <absolute_or_relative_file_path>
  ```
