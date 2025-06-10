# Full Workflow - Complete API test sequence
# Tests authentication → file upload → job processing → results

# Step 1: Health Check
GET {{base_url}}/health

HTTP 200
[Asserts]
status == 200
jsonpath "$.status" == "healthy"

# Step 2: Create API Key
POST {{base_url}}/auth/keys
Content-Type: application/json
{
  "name": "full-test-{{timestamp}}",
  "user_id": "{{user_id}}",
  "rate_limit_per_minute": {{rate_limit_per_minute}}
}

HTTP 201
[Asserts]
status == 201
jsonpath "$.key" exists
jsonpath "$.id" exists

[Captures]
api_key: jsonpath "$.key"
key_id: jsonpath "$.id"

# Step 3: Upload File
POST {{base_url}}/upload
Authorization: Bearer {{api_key}}
[MultipartFormData]
file: file,{{test_file_path}}

HTTP 201
[Asserts]
status == 201
jsonpath "$.id" exists
jsonpath "$.filename" exists
jsonpath "$.size" isInteger

[Captures]
file_id: jsonpath "$.id"
file_name: jsonpath "$.filename"

# Step 4: List Files (verify upload)
GET {{base_url}}/files
Authorization: Bearer {{api_key}}
[QueryStringParams]
limit: 10
offset: 0

HTTP 200
[Asserts]
status == 200
jsonpath "$" isCollection

# Step 5: Create Processing Job
POST {{base_url}}/jobs
Authorization: Bearer {{api_key}}
Content-Type: application/json
{
  "job_type": "PIPELINE",
  "file_ids": ["{{file_id}}"],
  "config": {
    "processing": {
      "silence_threshold": -40.0,
      "min_silence_duration": 1.0,
      "output_format": "wav",
      "normalize": true
    },
    "transcription": {
      "model": "{{default_model}}",
      "timestamps": true
    }
  }
}

HTTP 201
[Asserts]
status == 201
jsonpath "$.id" exists
jsonpath "$.status" exists
jsonpath "$.message" exists

[Captures]
job_id: jsonpath "$.id"
job_status: jsonpath "$.status"

# Step 6: Check Job Status
GET {{base_url}}/jobs/{{job_id}}
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
jsonpath "$.id" == "{{job_id}}"
jsonpath "$.status" exists
jsonpath "$.progress" isInteger

[Captures]
current_status: jsonpath "$.status"
progress: jsonpath "$.progress"

# Step 7: List Jobs (verify creation)
GET {{base_url}}/jobs
Authorization: Bearer {{api_key}}
[QueryStringParams]
limit: 10
offset: 0

HTTP 200
[Asserts]
status == 200
jsonpath "$.jobs" isCollection
jsonpath "$.jobs[?(@.id == '{{job_id}}')]" exists