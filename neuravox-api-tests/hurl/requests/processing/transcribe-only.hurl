# Transcribe Only
POST {{base_url}}/transcribe
Authorization: Bearer {{api_key}}
Content-Type: application/json
{
  "file_ids": ["{{file_id}}"],
  "model": "{{default_model}}",
  "config": {
    "timestamps": true,
    "chunk_processing": true,
    "max_concurrent": 2
  }
}

HTTP 202
[Asserts]
status == 202
header "Content-Type" contains "application/json"
jsonpath "$.id" exists
jsonpath "$.status" exists
jsonpath "$.message" exists

[Captures]
transcribe_job_id: jsonpath "$.id"