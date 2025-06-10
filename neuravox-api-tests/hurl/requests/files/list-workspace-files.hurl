# List Workspace Files
GET {{base_url}}/workspace/files
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$" isCollection
jsonpath "$[*].path" exists
jsonpath "$[*].size" exists
jsonpath "$[*].modified_at" exists