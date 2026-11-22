from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_BREAK
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
TEMPLATE = Path(r"C:\Users\shrey\Downloads\M.Tech Mini Project Report format.docx")
OUT = ROOT / "KeyShield_IoT_MTech_Mini_Project_Report.docx"


def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def set_cell_margins(cell, top=80, start=80, bottom=80, end=80):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tcMar.find(qn("w:" + m))
        if node is None:
            node = OxmlElement("w:" + m)
            tcMar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def add_field(paragraph, instr):
    run = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = instr
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.text = "PAGE"
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run._r.extend([fldChar1, instrText, fldChar2])


def no_borders(table):
    tblPr = table._tbl.tblPr
    borders = tblPr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblPr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = OxmlElement("w:" + edge)
        tag.set(qn("w:val"), "nil")
        borders.append(tag)


def format_table(table, header=True, font_size=9):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, row in enumerate(table.rows):
        if i == 0 and header:
            set_repeat_table_header(row)
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if i == 0 and header:
                set_cell_shading(cell, "D9E2F3")
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(font_size)


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    format_table(table)
    if widths:
        for row in table.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(10)


doc = Document(TEMPLATE) if TEMPLATE.exists() else Document()

# Clean template body while retaining page setup and base styles.
if TEMPLATE.exists():
    body = doc._element.body
    for child in list(body):
        if child.tag.endswith("}sectPr"):
            continue
        body.remove(child)

section = doc.sections[0]
section.page_width = Inches(8.27)
section.page_height = Inches(11.69)
section.top_margin = Inches(0.75)
section.bottom_margin = Inches(0.75)
section.left_margin = Inches(1.0)
section.right_margin = Inches(0.75)
section.different_first_page_header_footer = True

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(12)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
normal.paragraph_format.line_spacing = 1.15
normal.paragraph_format.space_after = Pt(6)

for style_name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
    style = styles[style_name]
    style.font.name = "Times New Roman"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

styles["Heading 1"].font.size = Pt(16)
styles["Heading 1"].font.bold = True
styles["Heading 1"].font.color.rgb = RGBColor(31, 78, 121)
styles["Heading 1"].paragraph_format.space_before = Pt(12)
styles["Heading 1"].paragraph_format.space_after = Pt(8)
styles["Heading 1"].paragraph_format.keep_with_next = True
styles["Heading 2"].font.size = Pt(13)
styles["Heading 2"].font.bold = True
styles["Heading 2"].paragraph_format.space_before = Pt(10)
styles["Heading 2"].paragraph_format.keep_with_next = True
styles["Heading 3"].font.size = Pt(12)
styles["Heading 3"].font.bold = True

footer = section.footer
p = footer.paragraphs[0]
add_page_number(p)


def p(text="", bold=False, align=None, italic=False):
    para = doc.add_paragraph()
    if align is not None:
        para.alignment = align
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    return para


def heading(text, level=1):
    para = doc.add_heading(text, level=level)
    return para


def bullets(items):
    for item in items:
        para = doc.add_paragraph()
        para.style = doc.styles["Normal"]
        para.paragraph_format.left_indent = Inches(0.25)
        para.paragraph_format.first_line_indent = Inches(-0.25)
        para.add_run("• ").bold = True
        para.add_run(item)


def page_break():
    doc.add_page_break()


# Cover page
for _ in range(2):
    p()
