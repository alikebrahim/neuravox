# List Available Models
GET {{base_url}}/models
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$" isCollection
jsonpath "$[*].id" exists
jsonpath "$[*].name" exists
jsonpath "$[*].provider" exists
jsonpath "$[*].capabilities" exists