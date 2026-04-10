/**
 * /faculty/curriculum — Curriculum Studio setup instructions.
 *
 * Sanity Studio runs as a separate process; embed it here once deployed.
 * Until then, this page shows local-dev and deployment instructions.
 */
export default function CurriculumPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        overflow: "auto",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        color: "#6b7280",
        textAlign: "center",
      }}
    >
      <div>
        <h2 style={{ marginBottom: "0.5rem", color: "inherit" }}>Sanity Studio</h2>
        <p>
          Run{" "}
          <code
            style={{
              background: "#f3f4f6",
              padding: "2px 6px",
              borderRadius: "3px",
            }}
          >
            cd 05_module.5_web/sanity &amp;&amp; npm install &amp;&amp; npm run dev
          </code>{" "}
          to start the Curriculum Studio locally.
        </p>
        <p style={{ marginTop: "0.5rem" }}>
          After deploying, set <code>SANITY_PROJECT_ID</code> and update this
          page to embed the deployed studio.
        </p>
      </div>
    </div>
  );
}
