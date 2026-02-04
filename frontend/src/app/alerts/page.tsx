"use client";

import { redirect } from "next/navigation";
import { useEffect } from "react";

// Redirect to audits page since alerts are part of audits
export default function AlertsPage() {
  useEffect(() => {
    redirect("/audits");
  }, []);

  return null;
}
