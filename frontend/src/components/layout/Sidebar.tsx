"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Megaphone,
  ClipboardCheck,
  Bell,
  Settings,
  Home,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const navItems = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "JARVIS",
    href: "/jarvis",
    icon: Bot,
  },
  {
    label: "Campaigns",
    href: "/campaigns",
    icon: Megaphone,
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

  useEffect(() => {
    api.getStatus()
      .then((status) => setApiConnected(status.meta_connected))
      .catch(() => setApiConnected(false));
  }, []);

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <Home className="h-6 w-6 text-primary" />
          <div className="flex flex-col">
            <span className="text-lg font-bold">Schumacher</span>
            <span className="text-xs text-muted-foreground">Ads Dashboard</span>
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
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t p-4">
          <div className={cn(
            "rounded-lg p-3",
            apiConnected ? "bg-green-50 dark:bg-green-950" : "bg-muted"
          )}>
            <p className="text-xs font-medium">
              {apiConnected ? "Live Data" : "Demo Mode"}
            </p>
            <p className="text-xs text-muted-foreground">
              {apiConnected
                ? "Connected to Meta Ads account."
                : "Using mock data. Connect Meta Ads account to see live data."}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
