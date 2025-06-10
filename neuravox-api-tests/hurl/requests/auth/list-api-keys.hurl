# List API Keys
GET {{base_url}}/auth/keys
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$" isCollection
jsonpath "$[*].id" exists
jsonpath "$[*].name" exists
jsonpath "$[*].created_at" exists