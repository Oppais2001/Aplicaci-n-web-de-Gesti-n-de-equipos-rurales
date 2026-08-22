from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, legal, letter, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


FORMATOS = {
    "carta": letter,
    "oficio": legal,
    "a4": A4,
}

NOMBRES_FORMATOS = {
    "carta": "Carta",
    "oficio": "Oficio",
    "a4": "A4",
}

DOCUMENTOS_DISPONIBLES = {
    "ficha_jugador": {
        "nombre": "Ficha jugador",
        "descripcion": "Formulario de inscripcion, pases y datos del jugador.",
        "orientacion": "Vertical",
        "generador": "crear_ficha_jugador_pdf",
        "archivo": "ficha_jugador",
    },
    "papeleta_partido": {
        "nombre": "Papeleta de partido",
        "descripcion": "Planilla oficial con nominas, firmas, informes y valores.",
        "orientacion": "Horizontal",
        "generador": "crear_papeleta_partido_pdf",
        "archivo": "papeleta_partido",
    },
}


def obtener_tamano_pagina(formato, orientacion="portrait"):
    pagina = FORMATOS.get(str(formato).lower(), letter)
    if orientacion == "landscape":
        return landscape(pagina)
    return pagina


def _draw_logo(c, ruta_logo, x, y, width, height, alpha=None):
    if not ruta_logo:
        return

    try:
        imagen = ImageReader(ruta_logo)
        c.saveState()
        if alpha is not None:
            try:
                c.setFillAlpha(alpha)
            except Exception:
                pass
        c.drawImage(
            imagen,
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask="auto",
        )
        c.restoreState()
    except Exception:
        pass


def _texto(c, x, y, value, size=9, bold=False, align="left"):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    if align == "center":
        c.drawCentredString(x, y, value)
    elif align == "right":
        c.drawRightString(x, y, value)
    else:
        c.drawString(x, y, value)


def _linea(c, x1, y1, x2, y2, grosor=1):
    c.setStrokeColor(colors.black)
    c.setLineWidth(grosor)
    c.line(x1, y1, x2, y2)


def _rect(c, x, y, width, height, grosor=1):
    c.setStrokeColor(colors.black)
    c.setLineWidth(grosor)
    c.rect(x, y, width, height, stroke=1, fill=0)


def _checkbox(c, x, y, lado=10):
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.rect(x, y, lado, lado, stroke=1, fill=1)
    c.setFillColor(colors.black)


