import { useEffect, useState } from "react";

export default function Agents() {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    fetch("/api/agents")
      .then((r) => r.json())
      .then(setAgents)
      .catch(() => {});
  }, []);

  return (
    <div>
      <h1>Agents</h1>
      <p>Available agents in AgentOS</p>

      <div className="agents" style={{ marginTop: 24 }}>
        {agents.map((agent) => (
          <div className="agent" key={agent.type}>
            <h3>{agent.name}</h3>
            <p style={{ color: "#6b7280", fontSize: 14, margin: "8px 0" }}>{agent.description}</p>
            <p>🟢 Ready</p>
          </div>
        ))}
      </div>
    </div>
  );
}
