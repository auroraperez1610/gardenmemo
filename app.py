from flask import Flask, render_template, request, jsonify, send_file
import json, os, base64, io, uuid
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    PageBreak, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing, Circle
from PIL import Image as PILImage

import os
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

DATA_FILE = 'catalog.json'

VERDE_OSC  = colors.HexColor('#2D5016')
VERDE_MED  = colors.HexColor('#4A7C28')
VERDE_CLAR = colors.HexColor('#7DB544')
BEIGE      = colors.HexColor('#F5F0E8')
GRIS_MED   = colors.HexColor('#666666')
GRIS_OSC   = colors.HexColor('#333333')
BLANCO     = colors.white
PAGE_W, PAGE_H = A4

def load_catalog():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_catalog(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/catalog', methods=['GET'])
def get_catalog():
    return jsonify(load_catalog())

@app.route('/api/catalog', methods=['POST'])
def add_species():
    data = request.json
    catalog = load_catalog()
    species = {
        'id':      str(uuid.uuid4())[:8],
        'name':    data.get('name', ''),
        'notes':   data.get('notes', ''),
        'icon':    data.get('icon', None),
        'photo':   data.get('photo', None),
        'created': datetime.now().isoformat()
    }
    catalog.append(species)
    save_catalog(catalog)
    return jsonify({'ok': True, 'species': species})

@app.route('/api/catalog/<sid>', methods=['DELETE'])
def delete_species(sid):
    catalog = [s for s in load_catalog() if s['id'] != sid]
    save_catalog(catalog)
    return jsonify({'ok': True})

@app.route('/api/catalog/<sid>', methods=['PUT'])
def update_species(sid):
    data = request.json
    catalog = load_catalog()
    for s in catalog:
        if s['id'] == sid:
            s.update({k: data[k] for k in data if k != 'id'})
    save_catalog(catalog)
    return jsonify({'ok': True})

@app.route('/api/generate', methods=['POST'])
def generate_pdf():
    data         = request.json
    project_name = data.get('project_name', 'Proyecto')
    address      = data.get('address', '')
    plan_b64     = data.get('plan_image', None)
    species_list = data.get('species', [])
    buf = io.BytesIO()
    _build_pdf(buf, project_name, address, plan_b64, species_list)
    buf.seek(0)
    filename = f"Memoria_{project_name.replace(' ','_')}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)

# ── PDF helpers ────────────────────────────────────────────────────────
def b64_to_img(b64str):
    if not b64str:
        return None
    header, data = b64str.split(',', 1) if ',' in b64str else ('', b64str)
    raw  = base64.b64decode(data)
    path = f'/tmp/{uuid.uuid4().hex}.jpg'
    with open(path, 'wb') as f:
        f.write(raw)
    try:
        pil = PILImage.open(path)
        if pil.mode in ('RGBA', 'LA', 'P'):
            bg = PILImage.new('RGBA', pil.size, (255,255,255,255))
            src = pil.convert('RGBA')
            bg.paste(src, mask=src.split()[3])
            pil = bg.convert('RGB')
        else:
            pil = pil.convert('RGB')
        out = path.replace('.jpg', '_n.jpg')
        pil.save(out, 'JPEG', quality=90)
        return out
    except:
        return path

def rli(b64str, max_w, max_h):
    path = b64_to_img(b64str)
    if not path or not os.path.exists(path):
        return None
    pil = PILImage.open(path)
    w, h = pil.size
    ratio = min(max_w / w, max_h / h)
    return RLImage(path, width=w*ratio, height=h*ratio)

def dot_drawing(w, h):
    d = Drawing(w, h)
    r = min(w, h) * 0.38
    c = Circle(w/2, h/2, r)
    c.fillColor  = VERDE_CLAR
    c.strokeColor = VERDE_MED
    c.strokeWidth = 1.5
    d.add(c)
    return d

def header_footer(canvas, doc, title, subtitle):
    canvas.saveState()
    # Cabecera verde
    canvas.setFillColor(VERDE_OSC)
    canvas.rect(0, PAGE_H-1.5*cm, PAGE_W, 1.5*cm, fill=1, stroke=0)
    canvas.setFillColor(BLANCO)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.drawString(1.5*cm, PAGE_H-1.0*cm, title)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(PAGE_W-1.5*cm, PAGE_H-1.0*cm, subtitle)
    canvas.setStrokeColor(VERDE_CLAR)
    canvas.setLineWidth(1.5)
    canvas.line(0, PAGE_H-1.52*cm, PAGE_W, PAGE_H-1.52*cm)
    # Pie beige
    canvas.setFillColor(BEIGE)
    canvas.rect(0, 0, PAGE_W, 1.0*cm, fill=1, stroke=0)
    canvas.setFillColor(GRIS_MED)
    canvas.setFont('Helvetica', 7)
    canvas.drawCentredString(PAGE_W/2, 0.38*cm, f'Página {doc.page}')
    canvas.restoreState()

def _build_pdf(buf, project_name, address, plan_b64, species_list):
    hdr_title = f'MEMORIA DE PLANTAS  ·  {project_name.upper()}'
    hdr_sub   = address or ''

    frame = Frame(1.5*cm, 1.2*cm, PAGE_W-3*cm, PAGE_H-3.0*cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    pt = PageTemplate(id='p', frames=[frame],
                      onPage=lambda c, d: header_footer(c, d, hdr_title, hdr_sub))
    doc = BaseDocTemplate(buf, pagesize=A4, pageTemplates=[pt])

    # Estilos
    tit_st  = ParagraphStyle('tit', fontSize=22, leading=26, textColor=VERDE_OSC,
                              fontName='Helvetica-Bold', spaceAfter=2)
    sub_st  = ParagraphStyle('sub', fontSize=9, leading=12, textColor=GRIS_MED,
                              fontName='Helvetica', spaceAfter=6)
    sec_st  = ParagraphStyle('sec', fontSize=9, fontName='Helvetica-Bold',
                              textColor=VERDE_OSC, spaceAfter=5)
    ley_st  = ParagraphStyle('ley', fontSize=6.5, leading=8, textColor=BLANCO,
                              fontName='Helvetica-Bold', alignment=TA_CENTER)
    cnom_st = ParagraphStyle('cn', fontSize=9, leading=12, textColor=BLANCO,
                              fontName='Helvetica-Bold', alignment=TA_CENTER)
    cnot_st = ParagraphStyle('cno', fontSize=7.5, leading=10, textColor=GRIS_MED,
                              fontName='Helvetica', alignment=TA_CENTER)

    story = []

    # ══════════════════════════════════════════════════════════════════
    # PÁG 1 — Plano + Leyenda de iconos
    # ══════════════════════════════════════════════════════════════════
    story.append(Paragraph(project_name.upper(), tit_st))
    story.append(Paragraph(
        address if address else 'Memoria de plantas y distribución de especies', sub_st))
    story.append(HRFlowable(width='100%', thickness=2, color=VERDE_CLAR, spaceAfter=6))

    # Plano
    if plan_b64:
        plano = rli(plan_b64, PAGE_W-3*cm, 13*cm)
        if plano:
            story.append(plano)
    story.append(Spacer(1, 10))

    # Leyenda horizontal: icono + nombre
    if species_list:
        story.append(Paragraph('LEYENDA DE ESPECIES', sec_st))
        N  = len(species_list)
        IW = (PAGE_W-3*cm) / N
        IH = 2.5*cm

        icon_cells, name_cells = [], []
        for sp in species_list:
            img = rli(sp.get('icon'), IW-8, IH-8) if sp.get('icon') else None
            if img:
                cell = Table([[img]], colWidths=[IW])
            else:
                cell = Table([[dot_drawing(IW*0.7, IH*0.7)]], colWidths=[IW])
            cell.setStyle(TableStyle([
                ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                ('TOPPADDING',    (0,0),(-1,-1), 5),
                ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ('LEFTPADDING',   (0,0),(-1,-1), 3),
                ('RIGHTPADDING',  (0,0),(-1,-1), 3),
            ]))
            icon_cells.append(cell)
            name_cells.append(Paragraph(f'<b>{sp["name"]}</b>', ley_st))

        icon_row = Table([icon_cells], colWidths=[IW]*N)
        icon_row.setStyle(TableStyle([
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ('BACKGROUND',    (0,0),(-1,-1), BEIGE),
            ('BOX',           (0,0),(-1,-1), 1, colors.HexColor('#CCCCCC')),
            ('INNERGRID',     (0,0),(-1,-1), 0.5, colors.HexColor('#DDDDDD')),
            ('TOPPADDING',    (0,0),(-1,-1), 0),
            ('BOTTOMPADDING', (0,0),(-1,-1), 0),
            ('LEFTPADDING',   (0,0),(-1,-1), 0),
            ('RIGHTPADDING',  (0,0),(-1,-1), 0),
        ]))
        name_row = Table([name_cells], colWidths=[IW]*N)
        name_row.setStyle(TableStyle([
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ('BACKGROUND',    (0,0),(-1,-1), VERDE_OSC),
            ('INNERGRID',     (0,0),(-1,-1), 0.5, colors.HexColor('#3a6b20')),
            ('TOPPADDING',    (0,0),(-1,-1), 3),
            ('BOTTOMPADDING', (0,0),(-1,-1), 3),
            ('LEFTPADDING',   (0,0),(-1,-1), 2),
            ('RIGHTPADDING',  (0,0),(-1,-1), 2),
        ]))
        story.append(icon_row)
        story.append(name_row)

    # ══════════════════════════════════════════════════════════════════
    # PÁG 2+ — Fichas de especies (3 columnas)
    # ══════════════════════════════════════════════════════════════════
    if species_list:
        story.append(PageBreak())
        story.append(Paragraph('FICHAS DE ESPECIES', tit_st))
        story.append(HRFlowable(width='100%', thickness=2, color=VERDE_CLAR, spaceAfter=10))

        COLS  = 3
        GAP   = 0.4*cm
        CW    = (PAGE_W-3*cm - GAP*(COLS-1)) / COLS
        IMG_H = 5.5*cm  # icono
        PHO_H = 4.5*cm  # foto real

        def make_card(sp):
            # ── Cabecera nombre ──
            hdr = Table([[Paragraph(f'<b>{sp["name"]}</b>', cnom_st)]], colWidths=[CW])
            hdr.setStyle(TableStyle([
                ('BACKGROUND',   (0,0),(-1,-1), VERDE_OSC),
                ('TOPPADDING',   (0,0),(-1,-1), 6),
                ('BOTTOMPADDING',(0,0),(-1,-1), 6),
                ('LEFTPADDING',  (0,0),(-1,-1), 5),
                ('RIGHTPADDING', (0,0),(-1,-1), 5),
            ]))

            # ── Icono del plano ──
            ico_img = rli(sp.get('icon'), CW-0.4*cm, IMG_H) if sp.get('icon') else None
            if ico_img:
                ico_cell = Table([[ico_img]], colWidths=[CW])
            else:
                ico_cell = Table([[dot_drawing(CW*0.8, IMG_H*0.8)]], colWidths=[CW])
            ico_cell.setStyle(TableStyle([
                ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                ('BACKGROUND',    (0,0),(-1,-1), BEIGE),
                ('TOPPADDING',    (0,0),(-1,-1), 6),
                ('BOTTOMPADDING', (0,0),(-1,-1), 6),
            ]))

            # Etiqueta "Icono en plano"
            ico_label = Table([[Paragraph('Icono en plano', ParagraphStyle(
                'il', fontSize=7, fontName='Helvetica', textColor=GRIS_MED,
                alignment=TA_CENTER))]], colWidths=[CW])
            ico_label.setStyle(TableStyle([
                ('BACKGROUND',   (0,0),(-1,-1), colors.HexColor('#E8E4DC')),
                ('TOPPADDING',   (0,0),(-1,-1), 2),
                ('BOTTOMPADDING',(0,0),(-1,-1), 2),
            ]))

            # ── Foto real ──
            pho_img = rli(sp.get('photo'), CW-0.4*cm, PHO_H) if sp.get('photo') else None
            if pho_img:
                pho_cell = Table([[pho_img]], colWidths=[CW])
                pho_cell.setStyle(TableStyle([
                    ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
                    ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                    ('BACKGROUND',    (0,0),(-1,-1), colors.HexColor('#F8F8F8')),
                    ('TOPPADDING',    (0,0),(-1,-1), 5),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ]))
                pho_label = Table([[Paragraph('Foto de referencia', ParagraphStyle(
                    'pl', fontSize=7, fontName='Helvetica', textColor=GRIS_MED,
                    alignment=TA_CENTER))]], colWidths=[CW])
                pho_label.setStyle(TableStyle([
                    ('BACKGROUND',   (0,0),(-1,-1), colors.HexColor('#F0F0F0')),
                    ('TOPPADDING',   (0,0),(-1,-1), 2),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 2),
                ]))
            else:
                pho_cell  = None
                pho_label = None

            # ── Notas ──
            notes_txt = sp.get('notes', '')
            if notes_txt:
                notes_cell = Table([[Paragraph(notes_txt, cnot_st)]], colWidths=[CW])
                notes_cell.setStyle(TableStyle([
                    ('BACKGROUND',   (0,0),(-1,-1), BEIGE),
                    ('TOPPADDING',   (0,0),(-1,-1), 4),
                    ('BOTTOMPADDING',(0,0),(-1,-1), 4),
                    ('LEFTPADDING',  (0,0),(-1,-1), 5),
                    ('RIGHTPADDING', (0,0),(-1,-1), 5),
                ]))
            else:
                notes_cell = None

            # ── Ensamblar ficha ──
            rows = [[hdr], [ico_cell], [ico_label]]
            if pho_cell:
                rows += [[pho_cell], [pho_label]]
            if notes_cell:
                rows.append([notes_cell])

            card = Table(rows, colWidths=[CW])
            card.setStyle(TableStyle([
                ('BOX',          (0,0),(-1,-1), 1, colors.HexColor('#BBBBBB')),
                ('LEFTPADDING',  (0,0),(-1,-1), 0),
                ('RIGHTPADDING', (0,0),(-1,-1), 0),
                ('TOPPADDING',   (0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 0),
            ]))
            return card

        for i in range(0, len(species_list), COLS):
            batch = species_list[i:i+COLS]
            cards = [make_card(s) for s in batch]
            while len(cards) < COLS:
                cards.append(Spacer(CW, 1))
            row_data, widths = [], []
            for j, c in enumerate(cards):
                row_data.append(c); widths.append(CW)
                if j < COLS-1:
                    row_data.append(Spacer(GAP, 1)); widths.append(GAP)
            row = Table([row_data], colWidths=widths)
            row.setStyle(TableStyle([
                ('VALIGN',       (0,0),(-1,-1), 'TOP'),
                ('LEFTPADDING',  (0,0),(-1,-1), 0),
                ('RIGHTPADDING', (0,0),(-1,-1), 0),
                ('TOPPADDING',   (0,0),(-1,-1), 0),
                ('BOTTOMPADDING',(0,0),(-1,-1), 10),
            ]))
            story.append(row)

    doc.build(story)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
