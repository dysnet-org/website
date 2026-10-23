#!/usr/bin/env python3
"""Two PDFs that explain the DysNet registry, in the look of the five-demands brief (build-demo.py,
build_brief_pdf): the waiting-room poster, one page a doctor can pin up, and the members' brief,
three pages an association can send to its families. Both carry a QR code to www.dysnet.org/app,
the address build-demo.py's REDIRECTS points at the registry page until the app opens to families.

Sources for every statement: the registry app's questions and answers (apps/registry/src/locales,
in the registry repository), the registry page of dysnet.org, and Health Data Safe's public
compliance matrix (compliance.datasafe.dev). Written 2026-10-17.

Run: python3 tools/build-member-pdfs.py   (Pillow is not needed; reportlab is, see requirements.txt)
Writes: docs/assets/dysnet-registry-poster.pdf and docs/assets/dysnet-registry-explained.pdf
"""
import pathlib

from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
LOGO = ASSETS / "img" / "dysnet-logo.png"
APP_URL = "https://www.dysnet.org/app/"   # printed: change the redirect in build-demo.py, never this
APP_SHOWN = "www.dysnet.org/app"

# the five-demands brief's palette
INK, MUTED = colors.HexColor("#241a33"), colors.HexColor("#5d5470")
PURPLE, PTEXT, PDEEP, PSOFT = (colors.HexColor("#9333ea"), colors.HexColor("#7222c2"),
                               colors.HexColor("#47156e"), colors.HexColor("#f3e8fd"))
LINE = colors.HexColor("#e6dcf2")
F, FB = "Helvetica", "Helvetica-Bold"


def styles(scale):
    """The brief's styles, scaled: 1 for the members' brief, larger for the poster read from a chair."""
    def st(name, **kw):
        base = dict(fontName=F, fontSize=8.9 * scale, leading=12.1 * scale, textColor=INK, spaceAfter=0)
        base.update(kw)
        return ParagraphStyle(name, **base)
    return {
        "kicker": st("kicker", fontName=FB, fontSize=7.6 * scale, leading=10 * scale, textColor=PTEXT),
        "title": st("title", fontName=FB, fontSize=19 * scale, leading=21.5 * scale, textColor=PDEEP),
        "lede": st("lede", fontSize=8.9 * scale, leading=12 * scale, textColor=MUTED, alignment=TA_JUSTIFY),
        "h2": st("h2", fontName=FB, fontSize=10.4 * scale, leading=12.8 * scale, spaceAfter=2.2),
        "h3": st("h3", fontName=FB, fontSize=8.9 * scale, leading=11.6 * scale, textColor=PTEXT, spaceAfter=0.6),
        "body": st("body", alignment=TA_JUSTIFY),
        "box": st("box", fontSize=8.6 * scale, leading=11.6 * scale),
        "act": st("act", fontSize=8.9 * scale, leading=12 * scale, textColor=colors.white),
        "acth": st("acth", fontName=FB, fontSize=11 * scale, leading=13.5 * scale, textColor=colors.white),
        "subtitle": st("subtitle", fontName=FB, fontSize=11.4 * scale, leading=14 * scale, textColor=PTEXT),
        "foot": st("foot", fontSize=7.4 * scale, leading=9.8 * scale, textColor=MUTED, alignment=TA_LEFT),
    }


class Dot(Flowable):
    """The numbered purple disc of the five-demands brief."""
    def __init__(self, n, d=8.4 * mm, size=11):
        super().__init__()
        self.n, self.d, self.size = n, d, size

    def wrap(self, *_):
        return self.d, self.d

    def draw(self):
        c = self.canv
        c.setFillColor(PDEEP)
        c.circle(self.d / 2, self.d / 2, self.d / 2, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont(FB, self.size)
        c.drawCentredString(self.d / 2, self.d / 2 - self.size * 0.36, str(self.n))


def qr_code(size):
    w = qr.QrCodeWidget(APP_URL, barLevel="M")
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(w)
    return d


def flat(rows, widths, **extra):
    """A table with no padding of its own, the brief's way of laying blocks side by side."""
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 0)] + extra.get("style", [])
    return Table(rows, colWidths=widths, style=TableStyle(style))


