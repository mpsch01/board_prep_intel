const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title  = "ITE Intelligence System";
pres.author = "St. Luke's Family Medicine Residency";

// ── Palette ──────────────────────────────────────────────────────────────────
const NAVY   = "1B3564";
const GOLD   = "C8922A";
const BLUE   = "2E5F9C";
const LGRAY  = "F4F6FA";
const WHITE  = "FFFFFF";
const DARK   = "1A1A2E";
const MED    = "5A6A7E";
const CARD   = "EBF0F7";

// ── Helpers ───────────────────────────────────────────────────────────────────
const makeShadow = () => ({ type:"outer", color:"000000", blur:8, offset:2, angle:135, opacity:0.12 });

// Gold left-bar motif (reused on content slides)
function addAccentBar(slide, y, h) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x:0.35, y, w:0.07, h,
    fill:{ color:GOLD }, line:{ color:GOLD }
  });
}

// Stat callout block
function addStat(slide, x, y, w, h, bigText, label, bgColor) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill:{ color: bgColor || CARD },
    line:{ color:BLUE, width:0 },
    shadow: makeShadow()
  });
  // Gold top strip
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h:0.06,
    fill:{ color:GOLD }, line:{ color:GOLD }
  });
  slide.addText(bigText, {
    x, y: y+0.1, w, h: h*0.55,
    fontSize:44, bold:true, color:NAVY,
    align:"center", valign:"bottom", margin:0
  });
  slide.addText(label, {
    x, y: y + h*0.58, w, h: h*0.36,
    fontSize:11, color:MED,
    align:"center", valign:"top", margin:0
  });
}

// Step box for pipeline flow
function addStep(slide, x, y, num, title, desc) {
  const W = 1.9, H = 2.1;
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w:W, h:H,
    fill:{ color:WHITE }, line:{ color:BLUE, width:0 },
    shadow: makeShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w:W, h:0.06, fill:{color:GOLD}, line:{color:GOLD} });
  // Step number circle
  slide.addShape(pres.shapes.OVAL, {
    x: x + W/2 - 0.25, y: y + 0.18, w:0.5, h:0.5,
    fill:{ color:NAVY }, line:{ color:NAVY }
  });
  slide.addText(String(num), {
    x: x + W/2 - 0.25, y: y + 0.18, w:0.5, h:0.5,
    fontSize:16, bold:true, color:WHITE, align:"center", valign:"middle", margin:0
  });
  slide.addText(title, {
    x: x+0.1, y: y+0.78, w: W-0.2, h:0.42,
    fontSize:13, bold:true, color:NAVY, align:"center", valign:"middle", margin:0
  });
  slide.addText(desc, {
    x: x+0.1, y: y+1.2, w: W-0.2, h:0.8,
    fontSize:10, color:MED, align:"center", valign:"top", margin:0
  });
}

// Arrow between steps
function addArrow(slide, x, y) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y: y+0.9, w:0.22, h:0.08,
    fill:{color:GOLD}, line:{color:GOLD}
  });
}

// Card (for deliverables slide)
function addCard(slide, x, y, w, h, title, bullets, titleBg) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill:{color:WHITE}, line:{color:BLUE, width:0},
    shadow: makeShadow()
  });
  // Header bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h:0.55,
    fill:{color: titleBg || NAVY}, line:{color: titleBg || NAVY}
  });
  slide.addText(title, {
    x: x+0.15, y, w: w-0.15, h:0.55,
    fontSize:13, bold:true, color:WHITE,
    align:"left", valign:"middle", margin:0
  });
  // Bullets
  const items = bullets.map((b, i) => ({
    text: b,
    options:{ bullet:{ type:"bullet" }, breakLine: i < bullets.length-1,
              fontSize:11, color:DARK, paraSpaceAfter:4 }
  }));
  slide.addText(items, { x: x+0.18, y: y+0.65, w: w-0.3, h: h-0.78 });
}

// ── SLIDE 1: Title ────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // Gold accent bar
  s.addShape(pres.shapes.RECTANGLE, {
    x:0, y:0, w:0.18, h:5.625,
    fill:{color:GOLD}, line:{color:GOLD}
  });
  // Subtle bottom bar
  s.addShape(pres.shapes.RECTANGLE, {
    x:0, y:5.1, w:10, h:0.525,
    fill:{color:"162A52"}, line:{color:"162A52"}
  });

  s.addText("ITE Intelligence System", {
    x:0.45, y:1.4, w:9.2, h:1.1,
    fontSize:44, bold:true, color:WHITE,
    align:"left", valign:"middle", margin:0
  });
  s.addText("Personalized study guidance from your residents' score reports", {
    x:0.45, y:2.6, w:8.5, h:0.7,
    fontSize:20, color:"CADCFC",
    align:"left", valign:"middle", margin:0
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x:0.45, y:3.45, w:2.8, h:0.04,
    fill:{color:GOLD}, line:{color:GOLD}
  });
  s.addText("St. Luke's Family Medicine Residency  •  2025", {
    x:0.45, y:5.12, w:9, h:0.48,
    fontSize:11, color:"AABBD4",
    align:"left", valign:"middle", margin:0
  });
}

