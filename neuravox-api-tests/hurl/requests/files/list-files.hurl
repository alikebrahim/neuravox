# List Files
GET {{base_url}}/files
Authorization: Bearer {{api_key}}
[QueryStringParams]
limit: 10
offset: 0

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.files" isCollection
jsonpath "$.total" isInteger
jsonpath "$.limit" == 10
jsonpath "$.offset" == 0
jsonpath "$.files[*].id" exists
jsonpath "$.files[*].filename" exists
jsonpath "$.files[*].size" exists