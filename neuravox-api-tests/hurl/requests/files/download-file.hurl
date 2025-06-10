# Download File
GET {{base_url}}/files/{{file_id}}/download
Authorization: Bearer {{api_key}}

HTTP 200
[Asserts]
status == 200
header "Content-Type" exists
header "Content-Disposition" contains "attachment"
header "Content-Length" exists