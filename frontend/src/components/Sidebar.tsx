import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, GitMerge, FileText, Activity, Clock, Database, MessageCircle } from 'lucide-react';
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { APP_ROUTES } from '../constants/appRoutes';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const Sidebar = () => {
  const links = [
    { to: APP_ROUTES.DASHBOARD, icon: <LayoutDashboard size={20} />, label: "Dashboard" },
    { to: APP_ROUTES.AGENTS, icon: <Users size={20} />, label: "Agents" },
    { to: APP_ROUTES.WORKFLOWS, icon: <GitMerge size={20} />, label: "Workflows" },
    { to: APP_ROUTES.TEMPLATES, icon: <FileText size={20} />, label: "Templates" },
    { to: APP_ROUTES.RUNS, icon: <Activity size={20} />, label: "Runs" },
    { to: APP_ROUTES.SCHEDULES, icon: <Clock size={20} />, label: "Schedules" },
    { to: APP_ROUTES.MEMORY, icon: <Database size={20} />, label: "Memory" },
    { to: APP_ROUTES.CHANNELS, icon: <MessageCircle size={20} />, label: "Channels" },
  ];

  return (
    <div className="w-64 bg-slate-900 text-white h-screen flex flex-col fixed left-0 top-0">
      <div className="p-4 text-xl font-bold border-b border-slate-800">
        Yuno Agent Studio
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              cn(
                "flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors",
                isActive ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )
            }
          >
            {link.icon}
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
};

export default Sidebar;
