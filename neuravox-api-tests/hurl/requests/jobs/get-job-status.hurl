# Get Job Status
GET {{base_url}}/jobs/{{job_id}}
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.id" == "{{job_id}}"
jsonpath "$.status" exists
jsonpath "$.progress" isInteger
jsonpath "$.created_at" exists
jsonpath "$.updated_at" exists

[Captures]
job_status: jsonpath "$.status"
job_progress: jsonpath "$.progress"
job_result: jsonpath "$.result"