# Process Audio Only
POST {{base_url}}/process
Authorization: Bearer {{api_key}}
Content-Type: application/json
{
  "file_ids": ["{{file_id}}"],
  "config": {
    "silence_threshold": -40.0,
    "min_silence_duration": 1.0,
    "output_format": "wav",
    "sample_rate": 16000,
    "normalize": true
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
process_job_id: jsonpath "$.id"