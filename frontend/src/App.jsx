import Tasks from "./pages/Tasks";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Agents from "./pages/Agents";
import Run from "./pages/Run";
import "./App.css";

function Sidebar() {
  const location = useLocation();
  const links = [
    { to: "/", label: "Dashboard" },
    { to: "/run", label: "▶ Run Agent" },
    { to: "/agents", label: "Agents" },
    { to: "/tasks", label: "Tasks" },
  ];
  return (
    <aside className="sidebar">
      <h2>AgentOS</h2>
      <nav>
        {links.map((l) => (
          <Link key={l.to} to={l.to} className={location.pathname === l.to ? "active" : ""}>
            {l.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/run" element={<Run />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/tasks" element={<Tasks />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
