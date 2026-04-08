/**
 * /faculty/curriculum — Embedded Sanity Studio for managing sessions,
 * prescribed readings, and assessment assignments.
 *
 * Sanity Studio is served as a client-only component.
 * Faculty use this page instead of navigating to a separate Sanity URL.
 */
"use client";

import { useEffect, useRef } from "react";

export default function CurriculumPage() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Dynamically load Sanity Studio to avoid SSR issues.
    // The studio is fully client-side React.
    let cleanup: (() => void) | undefined;

    async function mountStudio() {
      try {
        const { renderStudio } = await import("@/sanity/studio-entry");
        if (containerRef.current) {
          cleanup = renderStudio(containerRef.current);
        }
      } catch {
        // Studio not yet configured — show setup instructions
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #6b7280;">
              <h2 style="margin-bottom: 0.5rem;">Sanity Studio</h2>
              <p>Run <code style="background:#f3f4f6;padding:2px 6px;border-radius:3px;">cd 05_module.5_web/sanity && npm install && npm run dev</code> to start the Curriculum Studio locally.</p>
              <p style="margin-top:0.5rem;">After deploying, set <code>SANITY_PROJECT_ID</code> and update this page to embed the deployed studio.</p>
            </div>
          `;
        }
      }
    }

    mountStudio();
    return () => cleanup?.();
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ height: "100vh", width: "100%", overflow: "hidden" }}
    />
  );
}
