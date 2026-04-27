# StayEase AI Agent

This project is a small AI agent design for StayEase, a short-term rental platform in Bangladesh. I used a lightweight orchestrator first, then a small LangGraph executor. The orchestrator handles intent detection and parameter extraction. After that, the executor runs one operation-specific node for search, details, or booking. If important information is missing, the agent asks a follow-up question. If the request goes outside these three supported actions, it keeps a human in the loop.

## 1. System Overview

```mermaid
flowchart TD
    Guest[Guest Message]
    API[FastAPI Backend]
    LLM[Groq / OpenRouter LLM]
    DB[(PostgreSQL)]
    Human[Human Agent]
    Reply[Response Back To Guest]
    FollowUp[Follow-up Question]

    Guest --> API
    API --> Detect

    subgraph Orchestrator Chain
        Detect[detect_intent_and_route]
        Extract[extract_query_params]
    end

    Detect <--> LLM
    Detect --> IntentCheck{Supported intent?}
    IntentCheck -->|No| Human
    IntentCheck -->|Yes| Extract
    Extract <--> LLM
    Extract --> ParamCheck{Missing fields?}
    ParamCheck -->|Yes| FollowUp
    FollowUp --> Reply

    ParamCheck -->|No| Router

    subgraph Executor Agent (LangGraph)
        Router{Conditional entry}
        SearchNode[search_node]
        DetailsNode[details_node]
        BookNode[book_node]
    end

    Router --> SearchNode
    Router --> DetailsNode
    Router --> BookNode

    SearchNode --> SearchTool[search_available_properties]
    DetailsNode --> DetailsTool[get_listing_details]
    BookNode --> BookTool[create_booking]

    SearchTool --> DB
    DetailsTool --> DB
    BookTool --> DB

    SearchNode --> Reply
    DetailsNode --> Reply
    BookNode --> Reply
    Human --> Reply
    Reply --> API
    API --> Guest
```

## 2. Conversation Flow

Example guest message: "I need a room in Cox's Bazar from 2026-05-10 to 2026-05-12 for 2 guests."

1. The guest message is sent to `POST /api/chat/{conversation_id}/message`.
2. FastAPI loads the earlier conversation history and sends the latest message to the orchestrator.
3. `detect_intent_and_route` classifies the message as `search` and returns `search_node` as the executor target.
4. `extract_query_params` reads the message and history, then returns a clean input object:

```json
{
  "location": "Cox's Bazar",
  "check_in": "2026-05-10",
  "check_out": "2026-05-12",
  "guests": 2
}
```

5. Because the required fields are present, FastAPI sends the request into the LangGraph executor.
6. The graph enters `search_node`.
7. `search_node` calls `search_available_properties`, which checks PostgreSQL for matching listings.
8. The tool returns available properties such as `cox-101 - Sea Breeze Studio - BDT 4,800 per night` and `cox-205 - Kolatoli Family Suite - BDT 6,200 per night`.
9. `search_node` builds the final reply and returns it to FastAPI.
10. FastAPI stores the user message and assistant reply in conversation history, then sends the response back to the guest.

If some required search fields are missing, the orchestrator does not call LangGraph yet. It asks a follow-up question first. If the request is outside search, details, or booking, the API returns a human handoff message.

## 3. LangGraph State Design

The LangGraph state is only for the executor layer. The orchestrator runs before the graph and passes structured data into it.

| Field | Type | Why it is needed |
| --- | --- | --- |
| `conversation_id` | `str` | Keeps the executor run linked to the active conversation. |
| `messages` | `list[dict[str, str]]` | Holds the earlier conversation plus the newest user turn. |
| `user_message` | `str` | Stores the latest guest message for reference. |
| `intent` | `Literal["search", "details", "book", "escalate"]` | Stores the intent returned by the orchestrator. |
| `executor_target` | `Literal["search_node", "details_node", "book_node"]` | Tells the graph which node to enter. |
| `tool_input` | `ToolInput` | Stores the clean structured input prepared by `extract_query_params`. |
| `tool_result` | `dict[str, Any] \| None` | Stores the result returned by the business tool. |
| `final_response` | `str \| None` | Stores the final guest-facing reply. |
| `needs_human` | `bool` | Marks cases where the executor could not safely finish and should hand off. |

## 4. Node Design

The executor graph has only 3 nodes.