p("A PROJECT REPORT", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("ON", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("A project report submitted in partial fulfillment of the requirements for the degree of Master of Technology in Artificial Intelligence & Machine Learning", align=WD_ALIGN_PARAGRAPH.CENTER)
p()
p("MASTER OF TECHNOLOGY IN ARTIFICIAL INTELLIGENCE & MACHINE LEARNING", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p()
p("Submitted by:", align=WD_ALIGN_PARAGRAPH.CENTER)
p("[Student Name] — [PRN]", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("Group Number: [Group Number]", align=WD_ALIGN_PARAGRAPH.CENTER)
p()
p("UNDER THE GUIDANCE OF", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("Dr. Nivedita Mishra", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("Assistant Professor", align=WD_ALIGN_PARAGRAPH.CENTER)
p()
p("Pune – 412115, Maharashtra State, India", align=WD_ALIGN_PARAGRAPH.CENTER)
p("https://www.sitpune.edu.in/", align=WD_ALIGN_PARAGRAPH.CENTER)
p()
p("DEPARTMENT OF ARTIFICIAL INTELLIGENCE & MACHINE LEARNING", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("AY 2026–27", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

page_break()

# Certificate
p("DEPARTMENT OF ARTIFICIAL INTELLIGENCE & MACHINE LEARNING", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("CERTIFICATE", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("This is to certify that the project work entitled “KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security” is carried out by [Student Name], in partial fulfillment for the award of the degree of Master of Technology in Artificial Intelligence & Machine Learning, Symbiosis International (Deemed University), Pune during the academic year 2026–2027.")
p()
p("Place: Pune")
p("Date: ___ / ___ / 2026")
p()
table = doc.add_table(rows=3, cols=2)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
no_borders(table)
table.cell(0, 0).text = "Name and Signature of the Guide"
table.cell(0, 1).text = "Dr. Sumit Kumar"
table.cell(1, 1).text = "Head, Department of AI & ML"
table.cell(2, 0).text = "Dr. Nivedita Mishra"
table.cell(2, 1).text = "Symbiosis Institute of Technology"

page_break()
p("DECLARATION", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("I hereby declare that the project titled “KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security” submitted to Symbiosis Institute of Technology, Constituent of Symbiosis International (Deemed University), Pune for the award of the degree of Master of Technology in Artificial Intelligence & Machine Learning is the result of original work carried out during this project. I understand that my report may be made electronically available to the public. I further declare that this report or any substantial part of it has not previously been submitted to any university or institute for the award of a degree or diploma.")
add_table(doc, ["Field", "Details"], [
    ("Name(s) of Student(s)", "[Student Name]"),
    ("PRN", "[PRN]"),
    ("Degree", "Master of Technology in AI & ML"),
    ("Department", "Artificial Intelligence & Machine Learning"),
    ("Title of the project", "KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security"),
])
p("_________________________________", align=WD_ALIGN_PARAGRAPH.CENTER)
p("(Signature of the Student)", align=WD_ALIGN_PARAGRAPH.CENTER)
p("Date: ___ / ___ / 2026", align=WD_ALIGN_PARAGRAPH.CENTER)

page_break()
p("ACKNOWLEDGEMENT", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("I express my sincere appreciation to my project guide, Dr. Nivedita Mishra, for her guidance, constructive feedback, and support throughout the project. Her suggestions helped me maintain a clear connection between the security problem, the experimental method, and the final implementation.")
p("I am grateful to Dr. Sumit Kumar, Head of the Department of Artificial Intelligence & Machine Learning, and to Symbiosis Institute of Technology for providing the academic environment and resources needed to conduct this work.")
p("I also thank my project team members for their assistance in reviewing the implementation and validating the documentation. I acknowledge the support of my family and friends, whose encouragement sustained the project from planning through evaluation.")
p("Finally, I thank the creators of the CICIoT2023 dataset and the maintainers of the open-source Python libraries used in this work. Their publicly available research resources enabled repeatable experimentation on realistic IoT network traffic.")

page_break()
p("ABSTRACT", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
p("IoT systems often retain a session key until a fixed schedule or a predefined lifetime is reached. This design leaves a compromised device able to use its trusted key for an unnecessarily long period. The KeyShield-IoT project addresses this weakness by combining network-anomaly scores with hysteresis, rotation cooldown, persistent-compromise revocation, a maximum lifetime safety net, and a signed cryptographic audit trail. The system was implemented as a replay-based experimental platform rather than as a physical-device deployment.")
p("CICIoT2023 network traffic was organized into 60-second, ten-flow windows and divided by device and seed. Isolation Forest, One-Class SVM, Autoencoder, and a supervised Random Forest reference were compared using validation-selected thresholds. Isolation Forest was selected as the live model because it gave 0.995 mean ROC-AUC, 0.972 mean PR-AUC, 0.938 mean recall at the 99th-percentile benign threshold, and 1.000 mean episode detection. Across 20 test episodes per policy, the adaptive and hybrid policies achieved 57 seconds mean Key Exposure Window (KEW) in the key-theft scenario and 342 seconds in the device-compromise scenario. The fixed 60-window schedule showed 1797 seconds mean KEW in key theft and 31,377 seconds in full device compromise.")
p("The project supports secure, reliable, and innovation-oriented digital infrastructure in line with United Nations Sustainable Development Goal 9: Industry, Innovation and Infrastructure. The major limitation is that replayed traffic and simulated device compromise do not reproduce every constraint of physical IoT hardware. Nevertheless, the results indicate that anomaly-aware responses can reduce exposure without relying on frequent fixed rotations.")
p("Keywords: adaptive key rotation, IoT security, anomaly detection, CICIoT2023, key exposure window, adaptive security, SDG 9, resilient infrastructure")

page_break()
p("TABLE OF CONTENTS", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
toc = doc.add_paragraph()
add_field(toc, 'TOC \\o "1-3" \\h \\z \\u')

page_break()
p("LIST OF TABLES", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
for text in [
    "Table 2.1  Summary of related work and identified research gap",
    "Table 3.1  Software tools and frameworks",
    "Table 3.2  Hardware and execution environment",
    "Table 3.3  Work breakdown structure",
    "Table 3.4  Functional requirements",
    "Table 3.5  Non-functional requirements",
    "Table 3.6  Project cost estimation",
    "Table 4.1  CICIoT2023 experiment data summary",
    "Table 4.2  Model comparison on test windows",
    "Table 4.3  Recall by attack category",
    "Table 4.4  Policy performance across scenarios",
    "Table 4.5  Cryptographic benchmark",
]:
    p(text)

page_break()
p("LIST OF FIGURES", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
for text in [
    "Figure 2.1  KeyShield-IoT concept",
    "Figure 4.1  End-to-end system methodology",
    "Figure 4.2  Window construction and model evaluation",
    "Figure 5.1  ROC curves",
    "Figure 5.2  Precision-recall curves",
    "Figure 5.3  Recall by attack category",
    "Figure 5.4  KEW by policy and scenario",
    "Figure 5.5  Exposed Attack Volume",
    "Figure 5.6  Rotation cost",
]:
    p(text)

page_break()
p("LIST OF ABBREVIATIONS", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
add_table(doc, ["Abbreviation", "Meaning"], [
    ("AE", "Autoencoder"),
    ("AEAD", "Authenticated Encryption with Associated Data"),
    ("AIC", "Academic Integrity Check"),
    ("CA", "Certificate Authority"),
    ("CIC", "Canadian Institute for Cybersecurity"),
    ("EAV", "Exposed Attack Volume"),
    ("ECDSA", "Elliptic Curve Digital Signature Algorithm"),
    ("EWMA", "Exponentially Weighted Moving Average"),
    ("IoT", "Internet of Things"),
    ("KEW", "Key Exposure Window"),
    ("ML", "Machine Learning"),
    ("ROC-AUC", "Receiver Operating Characteristic — Area Under Curve"),
    ("PR-AUC", "Precision-Recall — Area Under Curve"),
    ("RF", "Random Forest"),
    ("SDG", "Sustainable Development Goal"),
    ("S1", "Scenario 1: key theft while the device remains otherwise functional"),
    ("S2", "Scenario 2: device compromise and attacker control"),
])

page_break()
heading("Chapter 1: Introduction", 1)
heading("1.1 Introduction", 2)
p("Internet of Things networks connect sensors, controllers, gateways, cameras, vehicles, meters, and industrial equipment to digital services. These devices are often resource constrained and may operate for long periods with limited operator supervision. Consequently, authentication and session protection must remain reliable even when the network contains noisy traffic or incomplete information [1].")
p("Cryptographic key rotation limits the interval during which a stolen session key remains useful. However, rotation is not cost-free: a handshake, certificate update, or key agreement operation consumes processing time and may interrupt communication. Fixed schedules simplify deployment but do not respond to the actual risk. A device that is not threatened may be rotated unnecessarily, while a compromised device may continue using a valid key until the next scheduled interval [2], [3].")
p("KeyShield-IoT was designed to separate detection from enforcement. An anomaly detector assigns a risk score to 60-second traffic windows. An adaptive policy converts the score into warning, rotation, or revocation actions. This separation allows the project to compare the AI policy against fixed schedules and static thresholds using the same replayed traffic and the same cryptographic operations.")

heading("1.2 Problem statement", 2)
p("The central problem is that long-lived session keys create a large exposure window after compromise. A fixed schedule may rotate too slowly to protect a compromised device and may rotate too frequently for ordinary devices. The project therefore investigates the following problem:")
p("How can an IoT key-management system adapt the timing of session-key rotation using network anomaly evidence while controlling false rotations, limiting attacker-delivered traffic, and preserving a maximum-key-lifetime safety mechanism?")
p("Two attacker scenarios are considered. In Scenario S1, the attacker steals or obtains a key but the device remains under defender control. In Scenario S2, the attacker controls the device and continues to deliver attack traffic. KEW measures the time or number of windows in which the session key remains exposed. EAV measures the number of attack windows delivered after compromise [4].")

heading("1.3 Scope of research", 2)
p("The implementation and evaluation cover offline replay of the CICIoT2023 dataset, feature-window construction, unsupervised and reference-supervised learning, threshold calibration, adaptive mitigation policies, ECDSA-signed audit logging, AES-256-GCM session protection, and measurement of KEW, EAV, and rotation cost.")
p("The work does not claim a physical-device certification. It does not reproduce radio impairments, battery discharge, firmware rollback, certificate provisioning in an industrial fleet, or compromised cloud gateways. The evaluation is intentionally replay-based so that each policy receives the same traffic sequence across repeated seeds.")

heading("1.4 Research hypothesis", 2)
p("It is hypothesized that an adaptive policy with calibrated anomaly thresholds, hysteresis, and cooldown will achieve a lower mean KEW and EAV than fixed interval policies when the anomaly detector is able to identify sustained hostile behavior. It is also hypothesized that a supervised reference model may provide high category recall, while an unsupervised Isolation Forest offers a suitable live detector because it requires no attack labels during training.")

heading("1.5 Objectives", 2)
bullets([
    "Process the CICIoT2023 CSV records into fixed-size network windows and device streams.",
    "Compare Isolation Forest, One-Class SVM, Autoencoder, and Random Forest for anomaly detection.",
    "Calibrate adaptive warning, rotation, and revocation thresholds only from benign validation traffic.",
    "Implement adaptive, static, fixed-interval, and hybrid key-management policies.",
    "Measure KEW, EAV, detection rate, false rotation rate, revocation frequency, and cryptographic cost.",
    "Provide an auditable, hash-chained security event log and a live Streamlit demonstration.",
    "Discuss limitations, reproducibility, operational implications, and future research.",
])

heading("1.6 Organization of the report", 2)
p("Chapter 2 reviews key management and anomaly-detection literature. Chapter 3 defines the software, hardware, requirements, work breakdown, and cost. Chapter 4 explains the data pipeline, model selection, cryptographic mechanism, policy logic, and evaluation protocol. Chapter 5 presents results and discusses their implications. Chapter 6 concludes the work and identifies future scope.")

page_break()
heading("Chapter 2: Literature Review", 1)
heading("2.1 Background", 2)
p("Key-management recommendations emphasize that cryptographic keys have a lifecycle: generation, distribution, use, rotation, and revocation. Excessively long cryptoperiods increase the consequences of exposure, while frequent rotation increases operational cost [2]. In IoT deployments, revocation and key replacement must account for constrained devices and unreliable connectivity [3].")
p("Isolation Forest is suitable for resource-conscious anomaly detection because it isolates unusual observations through random sub-samples and short path lengths rather than profiling a dense normal distribution [5]. One-Class SVM and Autoencoders offer complementary approaches by modeling support or reconstruction behavior from benign data [6]. Supervised Random Forest can provide a useful reference when labeled attacks are available, but unsupervised operation is more robust to unknown attacks.")
p("CICIoT2023 is a benchmark containing real and simulated IoT network traffic, benign flows, and numerous attack types across an extensive testbed [7], [8]. Its scale and category diversity make it useful for evaluating anomaly detection, although it cannot replace hardware-level testing.")
add_caption(doc, "Table 2.1: Summary of related work and identified research gap")
add_table(doc, ["Reference", "Contribution", "Limitation", "Gap addressed by KeyShield-IoT"], [
    ("NIST SP 800-57 [2]", "Key lifecycle and cryptoperiod guidance", "Not an IoT anomaly-response controller", "Links risk evidence to rotation and revocation"),
    ("NIST IoT Program [3]", "Device and lifecycle cybersecurity guidance", "Broad recommendations", "Adds measurable replay-based evaluation"),
    ("Liu et al. [5]", "Isolation Forest anomaly method", "Detection scores require calibration", "Hysteresis, cooldown, EWMA, and revocation policy"),
    ("CICIoT2023 [7]", "Large IoT attack benchmark", "Replay, not physical compromise", "Uses five seeds and two mitigation scenarios"),
    ("AES-GCM and ECDSA practice [9]", "Confidentiality, integrity, and signing primitives", "Primitives do not decide response timing", "Audit log and session protection around adaptive policy"),
])

heading("2.2 Summary of literature review and research gap", 2)
p("The literature provides strong support for lifecycle-based key management and machine-learning-based intrusion detection. It also identifies a separation between detection and decision control: anomaly scores are not, by themselves, a complete security response. Existing systems commonly apply fixed rotation periods or generic alerts. Few replay studies jointly evaluate detector quality, policy timing, cryptographic cost, and attacker exposure.")
p("KeyShield-IoT addresses this gap by defining a single stateful policy for each device, measuring exposure in S1 and S2, including a fallback action at maximum lifetime, and retaining all actions in a signed hash-chained audit log. The project does not claim that a detector guarantees safety; rather, it evaluates the consequences of detector outputs when they are converted into operational security actions.")

page_break()
heading("Chapter 3: Software Requirements Specification", 1)
heading("3.1 Software tool platform and frameworks", 2)
add_caption(doc, "Table 3.1: Software tools and frameworks")
add_table(doc, ["Component", "Technology", "Purpose"], [
    ("Language", "Python 3.13", "Implementation and experiments"),
    ("Data processing", "Pandas, PyArrow, NumPy", "Loading, windowing, and replay"),
    ("Machine learning", "scikit-learn", "Isolation Forest, OCSVM, Autoencoder, Random Forest"),
    ("Cryptography", "cryptography library", "ECDSA, ECDH, AES-256-GCM"),
    ("Dashboard", "Streamlit", "Interactive replay and audit verification"),
    ("Visualization", "Matplotlib, Plotly", "Figures and live dashboard"),
    ("Testing", "pytest", "Unit and integration tests"),
    ("Data format", "CSV, Parquet, JSON", "Raw and processed artifacts"),
])

heading("3.2 Hardware tools", 2)
add_caption(doc, "Table 3.2: Hardware and execution environment")
add_table(doc, ["Item", "Specification or role"], [
    ("Development host", "Windows workstation"),
    ("Processor", "Used for scikit-learn and replay experiments"),
    ("Memory", "Sufficient for Parquet streams and in-memory models"),
    ("Storage", "Local workspace for CICIoT2023 and generated artifacts"),
    ("IoT target", "No physical device used; replayed traffic only"),
])

heading("3.3 Work breakdown structure", 2)
add_caption(doc, "Table 3.3: Work breakdown structure")
add_table(doc, ["Phase", "Activities", "Outcome"], [
    ("Data engineering", "Inspect, clean, split, and generate windows", "Train, validation, and test streams"),
    ("Feature/model", "Drop constant/correlated features, train and compare models", "Four model comparison table"),
    ("Crypto/audit", "Implement CA, sessions, key epochs, signatures", "Signed key-management service"),
    ("Decision engine", "Implement adaptive and baseline policies", "Stateful per-device actions"),
    ("Evaluation", "Compute KEW, EAV, cost, and category recall", "Measured policy comparison"),
    ("User interface", "Build dashboard and replay controls", "Demonstration interface"),
    ("Validation", "Run pytest and inspect reports", "Verified implementation"),
])

heading("3.4 Functional requirements", 2)
add_caption(doc, "Table 3.4: Functional requirements")
add_table(doc, ["ID", "Requirement", "Verification"], [
    ("FR-01", "Load and validate CICIoT2023 CSV records.", "Build report and tests"),
    ("FR-02", "Construct fixed 10-flow, 60-second windows.", "Feature/window tests"),
    ("FR-03", "Train and score four candidate detectors.", "Model comparison report"),
    ("FR-04", "Select thresholds only from validation benign scores.", "Evaluation implementation"),
    ("FR-05", "Support WARN, ROTATE, and REVOKE actions.", "Engine tests"),
    ("FR-06", "Prevent rotation storm through cooldown.", "Policy unit tests"),
    ("FR-07", "Encrypt session traffic with AES-256-GCM.", "Crypto tests"),
    ("FR-08", "Sign and append audit events.", "Audit-log verification"),
    ("FR-09", "Replay S1 and S2 attack scenarios.", "E3 experiment report"),
])

heading("3.5 Non-functional requirements", 2)
add_caption(doc, "Table 3.5: Non-functional requirements")
add_table(doc, ["ID", "Requirement", "Acceptance criterion"], [
    ("NFR-01", "Reproducibility", "Five configured seeds; deterministic demo"),
    ("NFR-02", "Low overhead", "Benchmarked handshake and rotation times"),
    ("NFR-03", "Auditability", "Hash-chained and ECDSA-signed events"),
    ("NFR-04", "Maintainability", "Configurable data, model, policy, and evaluation modules"),
    ("NFR-05", "Usability", "Streamlit dashboard for replay and verification"),
    ("NFR-06", "Safety", "Maximum-lifetime fallback for the hybrid policy"),
])

heading("3.6 Project cost estimation", 2)
add_caption(doc, "Table 3.6: Project cost estimation")
add_table(doc, ["Cost component", "Estimate", "Basis"], [
    ("Development workstation", "Existing institutional resource", "No additional purchase"),
    ("Software licenses", "Open-source / ₹0", "Python and listed libraries"),
    ("CICIoT2023 dataset", "Public research resource", "No dataset purchase"),
    ("Cloud/physical IoT devices", "Not used", "Replay-based prototype"),
    ("Projected deployment hardware", "Site-dependent", "Gateway, fleet identity, and secure storage"),
])

page_break()
heading("Chapter 4: Methodology", 1)
heading("4.1 System architecture and data preparation", 2)
plt.figure(figsize=(9, 5))
plt.axis("off")
boxes = [
    (0.02, 0.58, "CICIoT2023\nMERGED CSV"),
    (0.25, 0.58, "Cleaning +\nFeature Windows"),
    (0.48, 0.58, "Anomaly\nModels"),
    (0.71, 0.58, "Adaptive\nPolicy"),
    (0.86, 0.58, "KeyManager\n+ CA"),
]
for x, y, text in boxes:
    plt.text(x, y, text, ha="center", va="center", bbox=dict(boxstyle="round,pad=0.45", fc="#D9E2F3", ec="#1F4E79"), fontsize=9)
for x1, x2 in ((0.12,0.25),(0.35,0.48),(0.58,0.71),(0.79,0.86)):
    plt.annotate("", xy=(x2,0.58), xytext=(x1,0.58), arrowprops=dict(arrowstyle="->", lw=1.5))
plt.text(0.50,0.28,"Same replay streams feed S1 and S2\nKEW, EAV, cost, audit-log, and dashboard evaluation",ha="center",fontsize=10,bbox=dict(boxstyle="round,pad=0.5",fc="#E2F0D9",ec="#548235"))
plt.tight_layout()
arch_path = ROOT / "report" / "figures" / "keyshield_architecture.png"
arch_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(arch_path, dpi=300, bbox_inches="tight")
plt.close()
doc.add_picture(str(arch_path), width=Inches(6.5))
add_caption(doc, "Figure 4.1: End-to-end system methodology")

p("The raw data consisted of six CICIoT2023 MERGED CSV files containing 4,297,838 rows. Benign and attack records were grouped into pools and distributed across 12 training devices, 4 validation devices, and 4 test devices for seeds 42–46. The project uses 1000 windows per device, 10 flows per window, and 60 seconds per window.")
add_caption(doc, "Table 4.1: CICIoT2023 experiment data summary")
add_table(doc, ["Dataset item", "Value"], [
    ("Raw rows", "4,297,838"),
    ("Training pool rows", "657,484"),
    ("Validation pool rows", "219,159"),
    ("Test pool rows", "219,162"),
    ("Windows per device", "1000"),
    ("Flows per window", "10"),
    ("Seconds per window", "60"),
    ("Seeds", "42, 43, 44, 45, 46"),
])
p("The feature pipeline begins with 39 flow features and calculates mean, standard deviation, and maximum summaries, producing 75 window columns. Constant and correlated fields are removed according to the project report configuration. Low-support and web/brute-force classes are excluded from the experiment as documented in the repository [10].")

heading("4.2 Model training and threshold calibration", 2)
p("Isolation Forest, One-Class SVM, and Autoencoder were trained only on benign windows. Random Forest was trained as a supervised reference using benign and selected attack windows. Validation thresholds were selected using the 99th percentile of benign scores. A separate best-F1 threshold was used in model comparison only as an additional reference, not to tune the policy on test data.")
p("Isolation Forest uses 200 trees and a maximum sample size of 1024. One-Class SVM uses nu=0.02 and scale gamma with a maximum training set of 30,000. The Autoencoder uses a 64–32–16–32–64 hidden structure. Live thresholds were derived from validation calibration: warn = −0.026438, rotate = 0.010265, and revoke = 0.051987.")

heading("4.3 Adaptive mitigation policy", 2)
p("The adaptive policy maintains a separate state dictionary for every device. A severe score that reaches 1.5 times the rotation threshold triggers immediate rotation if cooldown has expired. Otherwise, the policy requires at least two of the latest three windows to cross the warning condition. A WARN action is not sufficient to change the current key; a confirmed ROTATE action creates a new key epoch.")
p("After rotation, a ten-window cooldown begins. A score at or above the rotation threshold in five consecutive cooldown windows raises the device to REVOKE. The policy also maintains a gated EWMA only for scores below the rotation threshold, preventing sustained attacks from silently raising the device baseline.")
p("The hybrid policy wraps the adaptive policy and forces a rotation after 720 windows without a successful adaptive or baseline rotation. The fixed-interval policy rotates every 60, 180, 360, or 720 windows. The static policy uses fixed thresholds without hysteresis.")

heading("4.4 Cryptographic design", 2)
p("A certificate authority enrolls devices and establishes a session key for a device epoch. ECDSA provides signed audit events. ECDH establishes a session, while AES-256-GCM encrypts and authenticates application messages [9], [11]. Rotation increments the device epoch and revocation prevents further session establishment.")
p("Every audit event contains an event sequence, timestamp, device identifier, epoch, action, and the hash of the previous event. The event is signed and verification checks both the hash chain and the ECDSA signature. This design enables traceability but does not prove that a physical device is uncompromised.")

heading("4.5 Evaluation methodology", 2)
p("Experiment E1 compares models using ROC-AUC, PR-AUC, precision, recall, F1, false-positive rate, episode detection, and median delay. Experiment E2 reports recall by category and sublabel. Experiment E3 compares policies in S1 and S2 using KEW, EAV, detection rate, rotations per device-hour, false rotation rate, revokes per run, and cryptographic overhead.")
p("KEW is calculated as the interval between a compromised key or attacker-control onset and the first effective rotation or revocation. EAV is the number of attack windows delivered after the onset while the exposed key or compromised state remains usable. Censored episodes are those for which no valid mitigation occurs before the replay horizon.")

page_break()
heading("Chapter 5: Results and Discussion", 1)
heading("5.1 Model comparison", 2)
add_caption(doc, "Table 4.2: Model comparison on test windows")
add_table(doc, ["Model", "ROC-AUC", "PR-AUC", "Precision@99", "Recall@99", "F1@99", "Episode detect"], [
    ("Isolation Forest", "0.995 ± 0.005", "0.972 ± 0.026", "0.866 ± 0.029", "0.938 ± 0.055", "0.900 ± 0.033", "1.000"),
    ("One-Class SVM", "0.995 ± 0.004", "0.977 ± 0.020", "0.888 ± 0.033", "0.947 ± 0.039", "0.916 ± 0.028", "1.000"),
    ("Autoencoder", "0.992 ± 0.006", "0.951 ± 0.036", "0.876 ± 0.033", "0.883 ± 0.083", "0.878 ± 0.052", "1.000"),
    ("Random Forest", "0.999 ± 0.001", "0.995 ± 0.006", "0.886 ± 0.043", "0.992 ± 0.009", "0.936 ± 0.028", "1.000"),
])
p("The supervised Random Forest produced the strongest aggregate metrics, including 0.999 ROC-AUC and 0.992 recall. The result is consistent with its use of attack labels. Isolation Forest was selected for live operation because it is an unsupervised method with 0.995 ROC-AUC and low training cost (0.38 seconds). It therefore provides a useful compromise between detection, independence from attack labels, and resource use.")

for fname, cap in [
    ("e1_roc.png", "Figure 5.1: ROC curves (test windows, all seeds)"),
    ("e1_pr.png", "Figure 5.2: Precision-recall curves (test windows, all seeds)"),
]:
    path = ROOT / "report" / "figures" / fname
    if path.exists():
        doc.add_picture(str(path), width=Inches(5.8))
        add_caption(doc, cap)

heading("5.2 Category recall", 2)
add_caption(doc, "Table 4.3: Recall by attack category")
add_table(doc, ["Category", "Isolation Forest", "One-Class SVM", "Autoencoder", "Random Forest"], [
    ("DDoS", "1.000", "1.000", "1.000", "1.000"),
    ("DoS", "1.000", "1.000", "1.000", "1.000"),
    ("Mirai", "1.000", "1.000", "1.000", "1.000"),
    ("Recon", "0.865", "0.897", "0.765", "0.981"),
    ("Spoofing", "0.721", "0.738", "0.430", "0.977"),
])
p("DDoS, DoS, and Mirai traffic were detected reliably by all four models. Recon and spoofing categories were more difficult, especially for the Autoencoder. Spoofing recall for Isolation Forest was 0.721 and remained lower than Random Forest's 0.977. This difference is important because a replay model may miss stealthier or low-volume behaviors.")
hm = ROOT / "report" / "figures" / "e2_category_recall.png"
if hm.exists():
    doc.add_picture(str(hm), width=Inches(6.2))
    add_caption(doc, "Figure 5.3: Recall by attack category")

heading("5.3 Policy exposure and cost", 2)
add_caption(doc, "Table 4.4: Policy performance across scenarios")
add_table(doc, ["Policy", "S1 KEW", "S2 KEW", "S1 EAV", "S2 EAV", "Detection"], [
    ("AI adaptive", "57 ± 51 s", "342 ± 85 s", "0.95 ± 0.84", "5.70 ± 1.41", "1.000"),
    ("Hybrid", "57 ± 51 s", "342 ± 85 s", "0.95 ± 0.84", "5.70 ± 1.41", "1.000"),
    ("Static rule", "17,337 ± 9,920 s", "17,337 ± 9,920 s", "0.00 ± 0.00", "0.00 ± 0.00", "0.400"),
    ("Fixed T=60", "1,797 ± 341 s", "31,377 ± 1,436 s", "28.90 ± 5.46", "75.45 ± 14.58", "S1 1.0 / S2 0.0"),
    ("Fixed T=180", "5,397 ± 1,272 s", "31,377 ± 1,436 s", "56.85 ± 12.82", "75.45 ± 14.58", "S1 1.0 / S2 0.0"),
    ("Fixed T=360", "11,697 ± 3,161 s", "31,377 ± 1,436 s", "61.80 ± 8.99", "75.45 ± 14.58", "S1 0.85 / S2 0.0"),
])
p("The adaptive and hybrid policies produced identical performance in this experiment. They detected all 20 episodes in S1 and S2 and had 57 seconds mean KEW in S1 and 342 seconds in S2. The fixed 60-window policy detected S1 episodes but was censored in S2 because it could not revoke a device that remained under attacker control.")
p("The static-rule policy detected only 40 percent of episodes in this replay. It demonstrated that fixed thresholds can miss low-frequency attacks or react unpredictably in categories with weak separation.")

for fname, cap in [
    ("e3_kew_boxplot.png", "Figure 5.4: KEW by policy and scenario"),
    ("e3_eav_bar.png", "Figure 5.5: Exposed Attack Volume"),
    ("e3_cost_bar.png", "Figure 5.6: Rotation cost"),
]:
    path = ROOT / "report" / "figures" / fname
    if path.exists():
        doc.add_picture(str(path), width=Inches(6.2))
        add_caption(doc, cap)

heading("5.4 Cryptographic and operational results", 2)
add_caption(doc, "Table 4.5: Cryptographic benchmark")
add_table(doc, ["Operation", "Samples", "Mean time"], [
    ("ECDH handshake / establish session", "500", "0.316 ms"),
    ("Key rotation", "500", "0.336 ms"),
    ("AES-GCM encrypt 64 B", "2000", "0.00376 ms"),
    ("AES-GCM decrypt 64 B", "2000", "0.00405 ms"),
])
p("Handshake and rotation overhead remained below 0.34 milliseconds per operation in the local benchmark. AES-GCM overhead was also small. These values show that cryptographic primitives are not the dominant cost in the simulated system. The adaptive policy still consumed 0.32 rotations per device-hour, compared with 1.02 for the fixed 60-window schedule.")
p("The adaptive policy reported 4.00 revokes per run and a false-rotation rate of 0.842. The false-rotation metric is sensitive to the replay construction and should not be interpreted as a fleet-wide false alarm probability: it averages policy actions on episodes and benign-like windows rather than production incident reports.")

heading("5.5 Discussion and limitations", 2)
p("The results support the hypothesis that adaptive mitigation reduces exposure in replayed traffic. The S1 result is strongest because key theft leaves the defender able to enforce rotation and revoke sessions. The S2 result shows why S2 requires persistent detection and revocation: fixed schedules alone allow scheduled or long-lifetime keys to remain useful even when the device is controlled.")
p("The model and policy evaluation has several limitations. First, CICIoT2023 is replayed traffic; radio, firmware, physical tampering, and battery behavior are not modeled. Second, benign traffic reuse in the build process may reduce stream diversity. Third, category support differs substantially: recon and spoofing have fewer or less separable examples than DDoS and Mirai. Fourth, the project uses a 60-second window and may not detect a burst that is shorter than the window. Fifth, local benchmark values describe this development host and are not a guarantee of embedded-device performance.")
p("The signed log, certificate authority, and key epochs are defensive mechanisms, but they rely on secure enrollment and protected private keys. The prototype assumes secure credentials, updated firmware, network segmentation, and disabled unused services. These assumptions are consistent with basic IoT hygiene but remain deployment responsibilities.")

page_break()
heading("Chapter 6: Conclusion and Future Scope", 1)
heading("6.1 Conclusion", 2)
p("KeyShield-IoT provides an evidence-driven method for adapting session-key rotation in IoT environments. It combines anomaly detection, hysteresis, cooldown, EWMA baseline gating, persistent-compromise revocation, a hybrid maximum-lifetime fallback, and cryptographic auditability.")
p("Across five seeds, Isolation Forest was a suitable unsupervised live detector, achieving 0.995 mean ROC-AUC and complete episode detection. The adaptive policy reduced mean KEW to 57 seconds in S1 and 342 seconds in S2, compared with fixed-interval baselines that showed substantially larger exposure in the replay. The hybrid policy matched adaptive performance while adding a lifetime safeguard.")
p("The implementation is not a claim of universal security. It is a measured prototype that shows how detector quality, policy state, and cryptographic enforcement interact. The main engineering lesson is that key management should respond to evidence while retaining bounded behavior through cooldown and maximum lifetime.")

heading("6.2 Future scope", 2)
bullets([
    "Deploy the system on constrained devices or an emulated IoT gateway and measure battery and memory overhead.",
    "Evaluate the protocol with real certificates, transport security, and secure private-key storage.",
    "Improve spoofing and reconnaissance detection using temporal graph features or protocol-specific behavior.",
    "Integrate federated or continual learning so devices can update their local baseline without centralizing sensitive traffic.",
    "Add a formal key-rotation state machine and test it with model checking or property-based tests.",
    "Study alert fatigue, operator confirmation, and recovery from false revocation in a human-in-the-loop environment.",
    "Repeat the experiment on additional datasets and diverse IoT protocols to reduce dataset dependence.",
    "Add resilience against compromised gateways, replayed signed events, and certificate revocation-list delays.",
])

page_break()
p("REFERENCES (IEEE format)", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
refs = [
    "[1] E. S. R. M. Neto, S. Dadkhah, R. Ferreira, A. Zohourian, H. Lu, and A. A. Ghorbani, “CICIoT2023: A real-time dataset and benchmark for large-scale attacks in IoT environment,” Sensors, vol. 23, no. 13, 2023, doi: 10.3390/s23136128.",
    "[2] E. Barker, “Recommendation for key management: Part 1 – General,” NIST Special Publication 800-57 Part 1 Revision 5, NIST, Gaithersburg, MD, USA, May 2020.",
    "[3] K. Megas, B. Cuthill, M. Fagan, and P. Watrobski, “NIST Cybersecurity for IoT Program,” IEEE Computer, 2024.",
    "[4] KeyShield-IoT project, “KEW, EAV, and episode evaluation definitions,” source repository, 2026. [Online]. Available: https://github.com/shreyastaralekar/keyshield-iot-Final",
    "[5] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation forest,” in Proc. 2008 Eighth IEEE Int. Conf. Data Mining, Dec. 2008, pp. 413–422.",
    "[6] B. Schölkopf, J. C. Platt, J. Shawe-Taylor, A. J. Smola, and R. C. Williamson, “Estimating the support of a high-dimensional distribution,” Neural Computation, vol. 13, no. 7, pp. 1443–1471, 2001.",
    "[7] Canadian Institute for Cybersecurity, “IoT Dataset 2023,” University of New Brunswick, 2023. [Online]. Available: https://www.unb.ca/cic/datasets/iotdataset-2023.html",
    "[8] Canadian Institute for Cybersecurity, “CICIoT2023 dataset repository,” 2023. [Online]. Available: https://github.com/topics/ciciot2023",
    "[9] D. McGrew and J. Viega, “The Galois/Counter Mode of operation (GCM),” Journal of Cryptology, 2005.",
    "[10] KeyShield-IoT project, “README and implementation documentation,” 2026. [Online]. Available: https://github.com/shreyastaralekar/keyshield-iot-Final",
    "[11] E. Rescorla, “The Transport Layer Security (TLS) Protocol Version 1.3,” RFC 8446, IETF, Aug. 2018.",
    "[12] United Nations, “Goal 9: Industry, Innovation and Infrastructure,” 2026. [Online]. Available: https://sdgs.un.org/goals/goal9",
]
for ref in refs:
    para = doc.add_paragraph(ref)
    para.paragraph_format.left_indent = Inches(0.25)
    para.paragraph_format.first_line_indent = Inches(-0.25)

page_break()
heading("APPENDICES", 1)
heading("Appendix A: Academic Integrity Check (AIC) Form", 2)
p("The following fields must be completed and signed before submission. The AIC and plagiarism reports are appendices, not part of the report body.")
add_table(doc, ["AIC field", "Entry"], [
    ("Student name", "[Student Name]"),
    ("PRN", "[PRN]"),
    ("Project title", "KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security"),
    ("Originality / similarity result", "[Attach official Turnitin result]"),
    ("AI-content result", "[Attach official Turnitin AI result]"),
    ("Student declaration", "[Signature required]"),
    ("Guide declaration", "[Signature required]"),
])

heading("Appendix B: Similarity and AI Reports", 2)
p("Mandatory submission evidence: attach the official Turnitin similarity report PDF here. Attach the official AI-writing report PDF on the following page. Do not paste screenshots or estimates that do not match the institute report.")
p("Similarity target: less than 10 percent.")
p("AI-similarity target: 0 percent, subject to the institution's accepted verification output.")

heading("Appendix C: Research Paper / Publication Draft", 2)
p("A concise research-paper draft may be prepared from Chapters 2–5 and the project tables. Recommended sections are Abstract, Introduction, Dataset and Preprocessing, Methodology, Experimental Results, Discussion, Conclusion, and References.")

heading("Appendix D: Industry, Competition, and Other Outcome Evidence", 2)
p("Append certificates or evidence here if available. If no external certificate or competition evidence exists, mark the item as not applicable rather than inventing evidence.")

# Header for all pages
for s in doc.sections:
    s.header.is_linked_to_previous = False
    hp = s.header.paragraphs[0]
    hp.text = "KeyShield-IoT — M.Tech Mini Project Report"
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in hp.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(100, 100, 100)
    fp = s.footer.paragraphs[0]
    fp.text = ""
    add_page_number(fp)

# Ensure heading keep-with-next and widow control.
for para in doc.paragraphs:
    para_format = para.paragraph_format
    para_format.widow_control = True

doc.core_properties.title = "KeyShield-IoT: AI-Driven Adaptive Key Rotation for IoT Security"
doc.core_properties.subject = "M.Tech Mini Project Report"
doc.core_properties.author = "[Student Name]"
doc.core_properties.keywords = "IoT, adaptive key rotation, anomaly detection, CICIoT2023, SDG 9"

doc.save(OUT)
print(str(OUT))
