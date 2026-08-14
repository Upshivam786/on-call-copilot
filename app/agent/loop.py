"""ReAct agent loop with streaming response."""

import json
from typing import AsyncGenerator, Any

import openai

from app.config import settings
from app.agent.state import AgentState, ToolCall
from app.agent.prompts import SYSTEM_PROMPT, FINAL_SYNTHESIS_PROMPT, get_tool_schemas, format_tools_for_prompt, TOOL_SELECTION_PROMPT
from app.agent.tools import TOOL_REGISTRY
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.agent.tools.search_incidents import SearchIncidentsTool
from app.agent.tools.get_timeline import GetIncidentTimelineTool
from app.agent.tools.query_k8s import QueryK8sTool
from app.agent.tools.draft_postmortem import DraftPostmortemTool


class MockLLMClient:
    """Mock LLM for demo/testing when no OpenAI API key is available."""

    def __init__(self):
        self.call_count = 0

    async def chat_completions_create(self, model, messages, temperature, max_tokens, stream=False, response_format=None):
        self.call_count += 1

        # Determine if this is tool selection or final answer
        last_msg = messages[-1].get("content", "") if messages else ""

        class MockChoice:
            def __init__(self, content):
                self.message = MockMessage(content)
                self.delta = MockDelta(content)

        class MockMessage:
            def __init__(self, content):
                self.content = content

        class MockDelta:
            def __init__(self, content):
                self.content = content

        class MockResponse:
            def __init__(self, choices):
                self.choices = choices

        # Tool selection logic
        if "Available tools:" in last_msg:
            # Simple heuristic: if query mentions incident, use search_incidents
            user_query = ""
            for m in messages:
                if m.get("role") == "user" and "Current query:" in m.get("content", ""):
                    user_query = m["content"]
                    break

            if "incident" in user_query.lower() or "INC-" in user_query.upper():
                tool = "search_incidents"
                args = {"alert_name": "HighErrorRate_payments-api"}
            elif "k8s" in user_query.lower() or "kubernetes" in user_query.lower() or "pod" in user_query.lower():
                tool = "query_k8s"
                args = {"resource": "pods"}
            elif "postmortem" in user_query.lower():
                tool = "draft_postmortem"
                args = {"incident_id": "INC-2026-0142"}
            else:
                tool = "search_knowledge"
                args = {"query": user_query.split("Current query:")[-1].strip() if "Current query:" in user_query else user_query}

            return MockResponse([MockChoice(json.dumps({
                "tool": tool,
                "arguments": args,
                "reasoning": f"Selected {tool} based on query keywords"
            }, separators=(',', ':')))])

        # Final synthesis
        if stream:
            # Stream mock answer
            class MockStream:
                def __init__(self, answer):
                    self.answer = answer
                    self.idx = 0

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.idx >= len(self.answer):
                        raise StopAsyncIteration
                    chunk = self.answer[self.idx]
                    self.idx += 1
                    return MockResponse([MockChoice(chunk)])

            mock_answer = f"Based on my search, here's what I found about your query. [This is a mock response since no OpenAI API key is configured]"
            return MockStream(mock_answer)

        return MockResponse([MockChoice("Mock final answer")])

    async def embeddings_create(self, model, input, dimensions=None):
        class MockEmbedding:
            embedding = [0.0] * 1536

        class MockData:
            data = [MockEmbedding() for _ in input]

        return MockData()