| Node | What it does | What it updates | Next node |
| --- | --- | --- | --- |
| `search_node` | Handles search requests end-to-end and calls `search_available_properties`. | `tool_result`, `final_response`, `needs_human` | `END` |
| `details_node` | Handles property detail requests end-to-end and calls `get_listing_details`. | `tool_result`, `final_response`, `needs_human` | `END` |
| `book_node` | Handles booking requests end-to-end and calls `create_booking`. | `tool_result`, `final_response`, `needs_human` | `END` |

## 5. Tool Definitions

There are 2 orchestrator tools and 3 business tools.

### 5.1 `detect_intent_and_route`

1. Input parameters

| Field | Type |
| --- | --- |
| `message` | `str` |
| `messages` | `list[dict[str, str]]` |

2. Output format

```json
{
  "intent": "search",
  "executor_target": "search_node",
  "needs_human": false
}
```

3. Used when

This is the first tool called. It decides whether the guest wants search, details, booking, or human escalation.

### 5.2 `extract_query_params`

1. Input parameters

| Field | Type |
| --- | --- |
| `intent` | `str` |
| `message` | `str` |
| `messages` | `list[dict[str, str]]` |

2. Output format

```json
{
  "tool_input": {
    "location": "Cox's Bazar",
    "check_in": "2026-05-10",
    "check_out": "2026-05-12",
    "guests": 2
  },
  "missing_fields": [],
  "follow_up_question": null
}
```

3. Used when

This is the second tool called. It extracts structured fields from the latest message and earlier history. If something is missing, it prepares the follow-up question instead of sending the request into LangGraph.

### 5.3 `search_available_properties`

1. Input parameters

| Field | Type |
| --- | --- |
| `location` | `str` |
| `check_in` | `date` |
| `check_out` | `date` |
| `guests` | `int` |

2. Output format

```json
{
  "results": [
    {
      "listing_id": "cox-101",
      "title": "Sea Breeze Studio",
      "location": "Cox's Bazar",
      "price_bdt": 4800,
      "max_guests": 2
    }
  ],
  "count": 1
}
```

3. Used when

Called by `search_node` after the orchestrator has already prepared a complete search input.

### 5.4 `get_listing_details`

1. Input parameters

| Field | Type |
| --- | --- |
| `listing_id` | `str` |

2. Output format

```json
{
  "listing_id": "cox-101",
  "title": "Sea Breeze Studio",
  "description": "Private studio near Kolatoli beach.",
  "location": "Cox's Bazar",
  "price_bdt": 4800,
  "max_guests": 2,
  "amenities": ["wifi", "ac", "breakfast"]
}
```

3. Used when

Called by `details_node` after the orchestrator has identified which listing the guest wants to inspect.

### 5.5 `create_booking`

1. Input parameters

| Field | Type |
| --- | --- |
| `listing_id` | `str` |
| `guest_name` | `str` |
| `check_in` | `date` |
| `check_out` | `date` |
| `guests` | `int` |

2. Output format

```json
{
  "booking_id": "bk-demo-001",
  "listing_id": "cox-101",
  "status": "confirmed",
  "total_price_bdt": 9600
}
```

3. Used when

Called by `book_node` after the orchestrator has all required booking information.

## 6. Database Schema Design

Only 3 tables are used in this design.

### `listings`

| Column | Type |
| --- | --- |
| `id` | `UUID PRIMARY KEY` |
| `title` | `VARCHAR(150)` |
| `description` | `TEXT` |
| `location` | `VARCHAR(120)` |
| `price_bdt` | `INTEGER` |
| `max_guests` | `INTEGER` |
| `amenities` | `JSONB` |
| `is_active` | `BOOLEAN` |
| `created_at` | `TIMESTAMP` |

### `bookings`

| Column | Type |
| --- | --- |
| `id` | `UUID PRIMARY KEY` |
| `listing_id` | `UUID REFERENCES listings(id)` |
| `guest_name` | `VARCHAR(120)` |
| `check_in` | `DATE` |
| `check_out` | `DATE` |
| `guests` | `INTEGER` |
| `total_price_bdt` | `INTEGER` |
| `status` | `VARCHAR(30)` |
| `created_at` | `TIMESTAMP` |

### `conversations`

| Column | Type |
| --- | --- |
| `id` | `UUID PRIMARY KEY` |
| `conversation_id` | `VARCHAR(80)` |
| `role` | `VARCHAR(20)` |
| `message` | `TEXT` |
| `metadata` | `JSONB` |
| `created_at` | `TIMESTAMP` |
