# Health Check
GET {{base_url}}/health

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.status" exists
jsonpath "$.status" == "healthy"
jsonpath "$.timestamp" exists
jsonpath "$.version" exists