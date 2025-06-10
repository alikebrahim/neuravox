# Smoke Test Workflow - Quick health check sequence
# Run this to verify basic API functionality

# Step 1: Health Check
GET {{base_url}}/health

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.status" == "healthy"

# Step 2: Create API Key
POST {{base_url}}/auth/keys
Content-Type: application/json
{
  "name": "smoke-test-{{timestamp}}",
  "user_id": "{{user_id}}",
  "rate_limit_per_minute": {{rate_limit_per_minute}}
}

HTTP 201
[Asserts]
status == 201
jsonpath "$.key" exists
jsonpath "$.id" exists

[Captures]
api_key: jsonpath "$.key"
key_id: jsonpath "$.id"

# Step 3: Test Authentication - List Keys
GET {{base_url}}/auth/keys
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
jsonpath "$" isCollection

# Step 4: System Status
GET {{base_url}}/status
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
jsonpath "$.system" exists
jsonpath "$.workspace" exists
jsonpath "$.configuration" exists