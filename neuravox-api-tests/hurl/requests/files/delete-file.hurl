# Delete File
DELETE {{base_url}}/files/{{file_id}}
Authorization: Bearer {{api_key}}

HTTP 204
[Asserts]
status == 204