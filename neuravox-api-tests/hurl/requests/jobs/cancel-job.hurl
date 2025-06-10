# Cancel Job
DELETE {{base_url}}/jobs/{{job_id}}
Authorization: Bearer {{api_key}}

HTTP 204
[Asserts]
status == 204