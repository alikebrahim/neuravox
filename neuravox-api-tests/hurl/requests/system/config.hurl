# System Configuration
GET {{base_url}}/config
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.api_version" exists
jsonpath "$.features" exists
jsonpath "$.limits" exists
jsonpath "$.supported_formats" isCollection
jsonpath "$.models" exists