from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import json, os, base64, io, uuid, hashlib
from datetime import datetime
from functools import wraps
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, Image as RLImage,
    PageBreak, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, Circle
from PIL import Image as PILImage

# ── Supabase ───────────────────────────────────────────────────────────
try:
    from supabase import create_client
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    db = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None
except:
    db = None

import os as _os
app = Flask(__name__, template_folder=_os.path.join(_os.path.dirname(__file__), 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# ── Credenciales ───────────────────────────────────────────────────────
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'bolaga2024')
TEAM_PASS  = os.environ.get('TEAM_PASS',  'equipo2024')

# ── Colores PDF ────────────────────────────────────────────────────────
VERDE_OSC  = colors.HexColor('#2D5016')
VERDE_MED  = colors.HexColor('#4A7C28')
VERDE_CLAR = colors.HexColor('#7DB544')
BEIGE      = colors.HexColor('#F5F0E8')
GRIS_MED   = colors.HexColor('#666666')
BLANCO     = colors.white
PAGE_W, PAGE_H = A4

LOGO_B64 = os.environ.get('LOGO_B64', '')

# ── Auth helpers ───────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': 'Solo el administrador puede realizar esta acción'}), 403
        return f(*args, **kwargs)
    return decorated

# ── DB helpers ─────────────────────────────────────────────────────────
def db_get_catalog():
    if db:
        r = db.table('catalog').select('*').order('created_at').execute()
        return r.data or []
    # Fallback local
    if os.path.exists('catalog.json'):
        with open('catalog.json') as f:
            return json.load(f)
    return []

def db_save_species(sp):
    if db:
        db.table('catalog').insert(sp).execute()
    else:
        cat = db_get_catalog()
        cat.append(sp)
        with open('catalog.json','w') as f:
            json.dump(cat, f, ensure_ascii=False, indent=2)

def db_update_species(sid, data):
    if db:
        db.table('catalog').update(data).eq('id', sid).execute()
    else:
        cat = db_get_catalog()
        for s in cat:
            if s['id'] == sid:
                s.update(data)
        with open('catalog.json','w') as f:
            json.dump(cat, f, ensure_ascii=False, indent=2)

def db_delete_species(sid):
    if db:
        db.table('catalog').delete().eq('id', sid).execute()
    else:
        cat = [s for s in db_get_catalog() if s['id'] != sid]
        with open('catalog.json','w') as f:
            json.dump(cat, f, ensure_ascii=False, indent=2)

def db_get_projects():
    if db:
        r = db.table('projects').select('id,name,address,created_at,updated_at').order('updated_at', desc=True).execute()
        return r.data or []
    if os.path.exists('projects.json'):
        with open('projects.json') as f:
            return json.load(f)
    return []

def db_get_project(pid):
    if db:
        r = db.table('projects').select('*').eq('id', pid).execute()
        return r.data[0] if r.data else None
    projects = db_get_projects()
    return next((p for p in projects if p['id'] == pid), None)

def db_save_project(proj):
    if db:
        db.table('projects').insert(proj).execute()
    else:
        projects = db_get_projects()
        projects.append(proj)
        with open('projects.json','w') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)

def db_update_project(pid, data):
    if db:
        db.table('projects').update(data).eq('id', pid).execute()
    else:
        projects = db_get_projects()
        for p in projects:
            if p['id'] == pid:
                p.update(data)
        with open('projects.json','w') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)

def db_delete_project(pid):
    if db:
        db.table('projects').delete().eq('id', pid).execute()
    else:
        projects = [p for p in db_get_projects() if p['id'] != pid]
        with open('projects.json','w') as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)

def db_save_pdf(pid, pdf_b64):
    if db:
        db.table('projects').update({'pdf': pdf_b64, 'updated_at': datetime.now().isoformat()}).eq('id', pid).execute()
    else:
        db_update_project(pid, {'pdf': pdf_b64, 'updated_at': datetime.now().isoformat()})

