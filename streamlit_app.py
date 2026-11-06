import os
import uuid

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CONVERSATION_SESSION_KEY = "conversation_session_id"


def backend_error_detail(response):
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    return response.text or f"Backend returned HTTP {response.status_code}."


st.set_page_config(page_title="Zenith RAG Platform", page_icon="🧠")

if CONVERSATION_SESSION_KEY not in st.session_state:
    st.session_state[CONVERSATION_SESSION_KEY] = str(uuid.uuid4())

st.title("Zenith: Multi-Modal Architecture Review Assistant")

with st.sidebar:
    st.subheader("Conversation")
    st.caption("Follow-up questions share context within this browser session.")
    if st.button("Clear conversation memory"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/clear-session",
                json={"session_id": st.session_state[CONVERSATION_SESSION_KEY]},
                timeout=15,
            )
            response.raise_for_status()
            st.session_state[CONVERSATION_SESSION_KEY] = str(uuid.uuid4())
            st.session_state.pop("latest_query_result", None)
            st.success("Conversation memory cleared.")
        except requests.HTTPError as exc:
            detail = (
                backend_error_detail(exc.response)
                if exc.response is not None
                else str(exc)
            )
            st.error(f"Could not clear conversation memory: {detail}")
        except requests.RequestException as exc:
            st.error(f"Could not clear conversation memory: {exc}")

    if st.button("Reset Knowledge Base (Delete all indexed docs)"):
        try:
            response = requests.post(f"{BACKEND_URL}/api/clear", timeout=15)
            response.raise_for_status()
            st.session_state.pop("latest_query_result", None)
            st.session_state.pop("active_document", None)
            st.success("Knowledge base cleared! Saare purane documents delete ho gaye.")
            st.rerun()
        except requests.RequestException as exc:
            st.error(f"Could not clear knowledge base: {exc}")

    # Fetch currently indexed documents
    indexed_doc_items = []
    try:
        doc_resp = requests.get(f"{BACKEND_URL}/api/documents", timeout=5)
        if doc_resp.ok:
            indexed_doc_items = doc_resp.json().get("documents", [])
    except Exception:
        pass

    if indexed_doc_items:
        st.caption("📁 **Currently Indexed Documents:**")
        for item in indexed_doc_items:
            doc_name = item.get("document_name", "unknown")
            chunks = item.get("chunks", 1)
            col_doc, col_del = st.columns([4, 1])
            with col_doc:
                st.caption(f"• {doc_name} ({chunks} chunks)")
            with col_del:
                if st.button("✕", key=f"del_{doc_name}", help=f"Delete {doc_name}"):
                    try:
                        requests.delete(f"{BACKEND_URL}/api/documents/{doc_name}", timeout=10)
                        if st.session_state.get("active_document") == doc_name:
                            st.session_state.pop("active_document", None)
                        st.session_state.pop("latest_query_result", None)
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    st.divider()
    st.header("Upload documents")
    clear_before_upload = st.checkbox(
        "Clear old documents before uploading (Fresh review)",
        value=False,
        help="Check this if you want to wipe previous files and focus ONLY on this new document."
    )
    document_type = st.selectbox(
        "Index this as",
        options=["knowledge", "standard", "design"],
        help="Choose standard for internal policies used by compliance reviews.",
    )
    uploaded_file = st.file_uploader(
        "Choose a PDF, text document, or architecture diagram",
        type=["pdf", "txt", "md", "png", "jpg", "jpeg", "webp"],
    )
    if uploaded_file is not None:
        if st.button("Upload and index", type="primary"):
            if clear_before_upload:
                try:
                    requests.post(f"{BACKEND_URL}/api/clear", timeout=15)
                except Exception:
                    pass
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")}
            response = requests.post(
                f"{BACKEND_URL}/api/upload",
                files=files,
                data={"document_type": document_type},
                timeout=60,
            )
            if response.ok:
                st.session_state["active_document"] = uploaded_file.name
                st.session_state.pop("latest_query_result", None)
                st.success(f"✅ {response.json()['message']} Target document set to: {uploaded_file.name}")
                st.rerun()
            else:
                st.error(f"Upload failed: {backend_error_detail(response)}")

    st.divider()
    st.subheader("Index a GitHub repository")
    st.caption("Paste GitHub repository URL or enter owner and repository:")
    github_owner = st.text_input("GitHub URL / Owner", key="github_owner", placeholder="e.g. https://github.com/owner/repository")
    github_repository = st.text_input("Repository (optional if full URL entered above)", key="github_repository", placeholder="e.g. repository-name")
    if st.button("Queue repository indexing"):
        owner = (github_owner or "").strip().rstrip("/")
        repo = (github_repository or "").strip().rstrip("/")
        if "github.com/" in owner:
            parts = owner.split("github.com/")[-1].strip("/").split("/")
            owner = parts[0]
            if len(parts) >= 2 and not repo:
                repo = parts[1]
        if "github.com/" in repo:
            parts = repo.split("github.com/")[-1].strip("/").split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
            elif len(parts) == 1:
                repo = parts[0]
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/index/github",
                json={"owner": owner, "repository": repo},
                timeout=15,
            )
            response.raise_for_status()
            job = response.json()
            st.session_state["github_index_job_id"] = job["job_id"]
            st.success(f"Indexing queued: {job['job_id']}")
        except requests.HTTPError as exc:
            detail = (
                backend_error_detail(exc.response)
                if exc.response is not None
                else str(exc)
            )
            st.error(f"Could not queue repository indexing: {detail}")
        except requests.RequestException as exc:
            st.error(f"Could not queue repository indexing: {exc}")

    job_id = st.session_state.get("github_index_job_id")
    if job_id and st.button("Check indexing status"):
        with st.spinner("Checking status..."):
            try:
                response = requests.get(
                    f"{BACKEND_URL}/api/index/jobs/{job_id}",
                    timeout=15,
                )
                response.raise_for_status()
                job = response.json()
                if job["status"] == "PENDING":
                    st.info("⏳ Status: PENDING — Repo me 400+ files hain, background me AI embeddings calculate ho rahi hain (~30s). Kripya thoda wait karke dobara button dabayein.")
                elif job["status"] == "SUCCESS":
                    st.success("✅ Status: SUCCESS — Repository completely indexed!")
                    if job.get("result"):
                        st.json(job["result"])
                elif job["status"] == "FAILURE":
                    st.error(f"❌ Status: FAILURE — {job.get('error')}")
                else:
                    st.write(f"Status: {job['status']}")
            except requests.HTTPError as exc:
                detail = (
                    backend_error_detail(exc.response)
                    if exc.response is not None
                    else str(exc)
                )
                st.error(f"Could not fetch indexing status: {detail}")
            except requests.RequestException as exc:
                st.error(f"Could not fetch indexing status: {exc}")

