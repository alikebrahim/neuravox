# Get User Info
GET {{base_url}}/auth/me
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.user_id" exists
jsonpath "$.email" exists
jsonpath "$.created_at" exists