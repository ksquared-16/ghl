"use client";

import Script from "next/script";

export default function GhlScript() {
  return (
    <Script
      src="https://link.msgsndr.com/js/form_embed.js"
      strategy="afterInteractive"
      onLoad={() => {
        if (typeof window !== "undefined" && (window as any).LeadConnector) {
          (window as any).LeadConnector.init();
        }
      }}
    />
  );
}