def crear_ficha_jugador_pdf(formato="carta", ruta_logo=None):
    ancho, alto = obtener_tamano_pagina(formato)
    base_ancho, base_alto = letter
    sx = ancho / base_ancho
    sy = alto / base_alto
    escala = min(sx, sy)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(ancho, alto))

    margen = 20 * mm * escala
    logo_size = 60 * escala
    centro = ancho / 2
    content_width = ancho - 2 * margen

    marca_size = min(ancho, alto) * 0.72
    _draw_logo(
        c,
        ruta_logo,
        (ancho - marca_size) / 2,
        (alto - marca_size) / 2,
        marca_size,
        marca_size,
        alpha=0.15,
    )

    _draw_logo(c, ruta_logo, margen, alto - margen / 2 - logo_size, logo_size, logo_size)
    _draw_logo(c, ruta_logo, ancho - margen - logo_size, alto - margen / 2 - logo_size, logo_size, logo_size)

    _texto(c, centro, alto - margen - 5 * escala, "FICHA JUGADOR", size=20 * escala, bold=True, align="center")
    _texto(
        c,
        centro,
        alto - margen - 25 * escala,
        '"UNION COMUNAL DE CLUBES DEPORTIVOS RURALES, SOCIALES Y CULTURALES ENTRE RIOS.',
        size=8 * escala,
        bold=True,
        align="center",
    )
    _texto(
        c,
        centro,
        alto - margen - 35 * escala,
        'EX LIGA CANCURA. PUERTO OCTAY"',
        size=8 * escala,
        bold=True,
        align="center",
    )

    y_check = alto - margen - 65 * escala
    col_x = [margen, margen + 65 * mm * sx, margen + 130 * mm * sx]
    fila_h = 16 * escala
    opciones = [
        ["1. PASE COSTA/POLLOICO", "4. PRESTAMO NORMAL", "7. PASE SENIOR"],
        ["2. PASE ANFA", "5. PRESTAMO JUVENIL", "8. JUGADOR NUEVO"],
        ["3. PASE NORMAL", "6. JUGADOR RECESO", "9. PASE ANTICIPADO"],
    ]

    for fila_idx, fila in enumerate(opciones):
        y = y_check - fila_idx * fila_h
        for col_idx, etiqueta in enumerate(fila):
            x = col_x[col_idx]
            _checkbox(c, x, y - 8 * escala, lado=10 * escala)
            _texto(c, x + 14 * escala, y - 6 * escala, etiqueta, size=9 * escala)

    y_ci_label = y_check - 3 * fila_h - 15 * escala
    _texto(c, margen, y_ci_label, "FOTOCOPIA CEDULA DE IDENTIDAD", size=10 * escala, bold=True)

    box_ci_h = 90 * mm * sy
    box_ci_y = y_ci_label - 10 * escala - box_ci_h
    _rect(c, margen, box_ci_y, content_width, box_ci_h)

    y_nombre_label = box_ci_y - 30 * escala
    _texto(c, centro, y_nombre_label, "NOMBRE COMPLETO JUGADOR", size=10 * escala, bold=True, align="center")

    y_nombre_box = y_nombre_label - 25 * escala
    _rect(c, margen, y_nombre_box, content_width, 20 * escala)

    y_rut = y_nombre_box - 35 * escala
    alto_rut = 25 * escala
    ancho_rut = content_width * 0.30
    ancho_fecha = content_width * 0.40
    ancho_firma = content_width * 0.30

    x0 = margen
    _rect(c, x0, y_rut, ancho_rut, alto_rut)
    _texto(c, x0 + 4 * escala, y_rut + alto_rut - 12 * escala, "R.U.T:", size=9 * escala, bold=True)

    x1 = x0 + ancho_rut
    _rect(c, x1, y_rut, ancho_fecha, alto_rut)
    _texto(c, x1 + 4 * escala, y_rut + alto_rut - 12 * escala, "FECHA DE NACIMIENTO:", size=9 * escala, bold=True)

    x2 = x1 + ancho_fecha
    _rect(c, x2, y_rut, ancho_firma, alto_rut)
    _texto(c, x2 + 4 * escala, y_rut + alto_rut - 12 * escala, "FIRMA:", size=9 * escala, bold=True)

    y_inst_top = y_rut - 20 * escala
    alto_inst = 150 * escala
    ancho_inst = (content_width - 10 * escala) / 2
    x_origen = margen
    x_destino = margen + ancho_inst + 10 * escala
    y_inst_bottom = y_inst_top - alto_inst

    _rect(c, x_origen, y_inst_bottom, ancho_inst, alto_inst)
    _rect(c, x_destino, y_inst_bottom, ancho_inst, alto_inst)

    def bloque_institucion(x, titulo):
        y = y_inst_top - 15 * escala
        _texto(c, x + 5 * escala, y, titulo, size=10 * escala, bold=True)
        for label, salto in [
            ("CLUB", 16),
            ("DEPORTIVO:", 11),
            ("LIGA:", 11),
            ("PRESIDENTE DE CLUB", 20),
            ("NOMBRE:", 13),
            ("R.U.T:", 13),
            ("FIRMA:", 13),
            ("FECHA DE TRAMITACION:", 13),
        ]:
            y -= salto * escala
            _texto(c, x + 5 * escala, y, label, size=9 * escala, bold=True)
        y -= 15 * escala
        _texto(c, x + ancho_inst / 2, y, "TIMBRE", size=9 * escala, bold=True, align="center")

    bloque_institucion(x_origen, "INSTITUCION DE ORIGEN")
    bloque_institucion(x_destino, "INSTITUCION DE DESTINO")

    y_firma_final = y_inst_bottom - 45 * escala
    _texto(c, centro, y_firma_final, "FIRMA DIRIGENTE DE LIGA QUE RECEPCIONA", size=10 * escala, bold=True, align="center")

    c.save()
    buffer.seek(0)
    return buffer


def _campo_linea(c, etiqueta, x, y, ancho, size):
    _texto(c, x, y, etiqueta, size=size, bold=True)
    ancho_etiqueta = c.stringWidth(etiqueta, "Helvetica-Bold", size)
    _linea(c, x + ancho_etiqueta + 3, y - 1, x + ancho, y - 1, grosor=0.7)


