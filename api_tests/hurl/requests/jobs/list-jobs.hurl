# List Jobs
GET {{base_url}}/jobs
Authorization: Bearer {{api_key}}
[QueryStringParams]
limit: 10
offset: 0
status: COMPLETED

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.jobs" isCollection
jsonpath "$.total" isInteger
jsonpath "$.limit" == 10
jsonpath "$.offset" == 0
jsonpath "$.jobs[*].id" exists
jsonpath "$.jobs[*].status" exists
jsonpath "$.jobs[*].job_type" exists