def header(width, s, kicker, title, lede, logo_w=29 * mm, subtitle=None):
    cell = [Paragraph(kicker, s["kicker"]), Spacer(1, 1.6 * mm), Paragraph(title, s["title"])]
    if subtitle:
        cell += [Spacer(1, 1.4 * mm), Paragraph(subtitle, s["subtitle"])]
    cell += [Spacer(1, 1.6 * mm), Paragraph(lede, s["lede"])]
    logo = Image(str(LOGO), width=logo_w, height=logo_w * 176 / 269)
    return Table([[logo, cell]], colWidths=[logo_w + 8 * mm, width - logo_w - 8 * mm],
                 style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                   ("RIGHTPADDING", (0, 0), (0, 0), 8 * mm), ("RIGHTPADDING", (1, 0), (1, 0), 0),
                                   ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
                                   ("LINEBELOW", (0, 0), (-1, -1), 2.2, PDEEP)]))


def soft_box(label, text, width, s):
    """The brief's "PROGRESS LOOKS LIKE" box: soft purple, a purple bar on the left, a small-caps label."""
    return Table([[Paragraph(f'<font name="{FB}" size="{7.4 * s["box"].fontSize / 8.6:.1f}" color="#7222c2">{label}</font>  ' + text, s["box"])]],
                 colWidths=[width],
                 style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PSOFT), ("LINEBEFORE", (0, 0), (0, -1), 2.4, PURPLE),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 2.6 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2.6 * mm),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1.6 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8 * mm)]))


def numbered(n, title, parts, width, s, dot=8.4 * mm, dot_size=11):
    body_w = width - dot - 4.2 * mm
    cell = [Paragraph(title, s["h2"])]
    for p in parts:
        cell.append(p(body_w) if callable(p) else p)
    return flat([[Dot(n, dot, dot_size), cell]], [dot + 4.2 * mm, body_w])


def rule(width):
    return Table([[""]], colWidths=[width], rowHeights=[0.4],
                 style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), LINE)]))


def action_box(width, s, heading, lines, qr_size):
    text = [Paragraph(heading, s["acth"]), Spacer(1, 1.6 * mm)]
    for i, line in enumerate(lines):
        text += ([Spacer(1, 1.2 * mm)] if i else []) + [Paragraph(line, s["act"])]
    code = Table([[qr_code(qr_size)]], colWidths=[qr_size + 4 * mm],
                 style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                                   ("TOPPADDING", (0, 0), (-1, -1), 2 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm)]))
    inner = width - 10 * mm
    return Table([[flat([[text, code]], [inner - qr_size - 9 * mm, qr_size + 9 * mm],
                        style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT")])]],
                 colWidths=[width],
                 style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PDEEP),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm)]))


def document(out, title, subject, left_foot):
    doc = BaseDocTemplate(str(out), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                          topMargin=12 * mm, bottomMargin=17 * mm, title=title, author="DysNet", subject=subject)

    def furniture(canv, d):
        canv.saveState()
        y = 12 * mm
        canv.setStrokeColor(PDEEP)
        canv.setLineWidth(2.2)
        canv.line(d.leftMargin, y, d.leftMargin + d.width, y)
        canv.setFont(F, 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(d.leftMargin, y - 4.6 * mm, left_foot)
        right = "DysNet Ideell Förening · info@dysnet.org"
        if subject != "Poster":
            right += f" · page {canv.getPageNumber()}"
        canv.drawRightString(d.leftMargin + d.width, y - 4.6 * mm, right)
        canv.restoreState()

    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                                                             leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
                                       onPage=furniture)])
    return doc


