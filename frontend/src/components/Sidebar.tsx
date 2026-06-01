import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, GitMerge, FileText, Activity, Clock, Database, MessageCircle, X } from 'lucide-react';
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { APP_ROUTES } from '../constants/appRoutes';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const Sidebar = ({ isOpen, onClose }: SidebarProps) => {
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
    <aside className={cn(
      "w-64 bg-slate-900 text-white h-screen flex flex-col fixed left-0 top-0 z-50 transition-transform duration-300 ease-in-out border-r border-slate-800",
      isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
    )}>
      <div className="p-4 text-xl font-bold border-b border-slate-800 flex justify-between items-center">
        <span className="truncate">{import.meta.env.VITE_APP_NAME || "Devinder AI Agent Studio"}</span>
        <button
          onClick={onClose}
          aria-label="Close navigation"
          className="lg:hidden p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer"
        >
          <X size={20} />
        </button>
      </div>
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
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
    </aside>
  );
};

export default Sidebar;