st.subheader("Ask about your system architecture")
st.info("💬 **Query Box:** Apne uploaded documents ya indexed GitHub repository ke bare me sawaal poochne ke liye neeche diye gaye box me likhein aur **'Generate review'** click karein:")

available_docs = [item["document_name"] for item in indexed_doc_items] if indexed_doc_items else []
selected_doc = None
if available_docs:
    active = st.session_state.get("active_document")
    options = ["All Indexed Documents"] + available_docs
    default_idx = options.index(active) if (active and active in options) else 0
    chosen = st.selectbox(
        "🎯 Review Target (Document Scope):",
        options=options,
        index=default_idx,
        help="Select a specific document to only review that document without mixing in other files."
    )
    if chosen != "All Indexed Documents":
        selected_doc = chosen

question = st.text_area("What do you want reviewed? (Query Box - Type question here)", value="How should we design the service boundaries for this architecture?", height=120)

if st.button("Generate review") and question.strip():
    try:
        query_payload = {
            "question": question,
            "top_k": 5,
            "session_id": st.session_state[CONVERSATION_SESSION_KEY],
        }
        if selected_doc:
            query_payload["document_name"] = selected_doc

        response = requests.post(
            f"{BACKEND_URL}/api/query",
            json=query_payload,
            timeout=60,
        )
        response.raise_for_status()
        st.session_state["latest_query_result"] = response.json()
        st.session_state["feedback_rating"] = "Select a rating"
        st.session_state["feedback_comment"] = ""
        st.session_state.pop("feedback_submitted_interaction", None)
    except requests.HTTPError as exc:
        detail = (
            backend_error_detail(exc.response)
            if exc.response is not None
            else str(exc)
        )
        st.error(f"Architecture review failed: {detail}")
    except requests.RequestException as exc:  # pragma: no cover
        st.error(f"Failed to reach backend: {exc}")

