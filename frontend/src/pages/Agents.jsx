function Agents() {
  const agents = [
    {
      name: "Planner Agent",
      status: "Running"
    },
    {
      name: "Research Agent",
      status: "Running"
    },
    {
      name: "Code Agent",
      status: "Working"
    },
    {
      name: "Test Agent",
      status: "Idle"
    },
    {
      name: "Documentation Agent",
      status: "Idle"
    }
  ]

  return (
    <div>
      <h1>Agents</h1>
      <p>Manage and monitor AgentOS agents</p>

      <div className="agents">
        {agents.map((agent) => (
          <div className="agent" key={agent.name}>
            <h3>{agent.name}</h3>
            <p>{agent.status}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Agents