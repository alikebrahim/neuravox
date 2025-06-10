# Create Processing Job
POST {{base_url}}/jobs
Authorization: Bearer {{api_key}}
Content-Type: application/json
{
  "job_type": "pipeline",
  "file_ids": ["{{file_id}}"],
  "config": {
    "processing": {
      "silence_threshold": 0.4,
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
header "Content-Type" contains "application/json"
jsonpath "$.id" exists
jsonpath "$.status" exists
jsonpath "$.message" exists

[Captures]
job_id: jsonpath "$.id"
job_status: jsonpath "$.status"