# ── Rutas auth ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    if not session.get('user'):
        return render_template('login.html')
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = data.get('user', '').strip()
    pwd  = data.get('password', '').strip()
    if user == ADMIN_USER and pwd == ADMIN_PASS:
        session['user'] = user
        session['role'] = 'admin'
        return jsonify({'ok': True, 'role': 'admin'})
    elif pwd == TEAM_PASS:
        session['user'] = user or 'equipo'
        session['role'] = 'team'
        return jsonify({'ok': True, 'role': 'team'})
    return jsonify({'ok': False, 'error': 'Credenciales incorrectas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def me():
    if session.get('user'):
        return jsonify({'user': session['user'], 'role': session['role']})
    return jsonify({'user': None, 'role': None})

# ── Catálogo ───────────────────────────────────────────────────────────
@app.route('/api/catalog', methods=['GET'])
@login_required
def get_catalog():
    return jsonify(db_get_catalog())

@app.route('/api/catalog', methods=['POST'])
@login_required
@admin_required
def add_species():
    data = request.json
    sp = {
        'id':         str(uuid.uuid4())[:8],
        'name':       data.get('name', ''),
        'notes':      data.get('notes', ''),
        'icon':       data.get('icon', None),
        'photo':      data.get('photo', None),
        'created_at': datetime.now().isoformat()
    }
    db_save_species(sp)
    return jsonify({'ok': True, 'species': sp})

@app.route('/api/catalog/<sid>', methods=['PUT'])
@login_required
@admin_required
def update_species(sid):
    data = request.json
    allowed = {k: data[k] for k in ('name','notes','icon','photo') if k in data}
    db_update_species(sid, allowed)
    return jsonify({'ok': True})

@app.route('/api/catalog/<sid>', methods=['DELETE'])
@login_required
@admin_required
def delete_species(sid):
    db_delete_species(sid)
    return jsonify({'ok': True})

# ── Proyectos ──────────────────────────────────────────────────────────
@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects():
    return jsonify(db_get_projects())

@app.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    data = request.json
    proj = {
        'id':         str(uuid.uuid4())[:8],
        'name':       data.get('name', ''),
        'address':    data.get('address', ''),
        'plan':       data.get('plan', None),
        'species':    data.get('species', []),
        'pdf':        None,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    db_save_project(proj)
    return jsonify({'ok': True, 'project': proj})

@app.route('/api/projects/<pid>', methods=['GET'])
@login_required
def get_project(pid):
    proj = db_get_project(pid)
    if not proj:
        return jsonify({'error': 'No encontrado'}), 404
    return jsonify(proj)

@app.route('/api/projects/<pid>', methods=['PUT'])
@login_required
def update_project(pid):
    data = request.json
    allowed = {k: data[k] for k in ('name','address','plan','species') if k in data}
    allowed['updated_at'] = datetime.now().isoformat()
    db_update_project(pid, allowed)
    return jsonify({'ok': True})

@app.route('/api/projects/<pid>', methods=['DELETE'])
@login_required
@admin_required
def delete_project(pid):
    db_delete_project(pid)
    return jsonify({'ok': True})

# ── Generar PDF ────────────────────────────────────────────────────────
@app.route('/api/generate/<pid>', methods=['POST'])
@login_required
def generate_pdf(pid):
    proj = db_get_project(pid)
    if not proj:
        return jsonify({'error': 'Proyecto no encontrado'}), 404

    buf = io.BytesIO()
    _build_pdf(buf, proj['name'], proj.get('address',''),
               proj.get('plan'), proj.get('species', []))
    buf.seek(0)
    pdf_bytes = buf.read()

    # Guardar PDF en base64 en la BD
    pdf_b64 = base64.b64encode(pdf_bytes).decode()
    db_save_pdf(pid, pdf_b64)

    filename = f"Memoria_{proj['name'].replace(' ','_')}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                     as_attachment=True, download_name=filename)

@app.route('/api/projects/<pid>/pdf', methods=['GET'])
@login_required
def download_pdf(pid):
    proj = db_get_project(pid)
    if not proj or not proj.get('pdf'):
        return jsonify({'error': 'PDF no disponible'}), 404
    pdf_bytes = base64.b64decode(proj['pdf'])
    filename = f"Memoria_{proj['name'].replace(' ','_')}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                     as_attachment=True, download_name=filename)

# ── PDF engine ─────────────────────────────────────────────────────────
def b64_to_img(b64str):
    if not b64str: return None
    _, data = b64str.split(',', 1) if ',' in b64str else ('', b64str)
    raw  = base64.b64decode(data)
    path = f'/tmp/{uuid.uuid4().hex}.jpg'
    with open(path, 'wb') as f: f.write(raw)
    try:
        pil = PILImage.open(path)
        if pil.mode in ('RGBA','LA','P'):
            bg = PILImage.new('RGBA', pil.size, (255,255,255,255))
            src = pil.convert('RGBA')
            bg.paste(src, mask=src.split()[3])
            pil = bg.convert('RGB')
        else:
            pil = pil.convert('RGB')
        out = path.replace('.jpg','_n.jpg')
        pil.save(out, 'JPEG', quality=90)
        return out
    except: return path

def rli(b64str, max_w, max_h):
    path = b64_to_img(b64str)
    if not path or not os.path.exists(path): return None
    pil = PILImage.open(path)
    w, h = pil.size
    ratio = min(max_w/w, max_h/h)
    return RLImage(path, width=w*ratio, height=h*ratio)

def dot_drawing(w, h):
    d = Drawing(w, h)
    r = min(w,h)*0.38
    c = Circle(w/2, h/2, r)
    c.fillColor=VERDE_CLAR; c.strokeColor=VERDE_MED; c.strokeWidth=1.5
    d.add(c)
    return d

def get_logo_path():
    logo_b64 = LOGO_B64 or os.environ.get('LOGO_B64','')
    if not logo_b64: return None
    path = '/tmp/logo_bolaga.png'
    if not os.path.exists(path):
        with open(path,'wb') as f:
            f.write(base64.b64decode(logo_b64))
    return path

def header_footer(canvas, doc, project_name, address):
    canvas.saveState()
    canvas.setFillColor(VERDE_OSC)
    canvas.rect(0, PAGE_H-1.8*cm, PAGE_W, 1.8*cm, fill=1, stroke=0)
    canvas.setFillColor(BLANCO)
    canvas.setFont('Helvetica-Bold', 11)
    canvas.drawString(1.5*cm, PAGE_H-1.05*cm, project_name.upper())
    if address:
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#C8E6A0'))
        canvas.drawString(1.5*cm, PAGE_H-1.55*cm, address)
    try:
        lp = get_logo_path()
        if lp:
            pil = PILImage.open(lp)
            lw,lh = pil.size
            ratio = min(4.0*cm/lw, 1.3*cm/lh)
            dw,dh = lw*ratio, lh*ratio
            canvas.drawImage(lp, PAGE_W-1.5*cm-dw,
                PAGE_H-1.8*cm+(1.8*cm-dh)/2,
                width=dw, height=dh, preserveAspectRatio=True, mask='auto')
    except: pass
    canvas.setStrokeColor(VERDE_CLAR)
    canvas.setLineWidth(1.5)
    canvas.line(0, PAGE_H-1.82*cm, PAGE_W, PAGE_H-1.82*cm)
    canvas.setFillColor(BEIGE)
    canvas.rect(0, 0, PAGE_W, 1.0*cm, fill=1, stroke=0)
    canvas.setFillColor(GRIS_MED)
    canvas.setFont('Helvetica', 7)
    canvas.drawCentredString(PAGE_W/2, 0.38*cm, f'Página {doc.page}')
    canvas.restoreState()

def _build_pdf(buf, project_name, address, plan_b64, species_list):
    frame = Frame(1.5*cm, 1.2*cm, PAGE_W-3*cm, PAGE_H-3.2*cm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    pt = PageTemplate(id='p', frames=[frame],
                      onPage=lambda c,d: header_footer(c,d,project_name,address))
    doc = BaseDocTemplate(buf, pagesize=A4, pageTemplates=[pt])

    dist_st = ParagraphStyle('dist',fontSize=11,fontName='Helvetica-Bold',textColor=VERDE_OSC,spaceAfter=6,spaceBefore=4)
    sec_st  = ParagraphStyle('sec',fontSize=9,fontName='Helvetica-Bold',textColor=VERDE_OSC,spaceAfter=5)
    fic_st  = ParagraphStyle('fic',fontSize=18,leading=22,textColor=VERDE_OSC,fontName='Helvetica-Bold',spaceAfter=2)
    ley_st  = ParagraphStyle('ley',fontSize=6.5,leading=8,textColor=BLANCO,fontName='Helvetica-Bold',alignment=TA_CENTER)
    cnom_st = ParagraphStyle('cn',fontSize=9,leading=12,textColor=BLANCO,fontName='Helvetica-Bold',alignment=TA_CENTER)
    cnot_st = ParagraphStyle('cno',fontSize=7.5,leading=10,textColor=GRIS_MED,fontName='Helvetica',alignment=TA_CENTER)

    story = []
    story.append(Paragraph('Distribución de especies', dist_st))
    story.append(HRFlowable(width='100%',thickness=2,color=VERDE_CLAR,spaceAfter=8))
    if plan_b64:
        pl = rli(plan_b64, PAGE_W-3*cm, 13*cm)
        if pl: story.append(pl)
    story.append(Spacer(1,10))

    if species_list:
        story.append(Paragraph('LEYENDA DE ESPECIES', sec_st))
        N=len(species_list); IW=(PAGE_W-3*cm)/N; IH=2.5*cm
        ic,nc=[],[]
        for sp in species_list:
            img=rli(sp.get('icon'),IW-8,IH-8) if sp.get('icon') else None
            cell=Table([[img if img else dot_drawing(IW*0.7,IH*0.7)]],colWidths=[IW])
            cell.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3)]))
            ic.append(cell)
            nc.append(Paragraph(f'<b>{sp["name"]}</b>',ley_st))
        ir=Table([ic],colWidths=[IW]*N)
        ir.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('BACKGROUND',(0,0),(-1,-1),BEIGE),('BOX',(0,0),(-1,-1),1,colors.HexColor('#CCCCCC')),
            ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#DDDDDD')),
            ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
            ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        nr=Table([nc],colWidths=[IW]*N)
        nr.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('BACKGROUND',(0,0),(-1,-1),VERDE_OSC),('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#3a6b20')),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2)]))
        story.append(ir); story.append(nr)

    if species_list:
        story.append(PageBreak())
        story.append(Paragraph('Fichas de especies',fic_st))
        story.append(HRFlowable(width='100%',thickness=2,color=VERDE_CLAR,spaceAfter=10))
        COLS=3; GAP=0.4*cm; CW=(PAGE_W-3*cm-GAP*(COLS-1))/COLS
        ICO_H=3.0*cm; PHO_H=4.5*cm

        def make_card(sp):
            hdr=Table([[Paragraph(f'<b>{sp["name"]}</b>',cnom_st)]],colWidths=[CW])
            hdr.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),VERDE_OSC),
                ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
            ico_img=rli(sp.get('icon'),CW-0.6*cm,ICO_H) if sp.get('icon') else None
            ico=Table([[ico_img if ico_img else dot_drawing(CW*0.5,ICO_H*0.8)]],colWidths=[CW])
            ico.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('BACKGROUND',(0,0),(-1,-1),BEIGE),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            pho_img=rli(sp.get('photo'),CW-0.4*cm,PHO_H) if sp.get('photo') else None
            pho=None
            if pho_img:
                pho=Table([[pho_img]],colWidths=[CW])
                pho.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                    ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F8F8F8')),
                    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            notes=sp.get('notes','')
            not_cell=None
            if notes:
                not_cell=Table([[Paragraph(notes,cnot_st)]],colWidths=[CW])
                not_cell.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),BEIGE),
                    ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                    ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
            rows=[[hdr],[ico]]
            if pho: rows.append([pho])
            if not_cell: rows.append([not_cell])
            card=Table(rows,colWidths=[CW])
            card.setStyle(TableStyle([('BOX',(0,0),(-1,-1),1,colors.HexColor('#BBBBBB')),
                ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
            return card

        for i in range(0,len(species_list),COLS):
            batch=species_list[i:i+COLS]
            cards=[make_card(s) for s in batch]
            while len(cards)<COLS: cards.append(Spacer(CW,1))
            rd,ws=[],[]
            for j,c in enumerate(cards):
                rd.append(c); ws.append(CW)
                if j<COLS-1: rd.append(Spacer(GAP,1)); ws.append(GAP)
            row=Table([rd],colWidths=ws)
            row.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
                ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
            story.append(row)

    doc.build(story)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
