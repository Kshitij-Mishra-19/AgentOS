function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to AgentOS</p>

      <div className="cards">

        <div className="card">
          <h3>Total Agents</h3>
          <p>5</p>
        </div>

        <div className="card">
          <h3>Running Tasks</h3>
          <p>3</p>
        </div>

        <div className="card">
          <h3>Completed Tasks</h3>
          <p>7</p>
        </div>

        <div className="card">
          <h3>System Status</h3>
          <p>Online</p>
        </div>

      </div>

      <h2>Active Agents</h2>

      <div className="agents">

        <div className="agent">
          <h3>Planner Agent</h3>
          <p>🟢 Running</p>
        </div>

        <div className="agent">
          <h3>Research Agent</h3>
          <p>🟢 Running</p>
        </div>

        <div className="agent">
          <h3>Code Agent</h3>
          <p>🟡 Working</p>
        </div>

        <div className="agent">
          <h3>Test Agent</h3>
          <p>⚪ Idle</p>
        </div>

        <div className="agent">
          <h3>Documentation Agent</h3>
          <p>⚪ Idle</p>
        </div>

      </div>
    </div>
  )
}

export default Dashboard