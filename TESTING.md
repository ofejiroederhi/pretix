# pretix Testing Guide

This guide explains how we test pretix and how you can run and extend the test suite in day‑to‑day development.

## Running tests

You can run tests **locally** from the `src/` directory or through the **Docker test container** (for a consistent, preconfigured environment).

- **Run the full test suite**

  Local:

  ```bash
  cd src
  PRETIX_CONFIG_FILE=tests/ci_sqlite.cfg pytest tests/ -p no:sugar
  ```

  In Docker (from the repository root):

  ```bash
  docker compose --profile test run --rm \
    -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
    test pytest tests/ -p no:sugar
  ```

- **Run with coverage (same as CI)**

  Local:

  ```bash
  cd src
  PRETIX_CONFIG_FILE=tests/ci_sqlite.cfg pytest tests/ \
    --cov=./ --cov-report=term-missing --cov-report=xml --cov-fail-under=70
  ```

  In Docker (from the repository root):

  ```bash
  docker compose --profile test run --rm \
    -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
    test pytest tests/ \
      --cov=./ --cov-report=term-missing --cov-report=xml --cov-fail-under=70
  ```

- **Fast unit tests only**

  Local:

  ```bash
  cd src
  PRETIX_CONFIG_FILE=tests/ci_sqlite.cfg pytest tests/ -m unit -p no:sugar
  ```

  In Docker (from the repository root):

  ```bash
  docker compose --profile test run --rm \
    -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
    test pytest tests/ -m unit -p no:sugar
  ```

- **Integration and end‑to‑end (E2E) tests**

  Local:

  ```bash
  cd src
  PRETIX_CONFIG_FILE=tests/ci_sqlite.cfg pytest tests/ -m "integration or e2e" -p no:sugar
  ```

  In Docker (from the repository root):

  ```bash
  docker compose --profile test run --rm \
    -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
    test pytest tests/ -m "integration or e2e" -p no:sugar
  ```

- **Concurrency tests (PostgreSQL, reuse DB)**

  Local:

  ```bash
  cd src
  PRETIX_CONFIG_FILE=tests/ci_postgres.cfg pytest tests/concurrency_tests/ --reuse-db
  ```

  In Docker (from the repository root):

  ```bash
  docker compose --profile test run --rm \
    -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
    test pytest tests/concurrency_tests/ --reuse-db -v -p no:sugar
  ```

- **Performance / slow tests (typically on schedule)**

  Local:

  ```bash
  cd src
  PRETIX_CONFIG_FILE=tests/ci_postgres.cfg pytest tests/ -m "performance or slow" --reuse-db
  ```

  In Docker (from the repository root):

  ```bash
  docker compose --profile test run --rm \
    -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
    test pytest tests/ -m "performance or slow" --reuse-db -v -p no:sugar
  ```

## Test layout

The test tree roughly mirrors the application and separates different concerns:

| Area        | Path                                  | What it covers |
|------------|---------------------------------------|----------------|
| Unit       | `tests/base/`, `tests/helpers/`       | Core logic: rounding, quotas, vouchers, financial edge cases. |
| Integration| `tests/integration/`, `tests/presale/`, `tests/api/` | Multi‑component flows: checkout, voucher redemption, API. |
| E2E        | `tests/integration/test_e2e_workflows.py` | Full workflows: cart → confirm → order, voucher reuse. |
| Concurrency| `tests/concurrency_tests/`            | Locking and race conditions (PostgreSQL, `--reuse-db`). |
| Performance| `tests/concurrency_tests/test_quota_contention_performance.py` | Quota contention under concurrent purchases. |
| Plugins    | `tests/plugins/<name>/`               | Plugin‑specific tests (Stripe, PayPal, bank transfer, statistics, …). |
| Security   | any test with `@pytest.mark.security` | Payment flows, auth, and OWASP‑relevant behaviour. |

## Security focus (OWASP / PCI DSS context)

pretix handles payment flows (Stripe, PayPal, bank transfer) and personal/order data, so security‑relevant behaviour is in scope for testing:

- For new or changed code that touches **input handling**, **authentication**, or **payment**, add tests that check for:
  - Injection and XSS resistance (OWASP Top 10).
  - Broken access control (e.g. unauthorized access to events or APIs).
  - Correct payment state transitions (e.g. webhook → order paid).
- Payment card data itself is handled by the providers; our tests focus on:
  - Using provider APIs correctly.
  - Avoiding logging of sensitive data.
  - Keeping payment and order state consistent.

Use `@pytest.mark.security` on such tests so they can be run and audited explicitly.

## Coverage

- **Target:** The project enforces a minimum of **70 %** test coverage (configured in `src/setup.cfg` and used in CI).
- **Reports:** You can use `coverage report`, `coverage html`, or rely on `src/coverage.xml` for tools like Codecov.
- **Excluded:** Migrations, `urls.py`, test code, the `testdummy` plugin, and a few glue modules are omitted from coverage.
- **Filling gaps:** The `coverage.xml` (Cobertura) report is used to find high‑risk, low‑coverage areas. Some examples already covered by targeted tests are:
  - `tests/base/test_health_view.py`
  - `tests/base/test_exporter_base.py`
  - `tests/base/test_transactions_module.py`

## Continuous integration (CI)

GitHub Actions runs the same commands you can run locally:

- **Quality Gate** (`.github/workflows/quality.yml`)
  - Lint with **isort** and **flake8**.
  - Run tests on Python 3.11 with both sqlite and Postgres.
  - Optionally build a Docker test image and execute the suite inside the container.

- **Tests matrix** (`.github/workflows/tests.yml`)
  - Full test matrix for multiple Python versions and databases.
  - Concurrency tests on Postgres.
  - Coverage upload (using `src/coverage.xml`) with `--cov-fail-under=70`.

- **Style** (`.github/workflows/style.yml`)
  - Enforces import/order checks and license headers.

- **Mutation testing** (`.github/workflows/mutation.yml`)
  - Runs `mutmut` against selected modules to catch tests that are too weak.

## Writing tests for new code

When adding or changing behaviour:

- Start by writing a **failing test** (unit, integration, plugin, or E2E) that describes the new behaviour.
- Implement the change until the test passes.
- Use markers like `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.performance`, and `@pytest.mark.security` so both developers and CI can select the right subsets.

For new presale/control features, aim to include at least one integration or E2E test that exercises the full user‑visible flow.

## Running tests with PostgreSQL in Docker

You can also run the suite inside the provided Docker test container, including concurrency and performance tests:

1. **Configure credentials**

   In `.env` set:

   ```bash
   POSTGRES_USER=pretix
   POSTGRES_PASSWORD=pretix
   ```

   Then make sure `src/tests/ci_postgres_docker.cfg` uses the same values under `[database]`.

2. **Run the test container (PostgreSQL)**

   ```bash
   docker compose --profile test run --rm \
     -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
     test pytest tests/ -v -p no:sugar
   ```

3. **Run only concurrency tests (PostgreSQL, reuse DB)**

   ```bash
   docker compose --profile test run --rm \
     -e PRETIX_CONFIG_FILE=tests/ci_postgres_docker.cfg \
     test pytest tests/concurrency_tests/ --reuse-db -v -p no:sugar
   ```

## Where things live (testing‑related)

- `src/pretix/` – application code.
- `src/tests/` – test suite.
- `src/tests/base/` – core logic and financial/quota edge cases.
- `src/tests/integration/` – E2E and broader integration workflows.
- `src/tests/concurrency_tests/` – locking and performance tests (PostgreSQL).
- `src/setup.cfg` – pytest options, coverage config, flake8, isort.