result = st.session_state.get("latest_query_result")
if result:
    st.markdown("### Architecture Review")
    st.write(result["answer"])

    if result.get("sources"):
        st.markdown("### Retrieved Context")
        for source in result["sources"]:
            source_label = (
                f"{source['document_name']} • rerank {source['score']:.3f}"
            )
            if source.get("similarity_score") is not None:
                source_label += f" • similarity {source['similarity_score']:.3f}"
            source_path = source.get("path") or source.get("source_path")
            if source_path:
                source_label += f" • {source_path}"
            if source.get("line_start") is not None:
                line_end = source.get("line_end", source["line_start"])
                source_label += f":{source['line_start']}-{line_end}"
            if source.get("page_number") is not None:
                source_label += f" • page {source['page_number']}"
            if source.get("source_type") == "image_caption":
                source_label += " • diagram caption"
            st.caption(source_label)
            st.write(source["snippet"])

    interaction_id = result.get("interaction_id")
    if interaction_id:
        if st.session_state.get("feedback_submitted_interaction") == interaction_id:
            st.success("Feedback recorded. Thank you.")
        else:
            st.markdown("### Rate this answer")
            rating = st.selectbox(
                "Rate this answer",
                options=["Select a rating", "1", "2", "3", "4", "5"],
                key="feedback_rating",
            )
            comment = st.text_area("Feedback comment", key="feedback_comment")
            if st.button("Send feedback"):
                if rating == "Select a rating":
                    st.warning("Choose a rating from 1 to 5.")
                else:
                    try:
                        feedback_response = requests.post(
                            f"{BACKEND_URL}/api/feedback",
                            json={
                                "interaction_id": interaction_id,
                                "rating": int(rating),
                                "comment": comment or None,
                            },
                            timeout=15,
                        )
                        feedback_response.raise_for_status()
                        st.session_state["feedback_submitted_interaction"] = (
                            interaction_id
                        )
                        st.success("Feedback recorded. Thank you.")
                    except requests.HTTPError as exc:
                        detail = (
                            backend_error_detail(exc.response)
                            if exc.response is not None
                            else str(exc)
                        )
                        st.error(f"Could not submit feedback: {detail}")
                    except requests.RequestException as exc:
                        st.error(f"Could not submit feedback: {exc}")

st.divider()
st.subheader("Check design against internal standards")
design = st.text_area(
    "Proposed design",
    key="compliance_design",
    placeholder="Describe the design you want checked against uploaded standards.",
)

if st.button("Run compliance review") and design.strip():
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/compliance-review",
            json={"design": design, "top_k": 5},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        st.markdown(f"**Status: {result['status']}**")
        st.write(result["review"])
        if result.get("sources"):
            st.markdown("#### Standards used")
            for source in result["sources"]:
                source_label = f"{source['document_name']} • {source['chunk_id']}"
                source_path = source.get("path") or source.get("source_path")
                if source_path:
                    source_label += f" • {source_path}"
                if source.get("line_start") is not None:
                    line_end = source.get("line_end", source["line_start"])
                    source_label += f":{source['line_start']}-{line_end}"
                st.caption(source_label)
                st.write(source["snippet"])
    except requests.HTTPError as exc:
        detail = (
            backend_error_detail(exc.response)
            if exc.response is not None
            else str(exc)
        )
        st.error(f"Compliance review failed: {detail}")
    except requests.RequestException as exc:  # pragma: no cover
        st.error(f"Compliance review failed: {exc}")
