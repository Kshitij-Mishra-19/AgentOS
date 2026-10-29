import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then(setRuns)
      .catch(() => {});
  }, []);

  const completed = runs.filter((r) => r.status === "completed").length;
  const running   = runs.filter((r) => r.status === "running" || r.status === "planning").length;
  const failed    = runs.filter((r) => r.status === "failed").length;

  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to AgentOS</p>

      <div className="cards">
        <div className="card"><h3>Total Runs</h3><p>{runs.length}</p></div>
        <div className="card"><h3>Running</h3><p>{running}</p></div>
        <div className="card"><h3>Completed</h3><p>{completed}</p></div>
        <div className="card"><h3>Failed</h3><p>{failed}</p></div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Recent Runs</h2>
        <Link to="/run" className="run-link-btn">+ New Run</Link>
      </div>

      {runs.length === 0 ? (
        <p style={{ color: "#9ca3af" }}>No runs yet. <Link to="/run">Start your first run →</Link></p>
      ) : (
        <div className="recent-runs">
          {[...runs].reverse().slice(0, 5).map((run) => (
            <div key={run.id} className="recent-run-item">
              <span className={`run-status run-status--${run.status}`}>{run.status}</span>
              <span className="recent-run-goal">{run.goal}</span>
              <span className="recent-run-jobs">{run.jobs.length} tasks</span>
            </div>
          ))}
        </div>
      )}

      <h2 style={{ marginTop: 32 }}>Agents</h2>
      <div className="agents">
        {["Planner Agent", "Research Agent", "Coding Agent", "Testing Agent"].map((name) => (
          <div className="agent" key={name}>
            <h3>{name}</h3>
            <p>🟢 Ready</p>
          </div>
        ))}
      </div>
    </div>
  );
}