# ── The waiting-room poster ─────────────────────────────────────────────────
# Read from a chair, by someone who has never heard of DysNet: large type, four short blocks,
# the code to scan. It says what the practice does not do, so nobody thinks the doctor collects.

def poster():
    out = ASSETS / "dysnet-registry-poster.pdf"
    doc = document(out, "DysNet registry: born with a limb difference? Help research find out why",
                   "Poster", "Read more, with sources: www.dysnet.org/registry/")
    width, s = doc.width, styles(1.24)
    s["title"].fontSize, s["title"].leading = 25, 28
    s["body"].alignment = TA_LEFT   # justified text gapes in a half-page column
    story = [Spacer(1, 1 * mm), header(
        width, s, "DysNet · 29 patients’ associations in 13 countries",
        "Born with a limb difference, or expecting a child who is?",
        "DysNet, the international network of associations of people born with a limb difference, is building "
        "a registry that belongs to the families it describes, not to a hospital or a company. A cause is "
        "found in only about one case in five, because cases are spread across hospitals and countries and "
        "never studied together. The registry brings them together, with each family’s consent.", logo_w=33 * mm,
        subtitle="Take part in the international registry run by the patients’ associations themselves."),
        Spacer(1, 4 * mm)]

    strip = Table([[Paragraph(f'<font name="{FB}">International · Run by patients’ associations · Free · '
                              'For yourself, or your child even before birth</font>', s["box"])]],
                  colWidths=[width],
                  style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PSOFT), ("LINEBEFORE", (0, 0), (0, -1), 2.4, PURPLE),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm), ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm)]))
    story += [strip, Spacer(1, 5 * mm)]

    blocks = [
        ("Why it matters",
         "When enough families describe their situation the same way, researchers can see where cases "
         "gather and look for a cause. In France, three groups of babies born without a hand or forearm "
         "(2007 to 2014) were investigated years later, from memory. Families who record what happened during "
         "the pregnancy give the next investigation what that one lacked."),
        ("Your data stays yours",
         "Your answers stay in your own free account at Health Data Safe, a Swiss non-profit foundation. "
         "DysNet reads only what you agree to share, and you can withdraw that permission at any time. "
         "Nothing is ever sold, and nothing goes to insurers or employers. You appear on the public map only "
         "if you choose to, as a blurred dot: never a name or an address."),
        ("What it gives you",
         "A copy of your record to bring to your doctor, with the international codes specialists use. A say "
         "in research: every study asks you first, and you answer one study at a time. And a view of where "
         "other families like yours live, whom your national association can help you meet."),
        ("What it gives everyone",
         "Each country gets its own figures, which most have never had. Associations can show governments "
         "how many people need care, prosthetics and research. Researchers get records that can be compared "
         "across borders, so the search for causes can start again."),
    ]
    col = (width - 8 * mm) / 2
    cells = [numbered(i, t, [Paragraph(b, s["body"])], col, s, dot=9.4 * mm, dot_size=12.5)
             for i, (t, b) in enumerate(blocks, 1)]
    grid = flat([[cells[0], "", cells[1]], [Spacer(1, 5 * mm), "", ""], [cells[2], "", cells[3]]],
                [col, 8 * mm, col])
    story += [grid, Spacer(1, 6 * mm)]

    story.append(action_box(width, s, "Scan to read more and take part", [
        f'<font name="{FB}" size="13">{APP_SHOWN}</font>',
        "About ten minutes, in English, French or Italian. The registry opens first with the associations in "
        "France and Italy, then country by country.",
        "No phone at hand? Ask your national association, or write to info@dysnet.org.",
    ], qr_size=40 * mm))
    story += [Spacer(1, 4 * mm), Paragraph(
        "DysNet (dysmelia network) is a non-profit association registered in Sweden since 2009. Health Data "
        "Safe, a Swiss non-profit foundation, is its technical partner. This practice does not receive your "
        "answers. Leave this sheet for the next person, or take a photo of the code.", s["foot"])]
    doc.build(story)
    return out


