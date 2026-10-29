import { useEffect, useRef, useState } from "react";

const STATUS_ICON = {
  pending:   "⚪",
  ready:     "🔵",
  running:   "🟡",
  completed: "🟢",
  failed:    "🔴",
};

function downloadFile(filename, content) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function extractCode(result) {
  // Extract first code block if present
  const match = result.match(/```(?:\w+)?\n([\s\S]*?)```/);
  return match ? match[1].trim() : result;
}

function getExtension(agentType) {
  if (agentType === "testing") return "py";
  if (agentType === "coding") return "py";
  return "md";
}

function JobCard({ job, index }) {
  const [open, setOpen] = useState(true);

  const icon = STATUS_ICON[job.status] || "⚪";
  const hasResult = !!job.result;

  const handleDownload = () => {
    const ext = getExtension(job.agent_type);
    const content = ext === "py" ? extractCode(job.result) : job.result;
    const name = `${index + 1}_${job.agent_type}_${job.name.replace(/\s+/g, "_").slice(0, 40)}.${ext}`;
    downloadFile(name, content);
  };

  return (
    <div className="job-card">
      <div className="job-header" onClick={() => setOpen(!open)}>
        <span>{icon}</span>
        <span className="job-agent-badge" data-type={job.agent_type}>{job.agent_type}</span>
        <span className="job-name">{job.name}</span>
        <div className="job-header-actions">
          {hasResult && (
            <button
              className="download-btn"
              onClick={(e) => { e.stopPropagation(); handleDownload(); }}
              title="Download file"
            >
              ⬇ Download
            </button>
          )}
          <span className="job-toggle">{open ? "▲" : "▼"}</span>
        </div>
      </div>

      {open && (
        <div className="job-body">
          {hasResult ? (
            <pre className="job-result">{job.result}</pre>
          ) : job.status === "running" ? (
            <div className="job-loading">⏳ Agent is working...</div>
          ) : job.error ? (
            <div className="job-error">❌ {job.error}</div>
          ) : (
            <div className="job-loading">Waiting...</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Run() {
  const [goal, setGoal] = useState("");
  const [runId, setRunId] = useState(() => localStorage.getItem("lastRunId") || null);
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const startRun = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setError(null);
    setRun(null);
    setRunId(null);
    localStorage.removeItem("lastRunId");

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setRunId(data.run_id);
      localStorage.setItem("lastRunId", data.run_id);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  // Poll for status
  useEffect(() => {
    if (!runId) return;

    const poll = async () => {
      try {
        const res = await fetch(`/api/run/${runId}`);
        if (!res.ok) {
          // Run not found (e.g. server restarted) — clear stale state
          clearInterval(pollRef.current);
          setRunId(null);
          setRun(null);
          setLoading(false);
          localStorage.removeItem("lastRunId");
          return;
        }
        const data = await res.json();
        setRun(data);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(pollRef.current);
          setLoading(false);
        }
      } catch {}
    };

    poll();
    pollRef.current = setInterval(poll, 2000);
    return () => clearInterval(pollRef.current);
  }, [runId]);

  const handleDownloadAll = () => {
    if (!run?.jobs) return;
    run.jobs.forEach((job, i) => {
      if (!job.result) return;
      const ext = getExtension(job.agent_type);
      const content = ext === "py" ? extractCode(job.result) : job.result;
      const name = `${i + 1}_${job.agent_type}_${job.name.replace(/\s+/g, "_").slice(0, 40)}.${ext}`;
      setTimeout(() => downloadFile(name, content), i * 200);
    });
  };

  return (
    <div className="run-page">
      <h1>Run Agent</h1>
      <p className="run-subtitle">Describe your goal — agents will research, code, and test it.</p>

      <div className="goal-box">
        <textarea
          className="goal-input"
          placeholder="e.g. Build a Python REST API for a todo list..."
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); startRun(); } }}
          rows={3}
          disabled={loading}
        />
        <button className="run-btn" onClick={startRun} disabled={loading || !goal.trim()}>
          {loading ? "Running..." : "▶ Run"}
        </button>
      </div>

      {error && <div className="run-error">⚠ {error}</div>}

      {run && (
        <div className="run-results">

          {/* Status bar */}
          <div className="run-meta">
            <span className={`run-status run-status--${run.status}`}>{run.status?.toUpperCase()}</span>
            <span className="run-goal-label">"{run.goal}"</span>
            {run.status === "completed" && run.jobs.length > 0 && (
              <button className="download-all-btn" onClick={handleDownloadAll}>⬇ Download All</button>
            )}
          </div>

          {/* Plan */}
          {run.tasks.length > 0 && (
            <div className="run-plan">
              <h3>Plan — {run.tasks.length} tasks</h3>
              <div className="plan-steps">
                {run.tasks.map((t, i) => (
                  <div key={i} className="plan-step">
                    <span className="plan-num">{i + 1}</span>
                    <span className="job-agent-badge" data-type={t.agent_type}>{t.agent_type}</span>
                    <span>{t.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Jobs */}
          {run.jobs.length > 0 ? (
            <div className="run-jobs">
              <h3>Output</h3>
              {run.jobs.map((job, i) => (
                <JobCard key={job.id} job={job} index={i} />
              ))}
            </div>
          ) : run.status === "running" || run.status === "planning" ? (
            <div className="run-plan">
              <div className="job-loading">⏳ Agents are working on your goal...</div>
            </div>
          ) : null}

          {run.error && <div className="run-error">❌ {run.error}</div>}
        </div>
      )}
    </div>
  );
}
