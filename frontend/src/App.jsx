import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Agents from "./pages/Agents";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app">

        {/* Sidebar */}
        <aside className="sidebar">
          <h2>AgentOS</h2>

          <nav>
            <Link to="/">Dashboard</Link>
            <Link to="/agents">Agents</Link>
            <Link to="/tasks">Tasks</Link>
            <Link to="/scheduler">Scheduler</Link>
            <Link to="/memory">Memory</Link>
            <Link to="/tools">Tools</Link>
            <Link to="/plugins">Plugins</Link>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="main">
          <Routes>
  <Route path="/" element={<Dashboard />} />
  <Route path="/agents" element={<Agents />} />
</Routes>
        </main>

      </div>
    </BrowserRouter>
  );
}

export default App;
