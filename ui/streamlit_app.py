"""On-Call Copilot Streamlit UI."""

import uuid
import asyncio
import os
import requests
from typing import Generator

import streamlit as st


st.set_page_config(
    page_title="On-Call Copilot",
    page_icon="[!]",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Constants
API_URL = os.getenv("API_URL", "http://localhost:8000") + "/api/v1"


# Session state initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_session_title" not in st.session_state:
    st.session_state.current_session_title = "New Chat"


def create_session() -> str:
    """Create a new chat session."""
    try:
        resp = requests.post(f"{API_URL}/chat/sessions", json={}, timeout=10)
        if resp.status_code == 201:
            return resp.json()["id"]
    except Exception as e:
        st.error(f"Failed to create session: {e}")
    return str(uuid.uuid4())


def get_sessions() -> list[dict]:
    """Get list of chat sessions."""
    try:
        resp = requests.get(f"{API_URL}/chat/sessions", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def get_messages(session_id: str) -> list[dict]:
    """Get messages for a session."""
    try:
        resp = requests.get(f"{API_URL}/chat/sessions/{session_id}/messages", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def stream_chat(query: str, session_id: str) -> Generator[dict, None, None]:
    """Stream chat response from API."""
    try:
        with requests.post(
            f"{API_URL}/chat/stream",
            json={"query": query, "session_id": session_id},
            stream=True,
            timeout=60,
        ) as resp:
            for line in resp.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json

                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        yield {"type": "error", "content": str(e)}


# Sidebar
with st.sidebar:
    st.title("[!] On-Call Copilot")
    st.markdown("---")

    # New chat button
    if st.button("New Chat", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.session_state.current_session_title = "New Chat"
        st.rerun()

    st.markdown("### Sessions")

    sessions = get_sessions()
    for sess in sessions:
        title = sess.get("title") or "Untitled"
        if st.button(
            f"[C] {title[:30]}",
            key=f"session_{sess['id']}",
            use_container_width=True,
        ):
            st.session_state.session_id = sess["id"]
            st.session_state.current_session_title = title
            msgs = get_messages(sess["id"])
            st.session_state.messages = msgs
            st.rerun()

    st.markdown("---")
    st.caption("v0.1.0 | Demo Mode")

# Main chat area
st.title(f"[!] {st.session_state.current_session_title}")

# Create session if needed
if st.session_state.session_id is None:
    st.session_state.session_id = create_session()

# Display messages
for msg in st.session_state.messages:
    role = msg.get("role", "user")
    content = msg.get("content", "")

    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.markdown(content)
            # Show citations if present
            citations = msg.get("citations")
            if citations:
                with st.expander(f"Citations ({len(citations)})"):
                    for i, c in enumerate(citations, 1):
                        st.markdown(
                            f"**[{i}]** {c.get('snippet', 'No snippet')}  "
                            f"`chunk:{c.get('chunk_id', '')[:8]} doc:{c.get('document_id', '')[:8]}` "
                            f"(score: {c.get('score', 0):.3f})"
                        )
    elif role == "tool":
        with st.chat_message("assistant"):
            st.markdown(f"[TOOL] *Tool output: {content[:200]}...*")

# Chat input
if prompt := st.chat_input("Ask about an alert, incident, or runbook..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        citations = []

        for event in stream_chat(prompt, st.session_state.session_id):
            event_type = event.get("type", "")

            if event_type == "answer_delta":
                full_response += event.get("content", "")
                placeholder.markdown(full_response + "|")
            elif event_type == "tool_start":
                st.toast(f"[TOOL] {event.get('content', '')}")
            elif event_type == "tool_result":
                st.toast(f"[OK] Tool completed")
            elif event_type == "complete":
                citations = event.get("metadata", {}).get("citations", [])
            elif event_type == "error":
                st.error(event.get("content", ""))

        placeholder.markdown(full_response)

        # Show citations
        if citations:
            with st.expander(f"Citations ({len(citations)})"):
                for i, c in enumerate(citations, 1):
                    st.markdown(
                        f"**[{i}]** {c.get('snippet', 'No snippet')}  "
                        f"`chunk:{c.get('chunk_id', '')[:8]} doc:{c.get('document_id', '')[:8]}` "
                        f"(score: {c.get('score', 0):.3f})"
                    )

    # Add to history
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full_response,
            "citations": citations,
        }
    )
