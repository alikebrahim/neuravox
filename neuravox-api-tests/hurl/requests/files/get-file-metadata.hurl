# Get File Metadata
GET {{base_url}}/files/{{file_id}}
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" contains "application/json"
jsonpath "$.id" == "{{file_id}}"
jsonpath "$.filename" exists
jsonpath "$.size" isInteger
jsonpath "$.uploaded_at" exists
jsonpath "$.download_url" exists
jsonpath "$.audio" exists