def steps(width, s):
    """The registry app's own guide, in its words: who is taking part, the sign-in, the answers."""
    items = [("Who is taking part?", "Yourself, or your child. A parent answers for a child, even before birth."),
             ("Sign in or create your account", "Your free Health Data Safe account, and your agreement to take part."),
             ("Answer the questions", "Three questions and two consents, all optional. They save as you go.")]
    col = (width - 2 * 3 * mm) / 3
    cells = []
    for n, (head, text) in enumerate(items, 1):
        cells.append(Table([[[Paragraph(f'<font name="{FB}" color="#7222c2">STEP {n}</font>', s["box"]),
                              Paragraph(f'<font name="{FB}">{head}</font>', s["box"]), Spacer(1, 0.8 * mm),
                              Paragraph(text, s["box"])]]], colWidths=[col],
                           style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PSOFT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                             ("LINEABOVE", (0, 0), (-1, 0), 2.4, PURPLE),
                                             ("LEFTPADDING", (0, 0), (-1, -1), 2.6 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2.4 * mm),
                                             ("TOPPADDING", (0, 0), (-1, -1), 1.8 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm)])))
    return flat([[cells[0], "", cells[1], "", cells[2]]], [col, 3 * mm, col, 3 * mm, col])


def who_sees(width, s):
    """Who sees what, one row per party, in the order a family worries about them."""
    rows = [
        ("You", "Everything you entered, in your own account. You can change it, download a copy, or delete it all."),
        ("DysNet’s registry team", "Your answers to the three questions, including the exact place of the pregnancy, "
                                   "to count and to look for clusters. Your email only if you agreed to be contacted."),
        ("Anyone, on the public map", "Only if you agree: a dot blurred over the area you chose, with the words you chose. "
                                      "Never a name, an address or the exact place."),
        ("A researcher", "Nothing, unless you say yes to their study. Then only the data that study names, for that study."),
        ("Your national association", "Counts for its country, not your record."),
        ("Your doctor", "Only what you decide to show, for example the copy you download."),
        ("Health Data Safe", "It keeps your account and runs the servers. It gives nobody access to your data without "
                             "your consent."),
    ]
    head = [Paragraph(f'<font name="{FB}" color="#ffffff">Who</font>', s["box"]),
            Paragraph(f'<font name="{FB}" color="#ffffff">What they can see</font>', s["box"])]
    data = [head] + [[Paragraph(f'<font name="{FB}">{w}</font>', s["box"]), Paragraph(t, s["box"])] for w, t in rows]
    style = [("BACKGROUND", (0, 0), (-1, 0), PDEEP), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 2.4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2.4 * mm),
             ("TOPPADDING", (0, 0), (-1, -1), 1.4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 * mm),
             ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE)]
    style += [("BACKGROUND", (0, r), (-1, r), PSOFT) for r in range(2, len(data), 2)]
    return Table(data, colWidths=[38 * mm, width - 38 * mm], style=TableStyle(style))


# ── The members' brief ──────────────────────────────────────────────────────
# Three pages an association sends to its families: what the registry is for, what taking part
# means, how the data is protected, what it gives the community and each person, and what we do
# not claim. Every answer here is one the registry app's own questions and answers also gives.