// ── SLIDE 2: The Problem ───────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: LGRAY };

  addAccentBar(s, 0.35, 0.6);
  s.addText("Every resident gets the same thing.", {
    x:0.55, y:0.28, w:9.1, h:0.55,
    fontSize:26, bold:true, color:NAVY,
    align:"left", valign:"middle", margin:0
  });

  // 3 stat callouts
  addStat(s, 0.4,  1.1, 2.8, 1.9, "191",         "scored exam questions",           CARD);
  addStat(s, 3.6,  1.1, 2.8, 1.9, "14",           "body system categories",          CARD);
  addStat(s, 6.8,  1.1, 2.8, 1.9, "5",            "blueprint domains",               CARD);

  s.addText("...and a single number.", {
    x:0.4, y:3.2, w:9.2, h:0.55,
    fontSize:20, bold:true, color:NAVY, align:"center", valign:"middle", margin:0
  });
  s.addText("The score report tells you where you've been — not where to focus next.", {
    x:0.4, y:3.75, w:9.2, h:0.5,
    fontSize:14, italic:true, color:MED, align:"center", valign:"middle", margin:0
  });
}

// ── SLIDE 3: What We Built ────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: LGRAY };

  addAccentBar(s, 0.35, 0.6);
  s.addText("A three-layer knowledge system", {
    x:0.55, y:0.28, w:9.1, h:0.55,
    fontSize:26, bold:true, color:NAVY, align:"left", valign:"middle", margin:0
  });

  const cols = [
    { x:0.38, big:"2,850", label:"Practice Questions\n1,629 ITE (2018–2025)\n+ 1,221 AAFP Board Review", title:"Question Bank" },
    { x:3.63, big:"1,985", label:"Clinical Guidelines\n404 full PDFs\nlinked to exam content", title:"Article Library" },
    { x:6.88, big:"4,137", label:"ICD-10 article tags\n+ 5,284 question links\nClinical pathway maps", title:"Smart Matching" },
  ];
  cols.forEach(c => {
    const W = 2.85, H = 3.5;
    // Card bg
    s.addShape(pres.shapes.RECTANGLE, {
      x:c.x, y:1.05, w:W, h:H,
      fill:{color:WHITE}, line:{color:BLUE, width:0}, shadow:makeShadow()
    });
    // Color header
    s.addShape(pres.shapes.RECTANGLE, {
      x:c.x, y:1.05, w:W, h:0.52,
      fill:{color:NAVY}, line:{color:NAVY}
    });
    s.addText(c.title, {
      x:c.x+0.12, y:1.05, w:W-0.12, h:0.52,
      fontSize:13, bold:true, color:WHITE,
      align:"left", valign:"middle", margin:0
    });
    // Big number
    s.addText(c.big, {
      x:c.x+0.1, y:1.65, w:W-0.2, h:1.0,
      fontSize: c.big.length > 6 ? 30 : 42, bold:true, color:GOLD,
      align:"center", valign:"middle", margin:0
    });
    // Description
    s.addText(c.label, {
      x:c.x+0.12, y:2.75, w:W-0.24, h:1.65,
      fontSize:11, color:MED, align:"center", valign:"top", margin:0
    });
  });
}

// ── SLIDE 4: How It Works ─────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: LGRAY };

  addAccentBar(s, 0.35, 0.6);
  s.addText("From score report to personalized study plan", {
    x:0.55, y:0.28, w:9.1, h:0.55,
    fontSize:26, bold:true, color:NAVY, align:"left", valign:"middle", margin:0
  });

  const steps = [
    { x:0.38, num:1, title:"Upload PDFs",        desc:"Blueprint Performance\n+ Body System PDFs\nfrom ABFM score report" },
    { x:2.55, num:2, title:"Parse & Profile",    desc:"Item-level performance\nacross 14 body systems\n+ 5 blueprint domains" },
    { x:4.72, num:3, title:"Identify Weaknesses",desc:"Priority-ranked\ndimensions by gap size\n× exam weight" },
    { x:6.89, num:4, title:"Match & Deliver",    desc:"Targeted questions\nfrom ITE + AAFP banks\n+ top guideline articles" },
  ];
  steps.forEach(st => addStep(s, st.x, 1.1, st.num, st.title, st.desc));

  // Arrows between steps
  [2.45, 4.62, 6.79].forEach(ax => addArrow(s, ax, 1.1));

  s.addShape(pres.shapes.RECTANGLE, {
    x:0.38, y:3.35, w:9.22, h:0.06,
    fill:{color:GOLD}, line:{color:GOLD}
  });
  s.addText("Both deliverables generated in under 30 seconds.", {
    x:0.38, y:3.45, w:9.22, h:0.45,
    fontSize:13, italic:true, color:MED, align:"center", valign:"middle", margin:0
  });
}

