# Create API Key
POST {{base_url}}/auth/keys
Content-Type: application/json
{
  "name": "{{key_name}}-{{timestamp}}",
  "user_id": "{{user_id}}",
  "rate_limit_per_minute": {{rate_limit_per_minute}}
}

HTTP 201
[Asserts]
status == 201
header "Content-Type" contains "application/json"
jsonpath "$.key" exists
jsonpath "$.id" exists
jsonpath "$.name" contains "{{key_name}}"
jsonpath "$.user_id" == "{{user_id}}"

[Captures]
api_key: jsonpath "$.key"
key_id: jsonpath "$.id"