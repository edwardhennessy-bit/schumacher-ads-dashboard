"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardCheck,
  Bell,
  Settings,
  Home,
  Bot,
  Facebook,
  Search,
  Monitor,
  FileText,
  Receipt,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const navItems = [
  {
    label: "Overview",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Meta",
    href: "/meta",
    icon: Facebook,
  },
  {
    label: "Google",
    href: "/google",
    icon: Search,
  },
  {
    label: "Microsoft",
    href: "/microsoft",
    icon: Monitor,
  },
  {
    label: "JARVIS",
    href: "/jarvis",
    icon: Bot,
  },
  {
    label: "Reporting",
    href: "/reporting",
    icon: FileText,
  },
  {
    label: "Spend Report",
    href: "/spend-report",
    icon: Receipt,
  },
  {
    label: "Audits",
    href: "/audits",
    icon: ClipboardCheck,
  },
  {
    label: "Alerts",
    href: "/alerts",
    icon: Bell,
  },
  {
    label: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [apiConnected, setApiConnected] = useState(false);

  const [googleConnected, setGoogleConnected] = useState(false);
  const [microsoftConnected, setMicrosoftConnected] = useState(false);

  useEffect(() => {
    api.getStatus()
      .then((status) => {
        setApiConnected(status.meta_connected);
        setGoogleConnected(status.google_connected);
        setMicrosoftConnected(status.microsoft_connected);
      })
      .catch(() => setApiConnected(false));
  }, []);

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-[#2a2a2a] bg-[#1e1e1e]">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-[#2a2a2a] px-6">
          <span className="text-xl">🏠</span>
          <div className="flex flex-col">
            <span className="text-lg font-bold text-white">Schumacher</span>
            <span className="text-xs text-gray-500">Ads Dashboard</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-[#f27038] text-white"
                    : "text-gray-400 hover:bg-white/10 hover:text-white"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-[#2a2a2a] p-4 space-y-2">
          <div className="rounded-lg p-3 bg-white/10">
            <div className="flex items-center gap-2">
              {apiConnected && <span className="w-2 h-2 rounded-full bg-[#f27038] shrink-0" />}
              <p className="text-xs font-medium text-gray-300">
                {apiConnected ? "Meta: Connected" : "Meta: Not Connected"}
              </p>
            </div>
          </div>
          <div className="rounded-lg p-3 bg-white/10">
            <div className="flex items-center gap-2">
              {googleConnected && <span className="w-2 h-2 rounded-full bg-[#f27038] shrink-0" />}
              <p className="text-xs font-medium text-gray-300">
                {googleConnected ? "Google: Connected" : "Google: Not Connected"}
              </p>
            </div>
          </div>
          <div className="rounded-lg p-3 bg-white/10">
            <div className="flex items-center gap-2">
              {microsoftConnected && <span className="w-2 h-2 rounded-full bg-[#f27038] shrink-0" />}
              <p className="text-xs font-medium text-gray-300">
                {microsoftConnected ? "Microsoft: Connected" : "Microsoft: Not Connected"}
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
