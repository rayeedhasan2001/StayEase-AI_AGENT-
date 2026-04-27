# API Contract

## POST `/api/chat/{conversation_id}/message`

Send one guest message to the assistant and get one reply back for that turn.

### Request schema

**Path params**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `conversation_id` | `string` | Yes | Unique ID for the conversation. |

**JSON body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `message` | `string` | Yes | Guest message in plain text. |

### Response schema

| Field | Type | Notes |
| --- | --- | --- |
| `conversation_id` | `string` | Same conversation ID from the path. |
| `reply` | `string` | Assistant reply for this turn. |
| `escalated` | `boolean` | `true` if the request needs to go to a human. |

### Example request

```http
POST /api/chat/conv-001/message
Content-Type: application/json
```

```json
{
  "message": "I need a room in Cox's Bazar from 2026-05-10 to 2026-05-12 for 2 guests."
}
```

### Example response

```json
{
  "conversation_id": "conv-001",
  "reply": "Available options:\nSea Breeze Studio in Cox's Bazar - BDT 4800/night\nKolatoli Family Suite in Cox's Bazar - BDT 6200/night",
  "escalated": false
}
```

### Possible error responses

`400 Bad Request`

```json
{
  "detail": "Message cannot be empty."
}
```

`422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

`500 Internal Server Error`

```json
{
  "detail": "Unable to process the conversation right now."
}
```

## GET `/api/chat/{conversation_id}/history`

Return the stored message history for one conversation.

### Request schema

**Path params**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `conversation_id` | `string` | Yes | Conversation ID used in earlier messages. |

### Response schema

| Field | Type | Notes |
| --- | --- | --- |
| `conversation_id` | `string` | Requested conversation ID. |
| `messages` | `array<object>` | Ordered list of guest and assistant messages. |

Each item in `messages` has:

| Field | Type | Notes |
| --- | --- | --- |
| `role` | `string` | Usually `user` or `assistant`. |
| `content` | `string` | Message text shown in the chat. |

### Example request

```http
GET /api/chat/conv-001/history
```

### Example response

```json
{
  "conversation_id": "conv-001",
  "messages": [
    {
      "role": "user",
      "content": "Show me properties in Sylhet for 3 guests this weekend."
    },
    {
      "role": "assistant",
      "content": "I found Tea Garden Retreat in Sylhet for BDT 4300/night."
    },
    {
      "role": "user",
      "content": "Tell me more about that property."
    },
    {
      "role": "assistant",
      "content": "Tea Garden Retreat costs BDT 4300 per night and fits 3 guests."
    }
  ]
}
```

### Possible error responses

`404 Not Found`

```json
{
  "detail": "Conversation not found."
}
```

`500 Internal Server Error`

```json
{
  "detail": "Unable to fetch conversation history right now."
}
```