class AgentLoop:
    """ReAct-style agent loop with tool use and streaming."""

    def __init__(
        self,
        max_turns: int = None,
        timeout: int = None,
    ):
        self.max_turns = max_turns or settings.AGENT_MAX_TURNS
        self.timeout = timeout or settings.AGENT_TIMEOUT_SECONDS

        # Use mock LLM if no OpenAI API key
        if settings.OPENAI_API_KEY:
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            print("Warning: No OPENAI_API_KEY set, using mock LLM for demo")
            self.client = MockLLMClient()

        # Initialize tools
        self.tools = {
            "search_knowledge": SearchKnowledgeTool(),
            "search_incidents": SearchIncidentsTool(),
            "get_incident_timeline": GetIncidentTimelineTool(),
            "query_k8s": QueryK8sTool(),
            "draft_postmortem": DraftPostmortemTool(),
        }

    async def run_stream(
        self,
        user_query: str,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Run agent loop and stream responses.
        Yields dicts with: type, content, metadata
        """
        state = AgentState(
            user_query=user_query,
            session_id=session_id or "",
        )
        state.add_user_message(user_query)

        yield {"type": "start", "content": "", "metadata": {"session_id": str(state.session_id)}}

        # Add system prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(state.messages)

        for turn in range(self.max_turns):
            state.turn_count = turn + 1

            # Get tool selection from LLM
            tool_choice = await self._select_tool(messages, user_query)

            if tool_choice.get("tool") == "final":
                # Synthesize final answer
                async for chunk in self._stream_final_answer(messages, state):
                    yield chunk
                break

            # Execute tool
            tool_name = tool_choice["tool"]
            tool_args = tool_choice.get("arguments", {})
            reasoning = tool_choice.get("reasoning", "")

            yield {
                "type": "tool_start",
                "content": f"Using {tool_name}: {reasoning}",
                "metadata": {"tool": tool_name, "arguments": tool_args},
            }

            tool_result = await self._execute_tool(tool_name, tool_args)

            # Record tool call
            tool_call = ToolCall(
                name=tool_name,
                arguments=tool_args,
                result=tool_result,
            )
            state.add_tool_message(tool_call)

            # Extract citations from search results
            if tool_name == "search_knowledge" and "results" in tool_result:
                for r in tool_result["results"]:
                    state.add_citation(
                        chunk_id=r["chunk_id"],
                        document_id=r["document_id"],
                        score=r["score"],
                        snippet=r["content"][:200],
                    )

            yield {
                "type": "tool_result",
                "content": json.dumps(tool_result, default=str)[:2000],
                "metadata": {"tool": tool_name, "result_summary": str(tool_result)[:500]},
            }

            # Add tool result to conversation
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_name,
                    "content": json.dumps(tool_result, default=str),
                }
            )

        else:
            # Max turns reached
            yield {
                "type": "warning",
                "content": f"Max turns ({self.max_turns}) reached. Forcing final synthesis.",
                "metadata": {},
            }
            async for chunk in self._stream_final_answer(messages, state):
                yield chunk

        # Finalize
        yield {
            "type": "complete",
            "content": state.final_answer or "",
            "metadata": {
                "citations": state.citations,
                "tool_calls": [{"name": tc.name, "arguments": tc.arguments} for tc in state.tool_calls],
            },
        }

    async def _select_tool(
        self,
        messages: list[dict],
        user_query: str,
    ) -> dict[str, Any]:
        """Ask LLM to select next tool or finish."""
        tool_prompt = f"""Available tools:
{format_tools_for_prompt()}

Current query: {user_query}

{TOOL_SELECTION_PROMPT.format(tool_names=list(self.tools.keys()))}"""

        # Use mock client if available
        if hasattr(self.client, 'chat_completions_create'):
            response = await self.client.chat_completions_create(
                model=settings.LLM_MODEL,
                messages=messages + [{"role": "user", "content": tool_prompt}],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
        else:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages + [{"role": "user", "content": tool_prompt}],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            return {"tool": "final", "reasoning": "Failed to parse tool selection"}

    async def _execute_tool(self, tool_name: str, arguments: dict) -> dict[str, Any]:
        """Execute a tool by name."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return await self.tools[tool_name].execute(**arguments)
        except Exception as e:
            return {"error": f"Tool {tool_name} failed: {str(e)}"}

    async def _stream_final_answer(
        self,
        messages: list[dict],
        state: AgentState,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream the final synthesized answer."""
        messages.append({"role": "user", "content": FINAL_SYNTHESIS_PROMPT})

        # Use mock client if available
        if hasattr(self.client, 'chat_completions_create'):
            stream = await self.client.chat_completions_create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )
        else:
            stream = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )

        full_answer = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                full_answer += content
                yield {"type": "answer_delta", "content": content, "metadata": {}}

        state.final_answer = full_answer