def _dibujar_marca_agua_planilla(c, ancho, alto, ruta_logo, sx, sy):
    _draw_logo(c, ruta_logo, (ancho - 700 * sx) / 2, (alto - 500 * sy) / 2 - 20 * sy, 700 * sx, 500 * sy, alpha=0.15)


def _dibujar_tabla_pequena(c, x, y, ancho, alto, titulo, columnas, filas, sx, sy):
    alto_titulo = 20 * sy
    alto_columnas = 20 * sy
    ancho_columna = ancho / len(columnas)

    _rect(c, x, y - alto, ancho, alto, grosor=1.5)
    _linea(c, x, y - alto_titulo, x + ancho, y - alto_titulo)
    _texto(c, x + ancho / 2, y - 14 * sy, titulo, size=7.5 * sy, bold=True, align="center")
    _linea(c, x, y - alto_titulo - alto_columnas, x + ancho, y - alto_titulo - alto_columnas, grosor=0.8)

    for i in range(1, len(columnas)):
        _linea(c, x + i * ancho_columna, y - alto_titulo, x + i * ancho_columna, y - alto, grosor=0.7)

    for i, columna in enumerate(columnas):
        _texto(c, x + i * ancho_columna + ancho_columna / 2, y - alto_titulo - 14 * sy, columna, size=6.5 * sy, bold=True, align="center")

    alto_fila = (alto - alto_titulo - alto_columnas) / filas
    y_inicio = y - alto_titulo - alto_columnas
    for i in range(filas):
        yy = y_inicio - (i + 1) * alto_fila
        _linea(c, x, yy, x + ancho, yy, grosor=0.6)


def _dibujar_tabla_equipo(c, x, y, ancho, alto, nombre_equipo, filas, sx, sy):
    alto_encabezado_equipo = 20 * sy
    alto_encabezado_columnas = 22 * sy
    alto_fila = (alto - alto_encabezado_equipo - alto_encabezado_columnas) / filas

    _rect(c, x, y - alto, ancho, alto, grosor=2)
    _linea(c, x, y - alto_encabezado_equipo, x + ancho, y - alto_encabezado_equipo)
    _texto(c, x + 5 * sx, y - 14 * sy, f"{nombre_equipo}:", size=8.5 * sy, bold=True)
    _texto(c, x + ancho - 90 * sx, y - 14 * sy, "GOLES:", size=8.5 * sy, bold=True)
    _linea(c, x + 50 * sx, y - 15 * sy, x + ancho - 95 * sx, y - 15 * sy, grosor=0.7)
    _linea(c, x + ancho - 52 * sx, y - 15 * sy, x + ancho - 5 * sx, y - 15 * sy, grosor=0.7)

    y_columnas = y - alto_encabezado_equipo
    _linea(c, x, y_columnas - alto_encabezado_columnas, x + ancho, y_columnas - alto_encabezado_columnas, grosor=0.8)

    col_num = 30 * sx
    col_nombre = 185 * sx
    col_identidad = 115 * sx
    x1 = x + col_num
    x2 = x1 + col_nombre
    x3 = x2 + col_identidad

    for xx in (x1, x2, x3):
        _linea(c, xx, y_columnas, xx, y - alto, grosor=0.6)

    _texto(c, x + 8 * sx, y_columnas - 15 * sy, "N", size=8 * sy, bold=True)
    _texto(c, x1 + 5 * sx, y_columnas - 15 * sy, "NOMBRE JUGADOR", size=8 * sy, bold=True)
    _texto(c, x2 + 5 * sx, y_columnas - 15 * sy, "C. IDENTIDAD", size=8 * sy, bold=True)
    _texto(c, x3 + 5 * sx, y_columnas - 15 * sy, "FIRMA", size=8 * sy, bold=True)

    y_inicio = y - alto_encabezado_equipo - alto_encabezado_columnas
    for i in range(filas):
        yy = y_inicio - (i + 1) * alto_fila
        _linea(c, x, yy, x + ancho, yy, grosor=0.45)


