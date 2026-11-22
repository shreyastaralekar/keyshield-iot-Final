from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "KeyShield_IoT_MTech_Mini_Project_Presentation.pptx"
TEMPLATE = Path(r"C:\Users\shrey\Downloads\M_Tech_AICS_Mini_Project_ESE_Presentation_Template.pptx")

prs = Presentation(TEMPLATE)
for slide_id in list(prs.slides._sldIdLst):
    prs.part.drop_rel(slide_id.rId)
    prs.slides._sldIdLst.remove(slide_id)

NAVY = RGBColor(20, 48, 74)
BLUE = RGBColor(41, 119, 180)
CYAN = RGBColor(55, 157, 178)
GREEN = RGBColor(72, 145, 112)
ORANGE = RGBColor(225, 145, 67)
RED = RGBColor(185, 79, 79)
DARK = RGBColor(43, 53, 61)
GRAY = RGBColor(105, 116, 125)
LIGHT = RGBColor(244, 247, 249)
PALE = RGBColor(226, 238, 246)
WHITE = RGBColor(255, 255, 255)


def box(slide, text, x, y, w, h, size=16, color=DARK, bold=False,
        align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP):
    sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = Inches(0.03)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = "Aptos"
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return sh


def paragraphs(slide, items, x, y, w, h, size=15, color=DARK,
               bullet=True, gap=9):
    sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.clear()
    tf.margin_left = Inches(0.03)
    tf.margin_right = Inches(0.03)
    tf.margin_top = Inches(0.02)
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ("• " if bullet else "") + item
        p.font.name = "Aptos"
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(gap)
        p.line_spacing = 1.08
    return sh


def shape(slide, x, y, w, h, fill=LIGHT, line=None, radius=True):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line or fill
    return sh


def circle(slide, x, y, d, fill, text, size=11):
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = fill
    tf = sh.text_frame
    tf.clear()
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = "Aptos"
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = WHITE
    return sh


def line(slide, x, y, w, color=PALE):
    shape(slide, x, y, w, 0.012, color, color, radius=False)