def brief():
    out = ASSETS / "dysnet-registry-explained.pdf"
    doc = document(out, "The DysNet registry, explained", "Members' brief",
                   "Questions and answers, with sources: www.dysnet.org/registry/")
    width, s = doc.width, styles(1.06)
    P = lambda text, st="body": Paragraph(text, s[st])
    gap = lambda h=1.8: Spacer(1, h * mm)

    story = [Spacer(1, 1 * mm), header(
        width, s, "For the families of DysNet’s member associations · The registry",
        "The DysNet registry, explained",
        "On 26 August 2026 DysNet’s general assembly decided to build a registry of people born with a limb "
        "difference, with Health Data Safe as its technical partner. This brief says what the registry is for, "
        "what taking part means, how your data is protected, and what it gives the community and you. It is "
        "being tested now with the associations in France (Assedea) and Italy (Raggiungere), and opens to other "
        "countries after them."), Spacer(1, 4.5 * mm)]

    sections = [
        ("What the registry is for", [
            P("No registry, national or European, is dedicated to limb differences. Cases are recorded, when "
              "they are recorded at all, in different hospitals and countries, in systems that cannot talk to each "
              "other. In large birth-defect studies a cause is found in about one case in five, and usually none "
              "for a single limb. That figure moves only when enough cases are described well enough to study."),
            gap(),
            P("Between 2007 and 2014, three clusters of babies born without a hand or forearm came to light in "
              "France, in Loire-Atlantique, Ain and Morbihan. The investigations found no common exposure, and they "
              "met a limit no investigation can repair afterwards: families were questioned years after the birth, "
              "from memory. Families who record their situation themselves, from the pregnancy onwards, give the "
              "next investigation the data the last one lacked."),
            gap(2.2),
            lambda w: soft_box("THREE OBJECTIVES, IN THIS ORDER",
                               "Find the next clusters, by bringing the cases families declare together across "
                               "countries. Keep existing registries alive, by offering the population registries "
                               "that record our conditions a place to preserve their data if their funding fails. "
                               "Make registries talk to each other, so that a record moves without being retyped "
                               "and two countries’ figures can be compared.", w, s),
        ]),
        ("What taking part means", [
            P("Anyone born with a congenital limb difference can take part, from any country: an adult for "
              "themselves, or a parent or guardian for their child, even before birth. The registry works in "
              "English, French and Italian for now, and it takes about ten minutes."),
            gap(),
            gap(2.2),
            lambda w: steps(w, s),
            gap(2.2),
            P("You create a free Health Data Safe account (a parent also creates one for the child, from their "
              "own) and give one agreement to take part. Then come three questions: the date of birth, or the expected "
              "date; the limb difference, which you can search with the words families use or describe in your "
              "own words; and where the mother lived at the start of the pregnancy. Two consents follow: to "
              "appear on the public map, and to be contacted about research. Every question and every consent is "
              "optional, and you can change any answer later."),
        ]),
        ("Your data, and who can read it", [
            P("DysNet does not store your answers. They stay in your own account at Health Data Safe, a Swiss "
              "non-profit foundation under federal supervision, on servers in Switzerland (or in the United "
              "States, if you choose that region when you create the account). Data is encrypted when it travels "
              "and where it is stored. DysNet holds no patient database: it holds a permission to read what you "
              "agreed to share, and nothing else."),
            gap(),
            P("Each consent is a separate permission. Your account lists every service that can read your data "
              "and records each time it does. You can withdraw any permission in one click: DysNet then stops "
              "reading, and what is in your account stays yours, to keep or to delete. Neither DysNet nor Health "
              "Data Safe sells health data, and nobody can buy the registry’s data or receive it in bulk."),
            gap(),
            P("The place of the pregnancy is read by DysNet only to look for clusters, and it is never published. "
              "If you agree to the map, it shows a dot blurred over an area you choose (1 to 5 km across, or "
              "wider), labelled with the words you choose: the condition, only which limbs, or only that you live "
              "with a limb difference. Your dot can be the only one in its area, so choose with that in mind. You "
              "can leave the map at any time, and your dot disappears at the next update."),
            gap(),
            P("A child’s answers go into the child’s own account from the start, not the parent’s. You hold it "
              "for them until they are 18. When they take it over, they review every consent you gave and keep "
              "only the ones they choose; your access then ends, and nothing has to move."),
            gap(2.6),
            lambda w: who_sees(w, s),
            gap(2.6),
            lambda w: soft_box("OPEN ABOUT ITS LIMITS",
                               "Health Data Safe publishes, requirement by requirement, how it meets the GDPR, "
                               "Swiss data protection law and the US health privacy rule (HIPAA), and the gaps it "
                               "still has to close, at compliance.datasafe.dev. It is a self-assessment: Health "
                               "Data Safe holds no external certification yet, and says so.", w, s),
        ]),
        ("What it gives the community", [
            P("Most member associations have never had figures for their own country. The registry gives them: "
              "how many people, where, with which condition. With a figure and its source, an association can ask "
              "a ministry for a care pathway or for prosthetics to be reimbursed, and be heard. These are the "
              "demands DysNet carries at EURORDIS, the European Disability Forum and ERN BOND."),
            gap(),
            P("Research on causes needs records that compare across borders. The registry describes every "
              "condition with the codes doctors and registries use (ORPHAcode, ICD-10, ICD-11), so that a French "
              "record and an Italian one mean the same thing. Once live, it will be listed in Orphanet’s European "
              "directory of rare-disease registries, where researchers look for data."),
            gap(),
            P("The member associations also decide, together with the DysNet board, which studies may be put to "
              "families at all. Research reaches the community on the community’s terms."),
        ]),
        ("What it gives you", [
            P("With your doctor", "h3"),
            P("Your condition is recorded with the international codes specialists use, and you can download a "
              "copy of everything you entered to bring to an appointment. On dysnet.org, the guide to the "
              "conditions and the register of care centres help you find a specialist and prepare your questions."),
            gap(1.6),
            P("In research", "h3"),
            P("A researcher proposes a study, and DysNet’s member associations and board decide whether it may "
              "be put to families. If it is, you see the request in the registry, and by email if you agreed to be "
              "contacted: who asks, what for, and which data. You answer study by study. A yes opens that study’s "
              "data only, and you can withdraw it; a no changes nothing about your place in the registry."),
            gap(1.6),
            P("With other families", "h3"),
            P("The map shows where other people with the same condition live, area by area and never by name, "
              "so you can see you are not alone and where the others are. The registry does not put families in "
              "touch with each other; your national association does, and it is the place to ask."),
        ]),
    ]

    # page 2 ends on what the registry is not, next to what Health Data Safe says of its own limits
    careful = soft_box("WHAT WE ARE CAREFUL NOT TO CLAIM",
                       "The registry describes the families who choose to take part; it does not count every case "
                       "in a country. It has no medical board yet: writing a research protocol is a scientific act, "
                       "and an association will not pretend to perform it. And what families declare about "
                       "themselves is precious, but it is not clinician-verified data; the two will never be "
                       "confused.", width, s)
    for i, (title, parts) in enumerate(sections, 1):
        story.append(KeepTogether(numbered(i, title, parts, width, s)))
        if i == 3:
            story += [gap(3), careful, PageBreak()]
        else:
            story += [PageBreak()] if i == 2 else [gap(3), rule(width), gap(3)]

    story.append(KeepTogether([
        P("DysNet, the international dysmelia network, a non-profit association registered in Sweden since 2009, "
          "runs the registry, and Health Data Safe contributes its infrastructure in kind. Taking part is free. "
          "The registry is looking for its first funders, and it will never be funded by selling data."),
        gap(4),
        action_box(width, s, "Take part, or ask a question", [
            f'Scan the code or open <font name="{FB}">{APP_SHOWN}</font>. The registry opens first with the '
            "associations in France and Italy; your association will tell you when it opens in your country.",
            "The questions and answers, and the full reasoning with its sources, are at www.dysnet.org/registry/. "
            "Write to info@dysnet.org.",
        ], qr_size=30 * mm),
    ]))
    doc.build(story)
    return out


if __name__ == "__main__":
    from pypdf import PdfReader
    for made in (poster(), brief()):
        print(f"{made.relative_to(ROOT)}: {len(PdfReader(str(made)).pages)} page(s), {made.stat().st_size // 1024} kB")
