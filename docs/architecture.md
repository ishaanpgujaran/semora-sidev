# Semora System Architecture

Technical architectural specifications detailing the agent execution pipelines.

---

## ADK Graph Node Layout
1.  **State Init**: Load Git diff context.
2.  **Spec Generation**: Translate diff definitions into Gherkin feature files.
3.  **Sandbox Execution**: Spin isolated environment and execute pytest.
4.  **STRIDE Security Analysis**: Map threats across code modifications.
5.  **Aggregate & Publish**: Write status to console and push REST Firestore document.

*TODO(scaffold-agent): Map class interfaces and network sequences.*