def slide(title="", section="", number=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    if title:
        shape(s, 0, 0, 13.333, 0.09, CYAN, CYAN, radius=False)
        box(s, title, 0.65, 0.34, 10.8, 0.48, 24, NAVY, True)
        line(s, 0.65, 0.98, 12.03)
        box(s, section.upper(), 11.15, 0.42, 1.50, 0.28, 9, BLUE, True,
            PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    if number is not None:
        box(s, "Department of Artificial Intelligence & Machine Learning",
            0.65, 7.10, 7.0, 0.20, 8, GRAY)
        box(s, str(number), 12.15, 7.10, 0.50, 0.20, 9, GRAY, True,
            PP_ALIGN.RIGHT)
    return s


def metric(s, x, y, w, value, label, accent=BLUE):
    shape(s, x, y, w, 1.30)
    shape(s, x, y, 0.07, 1.30, accent, accent, radius=False)
    box(s, value, x + 0.22, y + 0.20, w - 0.40, 0.48, 23, NAVY, True)
    box(s, label, x + 0.22, y + 0.78, w - 0.40, 0.30, 11, GRAY)


# 1 Cover
s = slide(number=1)
shape(s, 0, 0, 13.333, 7.5, NAVY, NAVY, radius=False)
shape(s, 0.65, 0.72, 0.10, 5.80, CYAN, CYAN, radius=False)
box(s, "M. TECH. PROJECT • AICS • AY 2026-27",
    1.05, 0.78, 8.5, 0.30, 11, RGBColor(181, 211, 228), True)
box(s, "KeyShield-IoT",
    1.05, 1.55, 10.8, 0.65, 34, WHITE, True)
box(s, "AI-Driven Adaptive Key Rotation for IoT Security",
    1.05, 2.32, 10.9, 0.62, 27, WHITE, True)
box(s, "Group Members",
    1.05, 4.05, 2.2, 0.30, 10, RGBColor(181, 211, 228), True)
box(s, "[Member Name] (PRN)  •  [Member Name] (PRN)\n[Member Name] (PRN)  •  [Member Name] (PRN)",
    1.05, 4.42, 9.5, 0.72, 14, WHITE)
box(s, "Guide: Dr. Nivedita Mishra",
    1.05, 5.55, 5.5, 0.32, 13, WHITE, True)
box(s, "Project ID: [PROJECT ID]  •  23-11-2026",
    1.05, 6.14, 7.0, 0.30, 11, RGBColor(181, 211, 228))
box(s, "Department of Artificial Intelligence & Machine Learning",
    7.20, 6.78, 5.45, 0.26, 9, WHITE, False, PP_ALIGN.RIGHT)

# 2 Outline
s = slide("Outline of the Presentation", "Agenda", 2)
items = [
    ("01", "Team and work distribution"), ("02", "Introduction"),
    ("03", "Problem statement"), ("04", "Objectives"),
    ("05", "Project plan"), ("06", "Literature review"),
    ("07", "Research gap"), ("08", "Proposed solution"),
    ("09", "Requirement analysis"), ("10", "Technology stack"),
    ("11", "Design and implementation"), ("12", "Testing, outcome and conclusion"),
]
for i, (n, text) in enumerate(items):
    col, row = i % 2, i // 2
    x = 0.75 + col * 6.10
    y = 1.28 + row * 0.82
    circle(s, x, y + 0.05, 0.42, CYAN, n, 9)
    box(s, text, x + 0.60, y, 5.05, 0.50, 14, DARK, False,
        valign=MSO_ANCHOR.MIDDLE)

# 3 Team
s = slide("Group Members and Work Distribution", "Team", 3)
team = [
    ("Member 1", "[PRN]", "Data pipeline"),
    ("Member 2", "[PRN]", "Models and evaluation"),
    ("Member 3", "[PRN]", "Crypto and audit"),
    ("Member 4", "[PRN]", "Dashboard and testing"),
]
for i, (name, prn, work) in enumerate(team):
    x = 0.62 + i * 3.08
    shape(s, x, 1.55, 2.78, 4.10)
    circle(s, x + 1.03, 1.96, 0.72, [BLUE, CYAN, GREEN, ORANGE][i], str(i + 1), 14)
    box(s, name, x + 0.20, 2.95, 2.38, 0.38, 16, NAVY, True, PP_ALIGN.CENTER)
    box(s, prn, x + 0.20, 3.38, 2.38, 0.28, 10, GRAY, False, PP_ALIGN.CENTER)
    box(s, work, x + 0.30, 4.20, 2.18, 0.75, 13, DARK, False, PP_ALIGN.CENTER)

# 4 Introduction
s = slide("Introduction", "Overview", 4)
shape(s, 0.70, 1.45, 11.90, 1.15, PALE)
box(s, "Key exposure is the period in which a stolen key or compromised device remains trusted.",
    1.05, 1.78, 11.20, 0.50, 20, NAVY, True, PP_ALIGN.CENTER)
steps = [
    ("1", "IoT fleet", "Many devices operate continuously."),
    ("2", "Fixed schedule", "Rotation timing ignores live risk."),
    ("3", "Compromise", "Valid credentials remain usable."),
    ("4", "Adaptive response", "Evidence triggers warn, rotate or revoke."),
]
for i, (n, title, text) in enumerate(steps):
    x = 0.70 + i * 3.08
    shape(s, x, 3.15, 2.78, 2.35)
    circle(s, x + 0.20, 3.38, 0.45, CYAN, n, 9)
    box(s, title, x + 0.20, 3.95, 2.38, 0.36, 14, NAVY, True)
    box(s, text, x + 0.20, 4.43, 2.38, 0.74, 12, GRAY)

# 5 Problem
s = slide("Problem Statement", "Problem", 5)
metric(s, 0.70, 1.50, 3.72, "Long-lived", "keys increase exposure", ORANGE)
metric(s, 4.81, 1.50, 3.72, "Fixed", "schedules ignore real risk", BLUE)
metric(s, 8.92, 1.50, 3.72, "Cost", "frequent rotations add overhead", GREEN)
shape(s, 0.70, 3.55, 11.94, 1.70, NAVY)
box(s, "How can key rotation adapt to anomaly evidence while controlling false rotations\nand limiting attacker-delivered traffic?",
    1.15, 3.98, 11.04, 0.78, 19, WHITE, True, PP_ALIGN.CENTER)
box(s, "S1 — stolen key; defender still controls the device",
    1.05, 6.05, 5.40, 0.34, 12, BLUE, True)
box(s, "S2 — attacker controls the compromised device",
    6.85, 6.05, 5.40, 0.34, 12, RED, True)

# 6 Objectives
s = slide("Objectives of the Project", "Objectives", 6)
objectives = [
    "Process CICIoT2023 into 60-second traffic windows",
    "Compare Isolation Forest, OCSVM, Autoencoder and Random Forest",
    "Calibrate thresholds using benign validation traffic",
    "Implement adaptive, hybrid and fixed policies",
    "Measure KEW, EAV, rotations and crypto cost",
    "Provide a signed, hash-chained audit trail",
]
for i, text in enumerate(objectives):
    x = 0.75 + (i % 2) * 6.05
    y = 1.45 + (i // 2) * 1.55
    shape(s, x, y, 5.65, 1.18)
    circle(s, x + 0.22, y + 0.36, 0.46, CYAN, str(i + 1), 9)
    box(s, text, x + 0.85, y + 0.25, 4.55, 0.68, 13, DARK,
        valign=MSO_ANCHOR.MIDDLE)

# 7 Timeline
s = slide("Project Plan with Timeline", "Planning", 7)
phases = [
    ("01", "Data", "Week 1–2"), ("02", "Models", "Week 3–4"),
    ("03", "Crypto", "Week 5–6"), ("04", "Engine", "Week 7–8"),
    ("05", "Evaluate", "Week 9–10"), ("06", "Dashboard", "Week 11–12"),
]
line(s, 1.03, 3.45, 11.30)
for i, (n, name, timing) in enumerate(phases):
    x = 1.03 + i * 2.23
    circle(s, x, 3.18, 0.54, [BLUE, CYAN, GREEN, ORANGE, BLUE, CYAN][i], n, 9)
    box(s, name, x - 0.36, 4.05, 1.26, 0.32, 13, NAVY, True, PP_ALIGN.CENTER)
    box(s, timing, x - 0.36, 4.48, 1.26, 0.28, 10, GRAY, False, PP_ALIGN.CENTER)
shape(s, 1.05, 5.55, 11.20, 0.82, PALE)
box(s, "Milestone: replay pipeline • measured policies • working dashboard",
    1.40, 5.82, 10.50, 0.30, 13, NAVY, True, PP_ALIGN.CENTER)

# 8 Literature
s = slide("Literature Review", "Research", 8)
reviews = [
    ("Key management", "Keys require lifecycle control: generation, use, rotation and revocation."),
    ("Isolation Forest", "Unusual observations are isolated quickly through random sub-samples."),
    ("CICIoT2023", "Large benchmark of benign and malicious IoT network traffic."),
    ("Cryptography", "ECDH, ECDSA and AES-GCM support sessions, signatures and confidentiality."),
]
for i, (title, text) in enumerate(reviews):
    x = 0.75 + (i % 2) * 6.05
    y = 1.45 + (i // 2) * 2.20
    shape(s, x, y, 5.65, 1.75)
    shape(s, x, y, 0.08, 1.75, [BLUE, CYAN, GREEN, ORANGE][i],
          [BLUE, CYAN, GREEN, ORANGE][i], radius=False)
    box(s, title, x + 0.30, y + 0.25, 5.05, 0.36, 16, NAVY, True)
    box(s, text, x + 0.30, y + 0.75, 5.05, 0.70, 12, GRAY)

# 9 Gap
s = slide("Gap in Research / Technology / Methodology", "Research Gap", 9)
gaps = [
    ("Detection only", "Anomaly scores do not define an operational response."),
    ("Fixed schedules", "Rotation timing does not consider current attacker evidence."),
    ("Fragmented evaluation", "Studies rarely measure KEW, EAV and crypto cost together."),
    ("Replay limitations", "Physical radio, battery and firmware effects remain outside the dataset."),
]
for i, (title, text) in enumerate(gaps):
    y = 1.45 + i * 1.20
    shape(s, 0.75, y, 11.80, 0.92)
    circle(s, 1.03, y + 0.23, 0.46, RED, "!", 11)
    box(s, title, 1.72, y + 0.18, 3.20, 0.30, 14, NAVY, True)
    box(s, text, 4.55, y + 0.18, 7.45, 0.42, 12, DARK)

# 10 Solution
s = slide("Description of the Proposed Solution", "Solution", 10)
steps = [
    ("1", "Traffic", "CICIoT2023"),
    ("2", "Features", "60-second windows"),
    ("3", "Detection", "Isolation Forest"),
    ("4", "Decision", "Warn / Rotate / Revoke"),
    ("5", "Enforcement", "Key epoch / Audit"),
]
for i, (n, title, text) in enumerate(steps):
    x = 0.48 + i * 2.55
    shape(s, x, 2.05, 2.12, 2.05)
    circle(s, x + 0.79, 1.65, 0.54, [BLUE, CYAN, GREEN, ORANGE, NAVY][i], n, 10)
    box(s, title, x + 0.20, 2.56, 1.72, 0.34, 14, NAVY, True, PP_ALIGN.CENTER)
    box(s, text, x + 0.20, 3.05, 1.72, 0.52, 11, GRAY, False, PP_ALIGN.CENTER)
shape(s, 1.08, 5.25, 11.12, 0.92, PALE)
box(s, "Adaptive AI trigger + hysteresis + cooldown + EWMA + lifetime fallback",
    1.42, 5.52, 10.44, 0.38, 16, NAVY, True, PP_ALIGN.CENTER)

# 11 Requirements
s = slide("Requirement Analysis", "Requirements", 11)
box(s, "Functional requirements", 0.75, 1.45, 5.50, 0.36, 17, NAVY, True)
paragraphs(s, [
    "Load and validate CICIoT2023",
    "Create 10-flow, 60-second windows",
    "Score windows and select actions",
    "Rotate or revoke session-key epochs",
    "Sign and verify audit events",
], 0.75, 2.00, 5.55, 3.90, 14)
box(s, "Non-functional requirements", 6.85, 1.45, 5.50, 0.36, 17, NAVY, True)
paragraphs(s, [
    "Reproducible across five seeds",
    "Low cryptographic overhead",
    "Hash-chained auditability",
    "Configurable and maintainable",
    "Usable replay dashboard",
], 6.85, 2.00, 5.55, 3.90, 14)

# 12 Technology
s = slide("Technology Stack", "Technology", 12)
stack = [
    ("Python 3.13", "Implementation"),
    ("Pandas / PyArrow", "Data pipeline"),
    ("scikit-learn", "Isolation Forest, OCSVM, AE, RF"),
    ("cryptography", "ECDSA, ECDH, AES-GCM"),
    ("Streamlit", "Interactive dashboard"),
    ("pytest", "Automated validation"),
]
for i, (title, text) in enumerate(stack):
    x = 0.70 + (i % 3) * 4.14
    y = 1.55 + (i // 3) * 2.05
    shape(s, x, y, 3.72, 1.58)
    box(s, title, x + 0.20, y + 0.28, 3.32, 0.38, 15, NAVY, True, PP_ALIGN.CENTER)
    box(s, text, x + 0.20, y + 0.82, 3.32, 0.46, 11, GRAY, False, PP_ALIGN.CENTER)

# 13 Design
s = slide("Design", "Architecture", 13)
columns = [
    ("Data plane", "CSV loading\nCleaning\nWindowing"),
    ("Detection", "Isolation Forest\nOCSVM\nAutoencoder"),
    ("Decision", "Hysteresis\nCooldown\nEWMA"),
    ("Enforcement", "ECDH\nKey epochs\nAES-GCM"),
]
for i, (title, text) in enumerate(columns):
    x = 0.70 + i * 3.12
    shape(s, x, 1.65, 2.72, 3.65, PALE)
    box(s, title, x + 0.24, 2.00, 2.24, 0.38, 16, NAVY, True, PP_ALIGN.CENTER)
    box(s, text, x + 0.24, 2.78, 2.24, 1.50, 14, DARK, False, PP_ALIGN.CENTER)
    if i < 3:
        box(s, "→", x + 2.76, 3.10, 0.35, 0.35, 18, CYAN, True, PP_ALIGN.CENTER)

# 14 Implementation
s = slide("Development / Implementation", "Build", 14)
modules = [
    ("01", "Data", "Cleaning and device streams"),
    ("02", "Models", "Training and scoring"),
    ("03", "Engine", "AI and baseline policies"),
    ("04", "Crypto", "Sessions and signed audit"),
    ("05", "Dashboard", "Replay and metrics"),
]
for i, (n, title, text) in enumerate(modules):
    x = 0.55 + i * 2.47
    shape(s, x, 1.70, 2.22, 3.55)
    circle(s, x + 0.75, 2.10, 0.72, [BLUE, CYAN, GREEN, ORANGE, NAVY][i], n, 11)
    box(s, title, x + 0.18, 3.08, 1.86, 0.36, 14, NAVY, True, PP_ALIGN.CENTER)
    box(s, text, x + 0.22, 3.62, 1.78, 0.90, 11, GRAY, False, PP_ALIGN.CENTER)

# 15 Testing
s = slide("Testing and Debugging", "Validation", 15)
tests = [
    ("Data", "Pool, split and window integrity"),
    ("Models", "Training, scoring and thresholds"),
    ("Engine", "Cooldown, hysteresis and revocation"),
    ("Crypto", "AES-GCM and audit verification"),
    ("Dashboard", "Replay and metric rendering"),
]
for i, (title, text) in enumerate(tests):
    y = 1.45 + i * 1.02
    shape(s, 0.75, y, 11.80, 0.78)
    circle(s, 1.02, y + 0.16, 0.46, GREEN, "✓", 10)
    box(s, title, 1.72, y + 0.16, 3.05, 0.30, 14, NAVY, True)
    box(s, text, 4.55, y + 0.16, 7.45, 0.36, 12, DARK)

# 16 Results
s = slide("Project Outcome: Detection Performance", "Results", 16)
metric(s, 0.60, 1.50, 3.72, "0.995", "Isolation Forest ROC-AUC")
metric(s, 4.80, 1.50, 3.72, "0.972", "Isolation Forest PR-AUC", CYAN)
metric(s, 9.00, 1.50, 3.72, "1.000", "Episode detection", GREEN)
table = s.shapes.add_table(5, 4, Inches(0.75), Inches(3.50), Inches(11.80), Inches(2.55)).table
headers = ["Category", "Isolation Forest", "One-Class SVM", "Random Forest"]
rows = [
    ("DDoS", "1.000", "1.000", "1.000"),
    ("DoS", "1.000", "1.000", "1.000"),
    ("Recon", "0.865", "0.897", "0.981"),
    ("Spoofing", "0.721", "0.738", "0.977"),
]
for c, h in enumerate(headers):
    table.cell(0, c).text = h
    table.cell(0, c).fill.solid()
    table.cell(0, c).fill.fore_color.rgb = NAVY
    p = table.cell(0, c).text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    for r in p.runs:
        r.font.color.rgb = WHITE
        r.font.bold = True
        r.font.size = Pt(11)
for r, row in enumerate(rows, 1):
    for c, val in enumerate(row):
        table.cell(r, c).text = val
        table.cell(r, c).fill.solid()
        table.cell(r, c).fill.fore_color.rgb = WHITE if r % 2 else LIGHT
        p = table.cell(r, c).text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        for run in p.runs:
            run.font.name = "Aptos"
            run.font.size = Pt(11)

# 17 Exposure
s = slide("Project Outcome: Exposure Reduction", "Results", 17)
metric(s, 0.65, 1.50, 3.55, "57 s", "Adaptive mean KEW — S1", GREEN)
metric(s, 4.88, 1.50, 3.55, "342 s", "Adaptive mean KEW — S2")
metric(s, 9.11, 1.50, 3.55, "31,377 s", "Fixed T=60 mean KEW — S2", RED)
shape(s, 0.75, 3.55, 11.80, 2.18)
box(s, "Adaptive / Hybrid", 1.10, 3.95, 3.00, 0.34, 15, NAVY, True)
box(s, "S1 and S2 detection: 100%\nS1 EAV: 0.95  •  S2 EAV: 5.70",
    1.10, 4.48, 4.80, 0.72, 13, DARK)
box(s, "Fixed T=60", 6.65, 3.95, 2.30, 0.34, 15, NAVY, True)
box(s, "S1 KEW: 1,797 s\nS2 KEW: 31,377 s",
    6.65, 4.48, 4.80, 0.72, 13, DARK)

# 18 Crypto
s = slide("Project Outcome: Security and Cost", "Results", 18)
outcomes = [
    ("0.316 ms", "ECDH handshake"),
    ("0.336 ms", "Key rotation"),
    ("0.00376 ms", "AES-GCM encrypt (64 B)"),
    ("Hash + ECDSA", "Audit trail"),
]
for i, (value, text) in enumerate(outcomes):
    x = 0.65 + i * 3.08
    shape(s, x, 1.65, 2.78, 2.20)
    box(s, value, x + 0.20, 2.10, 2.38, 0.46, 18, NAVY, True, PP_ALIGN.CENTER)
    box(s, text, x + 0.20, 2.86, 2.38, 0.42, 11, GRAY, False, PP_ALIGN.CENTER)
shape(s, 1.05, 4.75, 11.20, 1.18, PALE)
box(s, "Adaptive: 0.32 rotations/device-hour   •   Fixed T=60: 1.02 rotations/device-hour",
    1.40, 5.12, 10.50, 0.44, 15, NAVY, True, PP_ALIGN.CENTER)

# 19 Conclusion
s = slide("Conclusion", "Conclusion", 19)
shape(s, 0.75, 1.50, 11.80, 1.28, NAVY)
box(s, "Evidence-aware key management can reduce exposure and retain bounded behavior.",
    1.12, 1.88, 11.06, 0.52, 19, WHITE, True, PP_ALIGN.CENTER)
conclusions = [
    "Isolation Forest is suitable for unsupervised live detection.",
    "Adaptive and hybrid policies detected all replayed episodes.",
    "The hybrid policy adds a maximum-lifetime safeguard.",
    "Physical deployment and hardware validation remain future work.",
]
for i, text in enumerate(conclusions):
    y = 3.40 + i * 0.70
    circle(s, 1.02, y, 0.38, GREEN, "✓", 9)
    box(s, text, 1.58, y - 0.02, 10.20, 0.36, 13, DARK)

# 20 Future
s = slide("Future Scope", "Next Steps", 20)
future = [
    "Deploy on constrained or emulated IoT hardware",
    "Improve spoofing and reconnaissance features",
    "Test secure key storage and real certificates",
    "Evaluate continual or federated learning",
]
for i, text in enumerate(future):
    x = 0.70 + (i % 2) * 6.05
    y = 1.55 + (i // 2) * 2.05
    shape(s, x, y, 5.65, 1.48)
    circle(s, x + 0.22, y + 0.43, 0.58, [BLUE, CYAN, GREEN, ORANGE][i], str(i + 1), 10)
    box(s, text, x + 1.02, y + 0.38, 4.25, 0.72, 13, NAVY, True)

# 21 References
s = slide("References", "References", 21)
refs = [
    "[1] E. S. R. M. Neto, S. Dadkhah, R. Ferreira, A. Zohourian, H. Lu, and A. A. Ghorbani, “CICIoT2023: A real-time dataset and benchmark for large-scale attacks in IoT environment,” Sensors, vol. 23, no. 13, 2023.",
    "[2] E. Barker, “Recommendation for key management: Part 1—General,” NIST SP 800-57 Part 1 Rev. 5, Gaithersburg, MD, USA, 2020.",
    "[3] K. Megas, B. Cuthill, M. Fagan, and P. Watrobski, “NIST Cybersecurity for IoT Program,” IEEE Computer, 2024.",
    "[4] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in Proc. ICDM, 2008, pp. 413–422.",
    "[5] B. Schölkopf, J. C. Platt, J. Shawe-Taylor, A. J. Smola, and R. C. Williamson, “Estimating the support of a high-dimensional distribution,” Neural Computation, vol. 13, no. 7, pp. 1443–1471, 2001.",
    "[6] Canadian Institute for Cybersecurity, “IoT Dataset 2023,” Univ. of New Brunswick, 2023. [Online]. Available: https://www.unb.ca/cic/datasets/iotdataset-2023.html",
    "[7] D. McGrew and J. Viega, “The Galois/Counter Mode of operation (GCM),” J. Cryptology, 2005.",
    "[8] E. Rescorla, “The Transport Layer Security (TLS) Protocol Version 1.3,” RFC 8446, Aug. 2018.",
    "[9] Canadian Institute for Cybersecurity, “CICIoT2023 dataset repository,” 2023. [Online]. Available: https://github.com/topics/ciciot2023",
    "[10] KeyShield-IoT Project, “Source repository and implementation documentation,” 2026. [Online]. Available: https://github.com/shreyastaralekar/keyshield-iot-Final",
    "[11] United Nations, “Goal 9: Industry, Innovation and Infrastructure,” 2026. [Online]. Available: https://sdgs.un.org/goals/goal9",
]
paragraphs(s, refs, 0.78, 1.42, 11.75, 4.95, 10, DARK, bullet=False, gap=6)
shape(s, 0.78, 6.10, 11.75, 0.48, PALE)
box(s, "Thank you • Questions?",
    1.05, 6.20, 11.20, 0.22, 14, NAVY, True, PP_ALIGN.CENTER)

prs.save(OUT)
print(OUT)
