from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path

PATH = Path(r"D:\keyshield-iot Final\KeyShield_IoT_MTech_Mini_Project_Report.docx")
doc = Document(PATH)


def set_dotted_right_tab(paragraph):
    tabs = paragraph.paragraph_format.tab_stops
    tabs.add_tab_stop(Inches(6.15), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)


def insert_paragraph_before(paragraph, text="", page=None, indent=0, size=9):
    p = OxmlElement("w:p")
    paragraph._p.addprevious(p)
    from docx.text.paragraph import Paragraph
    new_p = Paragraph(p, paragraph._parent)
    new_p.paragraph_format.left_indent = Inches(indent)
    new_p.paragraph_format.right_indent = Inches(0)
    new_p.paragraph_format.space_before = Pt(0)
    new_p.paragraph_format.space_after = Pt(0)
    new_p.paragraph_format.line_spacing = 1.0
    set_dotted_right_tab(new_p)
    if page is not None:
        r1 = new_p.add_run(text)
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(size)
        r2 = new_p.add_run("\t" + str(page))
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(size)
    else:
        r = new_p.add_run(text)
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
    return new_p


def remove_between(start_text, end_text):
    paras = doc.paragraphs
    si = next(i for i, p in enumerate(paras) if p.text.strip() == start_text)
    ei = next(i for i, p in enumerate(paras) if i > si and p.text.strip() == end_text)
    for p in list(doc.paragraphs[si + 1:ei]):
        p._element.getparent().remove(p._element)
    return si, ei


# Replace the blank TOC field area with exact static entries.
si, ei = remove_between("TABLE OF CONTENTS", "LIST OF TABLES")
paras = doc.paragraphs
list_tables = next(p for p in paras if p.text.strip() == "LIST OF TABLES")

toc_entries = [
    ("Certificate", "i", 0),
    ("Declaration", "ii", 0),
    ("Acknowledgment", "iii", 0),
    ("Abstract", "iv", 0),
    ("Table of Contents", "v", 0),
    ("List of Tables", "vii", 0),
    ("List of Figures", "viii", 0),
    ("List of Abbreviations", "ix", 0),
    ("CHAPTER 1: INTRODUCTION", "1", 0),
    ("1.1 Introduction", "1", 0.25),
    ("1.2 Problem statement", "1", 0.25),
    ("1.3 Scope of research", "2", 0.25),
    ("1.4 Research hypothesis", "2", 0.25),
    ("1.5 Objectives", "3", 0.25),
    ("1.6 Organization of the report", "3", 0.25),
    ("CHAPTER 2: LITERATURE REVIEW", "4", 0),
    ("2.1 Background", "4", 0.25),
    ("2.2 Summary of literature review and research gap", "5", 0.25),
    ("CHAPTER 3: SOFTWARE REQUIREMENTS SPECIFICATION", "6", 0),
    ("3.1 Software Tool Platform/Tools/Framework used", "6", 0.25),
    ("3.2 Hardware tools", "6", 0.25),
    ("3.3 Work Breakdown Structure", "7", 0.25),
    ("3.4 Functional Requirements", "7", 0.25),
    ("3.5 Non-Functional Requirements", "8", 0.25),
    ("3.6 Project Cost Estimation", "9", 0.25),
    ("CHAPTER 4: METHODOLOGY", "10", 0),
    ("4.1 System architecture and data preparation", "10", 0.25),
    ("4.2 Model training and threshold calibration", "11", 0.25),
    ("4.3 Adaptive mitigation policy", "11", 0.25),
    ("4.4 Cryptographic design", "12", 0.25),
    ("4.5 Evaluation methodology", "12", 0.25),
    ("CHAPTER 5: RESULTS AND DISCUSSION", "14", 0),
    ("5.1 Model comparison", "14", 0.25),
    ("5.2 Category recall", "16", 0.25),
    ("5.3 Policy exposure and cost", "17", 0.25),
    ("5.4 Cryptographic and operational results", "20", 0.25),
    ("5.5 Discussion and limitations", "20", 0.25),
    ("CHAPTER 6: CONCLUSION AND FUTURE SCOPE", "22", 0),
    ("6.1 Conclusion", "22", 0.25),
    ("6.2 Future Scope", "22", 0.25),
    ("REFERENCES (IEEE format only)", "24", 0),
    ("APPENDICES", "26", 0),
]

anchor = list_tables
for text, page, indent in reversed(toc_entries):
    insert_paragraph_before(anchor, text, page, indent, 9)

# Replace only list-of-table entries.
paras = doc.paragraphs
st = next(i for i, p in enumerate(paras) if p.text.strip() == "LIST OF TABLES")
en = next(i for i, p in enumerate(paras) if i > st and p.text.strip() == "LIST OF FIGURES")
for p in list(doc.paragraphs[st + 1:en]):
    p._element.getparent().remove(p._element)
paras = doc.paragraphs
list_figures = next(p for p in paras if p.text.strip() == "LIST OF FIGURES")

table_entries = [
    ("Table 2.1  Summary of related work and identified research gap", "4"),
    ("Table 3.1  Software tools and frameworks", "6"),
    ("Table 3.2  Hardware and execution environment", "6"),
    ("Table 3.3  Work breakdown structure", "7"),
    ("Table 3.4  Functional requirements", "7"),
    ("Table 3.5  Non-functional requirements", "8"),
    ("Table 3.6  Project cost estimation", "9"),
    ("Table 4.1  CICIoT2023 experiment data summary", "10"),
    ("Table 4.2  Model comparison on test windows", "14"),
    ("Table 4.3  Recall by attack category", "16"),
    ("Table 4.4  Policy performance across scenarios", "17"),
    ("Table 4.5  Cryptographic benchmark", "20"),
]
for text, page in reversed(table_entries):
    insert_paragraph_before(list_figures, text, page, 0, 10)

# Replace only list-of-figure entries.
paras = doc.paragraphs
st = next(i for i, p in enumerate(paras) if p.text.strip() == "LIST OF FIGURES")
en = next(i for i, p in enumerate(paras) if i > st and p.text.strip() == "LIST OF ABBREVIATIONS")
for p in list(doc.paragraphs[st + 1:en]):
    p._element.getparent().remove(p._element)
paras = doc.paragraphs
list_abbr = next(p for p in paras if p.text.strip() == "LIST OF ABBREVIATIONS")

figure_entries = [
    ("Figure 4.1  End-to-end system methodology", "10"),
    ("Figure 5.1  ROC curves", "16"),
    ("Figure 5.2  Precision-recall curves", "16"),
    ("Figure 5.3  Recall by attack category", "17"),
    ("Figure 5.4  KEW by policy and scenario", "19"),
    ("Figure 5.5  Exposed Attack Volume", "19"),
    ("Figure 5.6  Rotation cost", "20"),
]
for text, page in reversed(figure_entries):
    insert_paragraph_before(list_abbr, text, page, 0, 10)

doc.save(PATH)
print(PATH)
