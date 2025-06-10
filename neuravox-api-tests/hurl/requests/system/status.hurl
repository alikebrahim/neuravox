# System Status
GET {{base_url}}/status
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.status" exists
jsonpath "$.uptime" exists
jsonpath "$.active_jobs" isInteger
jsonpath "$.queue_size" isInteger
jsonpath "$.system_info" exists