def _dibujar_datos_equipo(c, x, y, ancho, sx, sy):
    _texto(c, x, y - 15 * sy, "NOMBRE", size=7.5 * sy, bold=True)
    _texto(c, x, y - 29 * sy, "ENTRENADOR:", size=7.5 * sy, bold=True)
    _linea(c, x + 75 * sx, y - 30 * sy, x + 190 * sx, y - 30 * sy, grosor=0.7)
    _texto(c, x, y - 55 * sy, "FIRMA:", size=7.5 * sy, bold=True)
    _linea(c, x + 42 * sx, y - 56 * sy, x + 165 * sx, y - 56 * sy, grosor=0.7)
    _linea(c, x + 65 * sx, y - 85 * sy, x + 160 * sx, y - 85 * sy, grosor=0.7)
    _texto(c, x + 112 * sx, y - 98 * sy, "FIRMA CAPITAN", size=7 * sy, bold=True, align="center")

    x_cambios = x + 205 * sx
    _dibujar_tabla_pequena(c, x_cambios, y, 75 * sx, 108 * sy, "CAMBIOS", ["ENTRA", "SALE"], 5, sx, sy)
    _dibujar_tabla_pequena(c, x_cambios + 85 * sx, y, 75 * sx, 108 * sy, "TARJETAS", ["AMARILLA", "ROJA"], 5, sx, sy)


def _dibujar_pagina_planilla_1(c, ancho, alto, ruta_logo, sx, sy):
    _dibujar_marca_agua_planilla(c, ancho, alto, ruta_logo, sx, sy)
    centro = ancho / 2
    _texto(c, centro, alto - 28 * sy, "CAMPEONATO OFICIAL LIGA RURAL CANCURA", size=12 * sy, bold=True, align="center")
    _campo_linea(c, "TURNO:", 20 * sx, alto - 48 * sy, 340 * sx, 9 * sy)
    _campo_linea(c, "ARBITRO:", 20 * sx, alto - 72 * sy, 340 * sx, 9 * sy)
    _campo_linea(c, "FECHA:", ancho - 297 * sx, alto - 72 * sy, 200 * sx, 9 * sy)
    _campo_linea(c, "ASISTENTE 1:", 20 * sx, alto - 96 * sy, 340 * sx, 9 * sy)
    _campo_linea(c, "HORA:", ancho - 297 * sx, alto - 96 * sy, 200 * sx, 9 * sy)
    _campo_linea(c, "ASISTENTE 2:", 20 * sx, alto - 120 * sy, 340 * sx, 9 * sy)

    x = 5 * mm * sx
    ancho_total = ancho - 10 * mm * sx
    ancho_equipo = ancho_total / 2
    y_tabla = alto - 125 * sy
    alto_tabla = 310 * sy

    _dibujar_tabla_equipo(c, x, y_tabla, ancho_equipo, alto_tabla, "LOCAL", 15, sx, sy)
    _dibujar_tabla_equipo(c, x + ancho_equipo, y_tabla, ancho_equipo, alto_tabla, "VISITANTE", 15, sx, sy)

    y_inferior = 145 * sy
    _dibujar_datos_equipo(c, x + 5 * sx, y_inferior, ancho_equipo - 10 * sx, sx, sy)
    _dibujar_datos_equipo(c, x + ancho_equipo + 5 * sx, y_inferior, ancho_equipo - 10 * sx, sx, sy)

    _linea(c, x, y_tabla, x, 30 * sy, grosor=1.5)
    _linea(c, x + ancho_total, y_tabla, x + ancho_total, 30 * sy, grosor=1.5)
    _linea(c, x, y_inferior - 114 * sy, x + ancho_total, y_inferior - 114 * sy, grosor=1.5)
    _linea(c, ancho / 2, y_tabla, ancho / 2, 30 * sy, grosor=1.5)


