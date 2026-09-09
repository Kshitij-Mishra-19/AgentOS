function Tasks() {
  return (
    <div>
      <h1>Tasks</h1>
      <p>Manage and monitor AgentOS tasks</p>

      <div className="tasks">

        <div className="task">
          <h3>Research latest AI trends</h3>
          <p>Assigned to: Research Agent</p>
          <p>🟢 Running</p>
        </div>

        <div className="task">
          <h3>Generate project plan</h3>
          <p>Assigned to: Planner Agent</p>
          <p>🟢 Running</p>
        </div>

        <div className="task">
          <h3>Test application</h3>
          <p>Assigned to: Test Agent</p>
          <p>⚪ Pending</p>
        </div>

      </div>
    </div>
  )
}

export default Tasks