// ── SLIDE 5: Live Example (Hopkins) ──────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: LGRAY };

  addAccentBar(s, 0.35, 0.6);
  s.addText("Live example: Oceana Hopkins, M.D. — 2025 ITE", {
    x:0.55, y:0.28, w:9.1, h:0.55,
    fontSize:24, bold:true, color:NAVY, align:"left", valign:"middle", margin:0
  });

  // Left panel — score card
  s.addShape(pres.shapes.RECTANGLE, {
    x:0.38, y:1.02, w:4.4, h:4.1,
    fill:{color:WHITE}, line:{color:BLUE, width:0}, shadow:makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x:0.38, y:1.02, w:4.4, h:0.52,
    fill:{color:NAVY}, line:{color:NAVY}
  });
  s.addText("Score Report — What She Received", {
    x:0.5, y:1.02, w:4.16, h:0.52,
    fontSize:12, bold:true, color:WHITE, align:"left", valign:"middle", margin:0
  });

  // Overall score callout
  s.addShape(pres.shapes.RECTANGLE, {
    x:0.55, y:1.65, w:4.06, h:0.72,
    fill:{color:CARD}, line:{color:BLUE, width:0}
  });
  s.addText("65.4%", {
    x:0.55, y:1.65, w:1.5, h:0.72,
    fontSize:30, bold:true, color:NAVY, align:"center", valign:"middle", margin:0
  });
  s.addText("Overall  •  125/191  •  PGY2", {
    x:2.1, y:1.65, w:2.4, h:0.72,
    fontSize:11, color:MED, align:"left", valign:"middle", margin:0
  });

  // Weak areas
  s.addText("Weak areas identified:", {
    x:0.55, y:2.5, w:4.1, h:0.32,
    fontSize:11, bold:true, color:NAVY, align:"left", valign:"middle", margin:0
  });
  const weaks = [
    "Acute Care  55.9%  (38/68)",
    "Emergent/Urgent  61.1%  (22/36)",
    "Injuries/Musculoskeletal  54.5%  (12/22)",
    "Respiratory  50.0%  (4/8)",
    "+ 3 additional dimensions",
  ];
  const wItems = weaks.map((w, i) => ({
    text: w,
    options:{ bullet:true, breakLine: i < weaks.length-1, fontSize:10.5, color: i===4 ? MED : DARK, paraSpaceAfter:3 }
  }));
  s.addText(wItems, { x:0.55, y:2.85, w:4.1, h:2.1 });

  // Right panel — output
  s.addShape(pres.shapes.RECTANGLE, {
    x:5.1, y:1.02, w:4.5, h:4.1,
    fill:{color:WHITE}, line:{color:BLUE, width:0}, shadow:makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x:5.1, y:1.02, w:4.5, h:0.52,
    fill:{color:GOLD}, line:{color:GOLD}
  });
  s.addText("System Output — What She Gets", {
    x:5.22, y:1.02, w:4.26, h:0.52,
    fontSize:12, bold:true, color:WHITE, align:"left", valign:"middle", margin:0
  });

  // Output stats
  const outs = [
    { num:"20", label:"targeted practice\nquestions" },
    { num:"7",  label:"weak dimensions\naddressed" },
    { num:"5",  label:"top guideline\narticles surfaced" },
  ];
  outs.forEach((o, i) => {
    const ox = 5.22 + i * 1.42;
    s.addText(o.num, {
      x:ox, y:1.68, w:1.3, h:0.65,
      fontSize:34, bold:true, color:NAVY, align:"center", valign:"middle", margin:0
    });
    s.addText(o.label, {
      x:ox, y:2.35, w:1.3, h:0.55,
      fontSize:9.5, color:MED, align:"center", valign:"top", margin:0
    });
  });

  // Distribution bar visual
  s.addText("Questions by dimension:", {
    x:5.22, y:3.0, w:4.2, h:0.32,
    fontSize:11, bold:true, color:NAVY, align:"left", valign:"middle", margin:0
  });
  const dims = [
    { label:"Acute Care",     n:3 },
    { label:"Injuries / MSK", n:3 },
    { label:"Emergent/Urgent",n:3 },
    { label:"Respiratory",    n:3 },
    { label:"Cross-tab dims", n:3 },
    { label:"Sexual/Repro",   n:2 },
  ];
  dims.forEach((d, i) => {
    const dy = 3.35 + i * 0.28;
    s.addText(d.label, { x:5.22, y:dy, w:2.0, h:0.24, fontSize:9, color:DARK, align:"left", valign:"middle", margin:0 });
    // Bar
    const bw = (d.n / 3) * 2.0;
    s.addShape(pres.shapes.RECTANGLE, { x:7.28, y:dy+0.03, w:bw, h:0.18, fill:{color:BLUE}, line:{color:BLUE} });
    s.addText(String(d.n), { x:7.28+bw+0.05, y:dy, w:0.3, h:0.24, fontSize:9, bold:true, color:NAVY, align:"left", valign:"middle", margin:0 });
  });
}

