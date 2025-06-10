# Upload File
POST {{base_url}}/upload
Authorization: Bearer {{api_key}}
[Multipart]
file: file,{{test_file_path}};

HTTP 201
[Asserts]
status == 201
header "Content-Type" contains "application/json"
jsonpath "$.id" exists
jsonpath "$.filename" exists
jsonpath "$.size" isInteger
jsonpath "$.message" exists

[Captures]
file_id: jsonpath "$.id"
file_name: jsonpath "$.filename"
file_size: jsonpath "$.size"