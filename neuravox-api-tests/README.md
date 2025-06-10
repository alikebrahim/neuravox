# Neuravox API Test Collection

Comprehensive API testing collection for the Neuravox audio processing and transcription API using Hurl.

## Features

- **🚀 Fast & Lightweight**: Written in Rust, powered by libcurl
- **📝 Plain Text Format**: Git-friendly, human-readable test files
- **🔄 Request Chaining**: Capture values from responses and use in subsequent requests
- **✅ Built-in Assertions**: Comprehensive validation without external scripts
- **🌍 Multi-Environment**: Easy switching between dev, staging, and production
- **🎯 Simple & Maintainable**: No complex scripting required

## Installation

Install Hurl using one of these methods:

### macOS
```bash
brew install hurl
```

### Linux (Debian/Ubuntu)
```bash
curl -LO https://github.com/Orange-OpenSource/hurl/releases/download/4.1.0/hurl_4.1.0_amd64.deb
sudo dpkg -i hurl_4.1.0_amd64.deb
```

### Other platforms
See [Hurl installation docs](https://hurl.dev/docs/installation.html)

## Quick Start

1. **Start the Neuravox API server:**
   ```bash
   cd /path/to/neuravox
   python -m neuravox serve
   ```

2. **Add a test audio file:**
   ```bash
   cd neuravox-api-tests
   mkdir -p test-data
   # Copy a sample WAV file to test-data/sample.wav
   ```

3. **Run smoke tests:**
   ```bash
   ./scripts/run-smoke.sh
   ```

4. **Run full workflow:**
   ```bash
   ./scripts/run-full.sh
   ```

## Collection Structure

```
neuravox-api-tests/
├── hurl/
│   ├── requests/          # Individual API endpoint tests
│   │   ├── auth/         # Authentication endpoints
│   │   ├── files/        # File management endpoints
│   │   ├── jobs/         # Job management endpoints
│   │   ├── processing/   # Processing endpoints
│   │   └── system/       # System endpoints
│   └── workflows/        # Multi-step test sequences
│       ├── smoke-test.hurl
│       └── full-workflow.hurl
├── environments/         # Environment configurations
│   ├── common.env       # Shared configuration
│   ├── dev.env          # Development settings
│   ├── staging.env      # Staging settings
│   └── prod.env         # Production settings
├── scripts/             # Test runner scripts
│   ├── run-tests.sh     # Run all tests
│   ├── run-smoke.sh     # Quick smoke test
│   └── run-full.sh      # Full workflow test
└── test-data/           # Test files (audio samples)
```

## Running Tests

### Quick Commands

```bash
# Run smoke tests (quick health check)
./scripts/run-smoke.sh

# Run full workflow test
./scripts/run-full.sh

# Run all tests
./scripts/run-tests.sh

# Run tests against staging
./scripts/run-smoke.sh staging

# Run tests against production (with safety checks)
./scripts/run-smoke.sh prod
```

### Direct Hurl Commands

```bash
# Run a specific test file
hurl --variables-file environments/common.env \
     --variables-file environments/dev.env \
     --test \
     hurl/requests/auth/create-api-key.hurl

# Run with verbose output
hurl --variables-file environments/common.env \
     --variables-file environments/dev.env \
     --verbose \
     hurl/workflows/smoke-test.hurl

# Run with specific variables
hurl --variables-file environments/common.env \
     --variables-file environments/dev.env \
     --variable "user_id=custom-user" \
     --variable "timestamp=$(date +%s)" \
     hurl/workflows/full-workflow.hurl
```

## Test Workflows

### Smoke Test (`workflows/smoke-test.hurl`)
Quick 4-step health check:
1. API health check
2. API key creation
3. Authentication verification
4. System status check

### Full Workflow (`workflows/full-workflow.hurl`)
Complete 7-step API test:
1. Health check
2. API key creation
3. File upload
4. File listing verification
5. Job creation
6. Job status monitoring
7. Job listing verification

## Environment Configuration

### Variables

Common variables (in `common.env`):
- `default_model`: Default transcription model
- `rate_limit_per_minute`: API rate limit
- `test_file_path`: Path to test audio file
- `timeout_seconds`: Request timeout

Environment-specific (in `dev.env`, `staging.env`, `prod.env`):
- `base_url`: API base URL
- `user_id`: Test user identifier
- `key_name`: API key name prefix
- `log_level`: Logging verbosity

### Using Different Environments

```bash
# Development (default)
./scripts/run-smoke.sh
./scripts/run-smoke.sh dev

# Staging
./scripts/run-smoke.sh staging

# Production (includes safety checks)
./scripts/run-smoke.sh prod
```

## Writing Hurl Tests

### Basic Request
```hurl
# Get system health
GET {{base_url}}/health

HTTP 200
[Asserts]
status == 200
jsonpath "$.status" == "healthy"
```

### Request with Authentication
```hurl
# List files
GET {{base_url}}/files
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
jsonpath "$.files" isCollection
```

### Capturing Values
```hurl
# Create API key and capture it
POST {{base_url}}/auth/keys
Content-Type: application/json
{
  "name": "test-{{timestamp}}",
  "user_id": "{{user_id}}"
}

HTTP 201
[Captures]
api_key: jsonpath "$.key"
key_id: jsonpath "$.id"
```

### Using Captured Values
```hurl
# Use captured API key in next request
GET {{base_url}}/files/{{file_id}}
Authorization: Bearer {{api_key}}

HTTP 200
```

## Assertions

Hurl provides powerful built-in assertions:

```hurl
[Asserts]
# Status code
status == 200

# Headers
header "Content-Type" contains "application/json"

# JSON responses
jsonpath "$.status" == "success"
jsonpath "$.count" isInteger
jsonpath "$.items" isCollection
jsonpath "$.items[0].id" exists

# Response time
duration < 1000
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run API Tests
  run: |
    curl -LO https://github.com/Orange-OpenSource/hurl/releases/download/4.1.0/hurl-4.1.0-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf hurl-*.tar.gz
    export PATH=$PATH:$PWD/hurl-*/bin
    ./scripts/run-tests.sh
```

### GitLab CI
```yaml
test:
  script:
    - apt-get update && apt-get install -y curl
    - curl -LO https://github.com/Orange-OpenSource/hurl/releases/download/4.1.0/hurl_4.1.0_amd64.deb
    - dpkg -i hurl_*.deb
    - ./scripts/run-tests.sh
```

## Troubleshooting

### Common Issues

**"test-data/sample.wav not found":**
- Add a sample audio file for testing
- Supported formats: WAV, MP3, M4A, FLAC

**"Connection refused":**
- Ensure the API server is running
- Check the base_url in environment files

**"401 Unauthorized":**
- API key may have expired
- Run smoke test to create a new key

### Debug Mode

Run with verbose output:
```bash
hurl --verbose --variables-file environments/common.env \
     --variables-file environments/dev.env \
     hurl/workflows/smoke-test.hurl
```

## Contributing

1. Add new test files in appropriate directories
2. Follow existing naming conventions
3. Include assertions for all critical fields
4. Test against dev environment before committing
5. Update this README if adding new features

## Migration from Posting

This test suite was migrated from Posting to Hurl for:
- Better command-line integration
- Simpler request chaining
- Built-in assertions
- Faster execution
- No external dependencies

The test coverage and functionality remain the same, with improved performance and maintainability.