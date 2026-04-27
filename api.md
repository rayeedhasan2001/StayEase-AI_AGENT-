# API Contract

## POST `/api/chat/{conversation_id}/message`

Send one guest message to the assistant and receive one reply for that turn. Depending on the message, the reply can be a final answer, a follow-up question, or a human handoff message.

### Request schema

1. Path params

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `conversation_id` | `string` | Yes | Unique conversation ID. |

2. JSON body

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `message` | `string` | Yes | Latest guest message. |

### Response schema

| Field | Type | Notes |
| --- | --- | --- |
| `conversation_id` | `string` | Same conversation ID from the path. |
| `reply` | `string` | Final answer, follow-up question, or human handoff message. |
| `escalated` | `boolean` | `true` when the request is handed to a human. |

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
  "reply": "I found these available options:\n1. cox-101 - Sea Breeze Studio, Cox's Bazar - BDT 4800/night\n2. cox-205 - Kolatoli Family Suite, Cox's Bazar - BDT 6200/night",
  "escalated": false
}
```

### Other possible reply styles

1. Follow-up question example

```json
{
  "conversation_id": "conv-002",
  "reply": "What check-in and check-out dates would you like to search for?",
  "escalated": false
}
```

2. Human handoff example

```json
{
  "conversation_id": "conv-003",
  "reply": "I can help with property search, listing details, and booking only. I am handing this conversation to a human agent.",
  "escalated": true
}
```

### Possible error responses

1. `400 Bad Request`

```json
{
  "detail": "Message cannot be empty."
}
```

2. `422 Unprocessable Entity`

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

3. `500 Internal Server Error`

```json
{
  "detail": "Unable to process the conversation right now."
}
```

## GET `/api/chat/{conversation_id}/history`

Return the stored conversation history for one conversation.

### Request schema

1. Path params

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `conversation_id` | `string` | Yes | Conversation ID used in earlier messages. |

### Response schema

| Field | Type | Notes |
| --- | --- | --- |
| `conversation_id` | `string` | Requested conversation ID. |
| `messages` | `array<object>` | Ordered list of guest and assistant messages. |

Each item in `messages` contains:

| Field | Type | Notes |
| --- | --- | --- |
| `role` | `string` | Usually `user` or `assistant`. |
| `content` | `string` | Message text shown in the conversation. |

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
      "content": "I need a room in Cox's Bazar from 2026-05-10 to 2026-05-12 for 2 guests."
    },
    {
      "role": "assistant",
      "content": "I found these available options:\n1. cox-101 - Sea Breeze Studio, Cox's Bazar - BDT 4800/night\n2. cox-205 - Kolatoli Family Suite, Cox's Bazar - BDT 6200/night"
    },
    {
      "role": "user",
      "content": "Tell me more about cox-101."
    },
    {
      "role": "assistant",
      "content": "cox-101 - Sea Breeze Studio is in Cox's Bazar. It costs BDT 4800 per night, fits 2 guests, and includes wifi, ac, breakfast."
    }
  ]
}
```

### Possible error responses

1. `404 Not Found`

```json
{
  "detail": "Conversation not found."
}
```

2. `500 Internal Server Error`

```json
{
  "detail": "Unable to fetch conversation history right now."
}
```
