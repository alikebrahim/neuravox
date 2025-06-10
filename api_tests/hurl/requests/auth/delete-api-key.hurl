# Delete API Key
DELETE {{base_url}}/auth/keys/{{key_id}}
Authorization: Bearer {{api_key}}

HTTP 204
[Asserts]
status == 204