// ── SLIDE 6: The Deliverables ─────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: LGRAY };

  addAccentBar(s, 0.35, 0.6);
  s.addText("Two deliverables — generated automatically", {
    x:0.55, y:0.28, w:9.1, h:0.55,
    fontSize:26, bold:true, color:NAVY, align:"left", valign:"middle", margin:0
  });

  addCard(s, 0.38, 1.05, 4.4, 4.1,
    "Analysis Report  (.docx)",
    [
      "Overall scaled score + pass probability",
      "Blueprint & body system performance breakdown",
      "Relative weakness classification (vs. personal mean)",
      "ICD-10 weakness map — codes driving missed questions",
      "Clinical pathway gaps — where knowledge breaks down",
      "20 targeted practice questions with explanations",
      "Top 5 linked guideline articles",
    ],
    NAVY
  );

  addCard(s, 5.1, 1.05, 4.5, 4.1,
    "Practice Exam  (.docx)",
    [
      "Clean exam format — stem + 5 choices",
      "Sorted by priority dimension (weakest first)",
      "Dual bank: ITE questions + AAFP Board Review",
      "Cover answer while reading choices",
      "Correct answer + explanation on flip",
      "3 questions max per dimension\n(no single topic monopoly)",
    ],
    BLUE
  );
}

// ── SLIDE 7: What's Next ──────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // Gold left bar
  s.addShape(pres.shapes.RECTANGLE, {
    x:0, y:0, w:0.18, h:5.625,
    fill:{color:GOLD}, line:{color:GOLD}
  });
  // Bottom bar
  s.addShape(pres.shapes.RECTANGLE, {
    x:0, y:5.1, w:10, h:0.525,
    fill:{color:"162A52"}, line:{color:"162A52"}
  });

  s.addText("The foundation is set.", {
    x:0.45, y:0.55, w:9.1, h:0.65,
    fontSize:32, bold:true, color:WHITE, align:"left", valign:"middle", margin:0
  });

  const rows = [
    { status:"LIVE",      text:"Personalized question matching — both ITE + AAFP banks",     sub:"Priority-ranked by gap × exam weight. Diversity-capped across dimensions." },
    { status:"LIVE",      text:"ICD-10 crosswalk — 4,137 article tags, 5,284 question links",sub:"Connects missed questions to clinical diagnosis codes and guideline articles." },
    { status:"LIVE",      text:"Clinical pathway maps — 4,020 diagnosis-to-guideline paths", sub:"Where a resident's knowledge breaks down in the clinical decision chain." },
    { status:"BUILDING",  text:"PubMed currency checks — are your guidelines still current?",sub:"344 PMIDs cached. Tracks publication dates, superseded articles, citation trends." },
  ];

  rows.forEach((r, i) => {
    const ry = 1.35 + i * 1.0;
    s.addText(r.status, {
      x:0.45, y:ry, w:1.5, h:0.38,
      fontSize:11, bold:true, color:GOLD, align:"left", valign:"middle", margin:0
    });
    s.addText(r.text, {
      x:2.05, y:ry, w:7.5, h:0.38,
      fontSize:13, bold:true, color:WHITE, align:"left", valign:"middle", margin:0
    });
    s.addText(r.sub, {
      x:2.05, y:ry+0.4, w:7.5, h:0.52,
      fontSize:10, color:"AABBD4", align:"left", valign:"top", margin:0
    });
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x:0.45, y:5.12, w:9.1, h:0.04,
    fill:{color:GOLD}, line:{color:GOLD}
  });
  s.addText("From exam prep to clinical intelligence.", {
    x:0.45, y:5.15, w:9.1, h:0.46,
    fontSize:13, italic:true, color:"AABBD4",
    align:"left", valign:"middle", margin:0
  });
}

// ── Write ─────────────────────────────────────────────────────────────────────
const OUT = "/sessions/quirky-awesome-cori/ITE_Intelligence_FacultyPresentation_2025.pptx";
pres.writeFile({ fileName: OUT }).then(() => console.log("OK:" + OUT));
