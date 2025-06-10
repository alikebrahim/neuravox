# Retry Failed Job
POST {{base_url}}/jobs/{{job_id}}/retry
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.id" exists
jsonpath "$.status" == "PENDING"
jsonpath "$.retry_count" isInteger

[Captures]
new_job_id: jsonpath "$.id"