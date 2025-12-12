"use client";

import { useEffect } from "react";

interface GhlEmbedProps {
  src: string;
  title: string;
  height?: number;
  id?: string;
  className?: string;
}

export default function GhlEmbed({
  src,
  title,
  height = 800,
  id,
  className = "",
}: GhlEmbedProps) {
  useEffect(() => {
    // Initialize GHL forms if script is loaded
    if (typeof window !== "undefined" && (window as any).LeadConnector) {
      (window as any).LeadConnector.init();
    }
  }, []);

  return (
    <iframe
      id={id}
      src={src}
      title={title}
      className={`w-full border-none rounded-xl ${className}`}
      style={{ minHeight: `${height}px` }}
      loading="lazy"
    />
  );
}

