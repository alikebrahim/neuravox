# Full Processing Pipeline
POST {{base_url}}/pipeline
Authorization: Bearer {{api_key}}
Content-Type: application/json
{
  "file_ids": ["{{file_id}}"],
  "config": {
    "processing": {
      "silence_threshold": 0.4,
      "min_silence_duration": 1.0,
      "output_format": "wav",
      "sample_rate": 16000,
      "normalize": true
    },
    "transcription": {
      "model": "{{default_model}}",
      "timestamps": true,
      "chunk_processing": true,
      "max_concurrent": 2
    }
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
pipeline_job_id: jsonpath "$.id"