def _dibujar_pagina_planilla_2(c, ancho, alto, ruta_logo, sx, sy):
    _dibujar_marca_agua_planilla(c, ancho, alto, ruta_logo, sx, sy)
    centro = ancho / 2
    _texto(c, centro, alto - 28 * sy, "INFORMES", size=13 * sy, bold=True, align="center")

    x = 10 * mm * sx
    y = alto - 45 * sy
    ancho_box = ancho - 20 * mm * sx
    alto_box = 530 * sy
    mitad = x + ancho_box / 2

    _rect(c, x, y - alto_box, ancho_box, alto_box, grosor=2)
    _linea(c, mitad, y, mitad, y - alto_box, grosor=0.8)
    _linea(c, x, y - 25 * sy, x + ancho_box, y - 25 * sy, grosor=0.8)
    _texto(c, x + ancho_box / 4, y - 17 * sy, "INFORMES DEL ARBITRO", size=8.5 * sy, bold=True, align="center")
    _texto(c, x + 3 * ancho_box / 4, y - 17 * sy, "INFORME DIRECTOR DE TURNO", size=8.5 * sy, bold=True, align="center")

    inicio_lineas = y - 25 * sy
    espacio = (245 * sy - 25 * sy) / 15
    for i in range(15):
        yy = inicio_lineas - (i + 1) * espacio
        _linea(c, x, yy, x + ancho_box, yy, grosor=0.4)

    x_izq = x + 6 * sx
    y_info = y - 270 * sy
    for label, dy, line_offset in [
        ("GOLES LOCAL N", 0, 78),
        ("GOLES VISITA N", 22, 78),
        ("EXPULSADOS", 58, None),
        ("LOCAL N", 80, 55),
        ("VISITA N", 101, 55),
        ("TARJETAS AMARILLAS", 137, None),
        ("LOCAL N", 159, 55),
        ("VISITA N", 180, 55),
    ]:
        _texto(c, x_izq, y_info - dy * sy, label, size=8 * sy, bold=True)
        if line_offset:
            _linea(c, x_izq + line_offset * sx, y_info - (dy + 1) * sy, mitad - 15 * sx, y_info - (dy + 1) * sy, grosor=0.7)

    y_firma = y - alto_box + 35 * sy
    _linea(c, x_izq, y_firma, x_izq + 230 * sx, y_firma, grosor=0.7)
    _linea(c, x_izq + 255 * sx, y_firma, mitad - 10 * sx, y_firma, grosor=0.7)
    _texto(c, x_izq + 115 * sx, y_firma - 15 * sy, "NOMBRE ARBITRO", size=7 * sy, bold=True, align="center")
    _texto(c, x_izq + 300 * sx, y_firma - 15 * sy, "FIRMA ARBITRO", size=7 * sy, bold=True, align="center")

    x_valores = mitad + 8 * sx
    y_valores = y - 250 * sy
    ancho_valores = 260 * sx
    alto_valores = 195 * sy
    _rect(c, x_valores, y_valores - alto_valores, ancho_valores, alto_valores, grosor=1.2)
    _texto(c, x_valores + ancho_valores / 2, y_valores - 15 * sy, "VALORES", size=8 * sy, bold=True, align="center")
    _linea(c, x_valores, y_valores - 25 * sy, x_valores + ancho_valores, y_valores - 25 * sy, grosor=0.8)

    conceptos = [
        "ARBITRAJES LOCAL",
        "ARBITRAJES VISITA",
        "AMARILLAS LOCAL",
        "AMARILLAS VISITA",
        "MULTAS LOCAL",
        "MULTAS VISITA",
        "OTROS LOCAL",
        "OTROS VISITA",
    ]
    alto_fila = (alto_valores - 25 * sy) / len(conceptos)
    ancho_concepto = 130 * sx
    _linea(c, x_valores + ancho_concepto, y_valores - 25 * sy, x_valores + ancho_concepto, y_valores - alto_valores, grosor=0.8)
    for i, concepto in enumerate(conceptos):
        yy = y_valores - 25 * sy - (i + 1) * alto_fila
        _linea(c, x_valores, yy, x_valores + ancho_valores, yy, grosor=0.6)
        _texto(c, x_valores + 6 * sx, yy + alto_fila / 2 - 3 * sy, concepto, size=7.2 * sy, bold=True)

    _linea(c, mitad + 8 * sx, y_firma, mitad + 230 * sx, y_firma, grosor=0.7)
    _linea(c, mitad + 255 * sx, y_firma, x + ancho_box - 10 * sx, y_firma, grosor=0.7)
    _texto(c, mitad + 120 * sx, y_firma - 15 * sy, "NOMBRE DIRECTOR DE TURNO", size=7 * sy, bold=True, align="center")
    _texto(c, mitad + 300 * sx, y_firma - 15 * sy, "FIRMA DIRECTOR DE TURNO", size=7 * sy, bold=True, align="center")


def crear_papeleta_partido_pdf(formato="carta", ruta_logo=None):
    ancho, alto = obtener_tamano_pagina(formato, orientacion="landscape")
    base_ancho, base_alto = landscape(letter)
    sx = ancho / base_ancho
    sy = alto / base_alto

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(ancho, alto))
    _dibujar_pagina_planilla_1(c, ancho, alto, ruta_logo, sx, sy)
    c.showPage()
    _dibujar_pagina_planilla_2(c, ancho, alto, ruta_logo, sx, sy)
    c.save()
    buffer.seek(0)
    return buffer
