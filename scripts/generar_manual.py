"""Genera la guía de usuario del sistema (HTML y PDF opcional).

Uso:
    python scripts/generar_manual.py [--pdf]

El HTML se genera en docs/Guia_Chronos.html listo para abrir o imprimir.
El PDF solo se genera si se pasa --pdf y existe una herramienta de conversión
(weasyprint, chromium o wkhtmltopdf).
"""
import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DESTINO_DIR = BASE_DIR / 'docs'


def html_manual(fecha):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Guía de usuario — Chronos</title>
<style>
  :root {{
    --verde: #0f8a63;
    --verde-claro: #e8f5f0;
    --tinta: #17211e;
    --gris: #5b6b66;
    --borde: #d8e2de;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Outfit", "Segoe UI", system-ui, sans-serif;
    color: var(--tinta);
    background: #f6f9f8;
    line-height: 1.6;
    font-size: 15px;
  }}
  .hoja {{
    max-width: 820px;
    margin: 0 auto;
    background: #fff;
    padding: 48px 64px 72px;
  }}
  header {{
    border-bottom: 3px solid var(--verde);
    padding-bottom: 22px;
    margin-bottom: 32px;
  }}
  header .marca {{
    color: var(--verde);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .16em;
    text-transform: uppercase;
  }}
  h1 {{
    font-size: 32px;
    line-height: 1.15;
    margin: 8px 0 6px;
    letter-spacing: -.02em;
  }}
  header p {{ color: var(--gris); margin: 0; }}
  h2 {{
    font-size: 20px;
    margin: 38px 0 10px;
    padding-top: 12px;
    border-top: 1px solid var(--borde);
    letter-spacing: -.01em;
  }}
  h2 .num {{
    display: inline-grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: var(--verde);
    color: #fff;
    font-size: 13px;
    margin-right: 10px;
    vertical-align: 2px;
  }}
  h3 {{ font-size: 16px; margin: 22px 0 6px; }}
  p, li {{ color: #2e3b37; }}
  ol, ul {{ padding-left: 22px; }}
  li {{ margin-bottom: 6px; }}
  .nota {{
    background: var(--verde-claro);
    border-left: 4px solid var(--verde);
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 16px 0;
    font-size: 14px;
  }}
  .nota b {{ color: var(--verde); }}
  .alerta {{
    background: #fff6e8;
    border-left: 4px solid #d98b1c;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 16px 0;
    font-size: 14px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 18px;
    font-size: 14px;
  }}
  th, td {{
    text-align: left;
    padding: 9px 12px;
    border-bottom: 1px solid var(--borde);
    vertical-align: top;
  }}
  th {{
    background: #f2f7f5;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: var(--gris);
  }}
  .status-demo {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 9px;
    border-radius: 6px;
    background: #fdf2dc;
    color: #a5660a;
  }}
  .status-demo.ok {{ background: var(--verde-claro); color: var(--verde); }}
  .status-demo.off {{ background: #eef1f0; color: var(--gris); }}
  code {{
    background: #eef3f1;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 13px;
  }}
  .paso {{
    display: flex;
    gap: 14px;
    margin: 14px 0;
    padding: 14px 16px;
    border: 1px solid var(--borde);
    border-radius: 10px;
  }}
  .paso .n {{
    flex-shrink: 0;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: var(--verde-claro);
    color: var(--verde);
    font-weight: 800;
    display: grid;
    place-items: center;
  }}
  .paso b {{ display: block; margin-bottom: 2px; }}
  .paso p {{ margin: 0; font-size: 14px; color: var(--gris); }}
  footer {{
    margin-top: 48px;
    padding-top: 18px;
    border-top: 1px solid var(--borde);
    color: var(--gris);
    font-size: 12px;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }}
  @page {{ margin: 18mm 16mm; }}
  @media print {{
    body {{ background: #fff; font-size: 12.5px; }}
    .hoja {{ padding: 0; max-width: none; }}
    h2 {{ break-after: avoid; }}
    .paso, .nota, .alerta, table {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
<div class="hoja">

  <header>
    <div class="marca">Chronos · Sistema de horarios escolares</div>
    <h1>Guía de usuario</h1>
    <p>Cómo configurar el colegio y generar los horarios, paso a paso.</p>
  </header>

  <h2><span class="num">1</span>¿Qué hace Chronos?</h2>
  <p>
    Chronos arma los horarios de clase de todo el colegio de forma automática.
    A partir de la estructura del colegio, los profesores, sus materias y su
    disponibilidad, y las reglas que vos definas, el sistema busca la mejor
    combinación posible y se asegura de que <b>ningún profesor, aula o curso
    quede en dos lugares a la vez</b>.
  </p>
  <p>Lo que antes llevaba días de prueba y error, se resuelve en segundos y sin errores.</p>

  <h3>Beneficios</h3>
  <ul>
    <li>Horarios sin superposiciones, garantizadas por el sistema.</li>
    <li>Respeta la disponibilidad de cada docente.</li>
    <li>Cumple la carga horaria de cada materia y de cada curso.</li>
    <li>Permite ajustes manuales y guarda versiones: borrador, publicada e históricas.</li>
  </ul>

  <h2><span class="num">2</span>Antes de empezar: orden de la configuración</h2>
  <p>
    Las pantallas siguen un orden lógico. Si cargás los datos en este orden,
    no vas a encontrar dependencias vacías:
  </p>
  <table>
    <thead>
      <tr><th style="width: 40%">Pantalla</th><th>Qué se carga</th></tr>
    </thead>
    <tbody>
      <tr><td><b>Estructura → Años lectivos</b></td><td>El año de trabajo (por ejemplo 2026). Solo uno puede estar activo.</td></tr>
      <tr><td><b>Estructura → Niveles</b></td><td>Inicial, Primaria, Secundaria. El número de grados abre el listado filtrado de ese nivel.</td></tr>
      <tr><td><b>Estructura → Grados</b></td><td>Los cursos de cada nivel: 1er grado, 2do grado…</td></tr>
      <tr><td><b>Estructura → Turnos</b></td><td>Mañana, Tarde.</td></tr>
      <tr><td><b>Estructura → Aulas</b></td><td>Aulas regulares, laboratorios, sala de informática, gimnasio.</td></tr>
      <tr><td><b>Estructura → Materias</b></td><td>Las asignaturas y, si corresponde, el tipo de aula que necesitan.</td></tr>
      <tr><td><b>Estructura → Áreas</b></td><td>Agrupaciones de materias: Lengua, Ciencias Básicas, Técnicas, etc. Cada materia pertenece a un área.</td></tr>
      <tr><td><b>Estructura → Planes</b></td><td>Planes de estudio de cada ciclo y los grados que los componen.</td></tr>
      <tr><td><b>Profesores → Listado</b></td><td>Docentes, materias que pueden dictar y su carga máxima.</td></tr>
      <tr><td><b>Profesores → Disponibilidad</b></td><td>Días y horarios en que cada docente puede dar clases.</td></tr>
      <tr><td><b>Planificación → Plantillas y bloques</b></td><td>La grilla horaria de cada turno: horas de clase y recesos.</td></tr>
      <tr><td><b>Grados → Plan</b></td><td>Materias, horas semanales y tipo de plan de cada grado. Las áreas se heredan de la materia.</td></tr>
      <tr><td><b>Planificación → Secciones y plan</b></td><td>Los cursos concretos (A, B) con su profesor por materia.</td></tr>
      <tr><td><b>Planificación → Reglas</b></td><td>Preferencias pedagógicas opcionales.</td></tr>
      <tr><td><b>Planificación → Horarios</b></td><td>Generar, revisar y publicar el horario.</td></tr>
    </tbody>
  </table>

  <h2><span class="num">3</span>Configurar la estructura del colegio</h2>

  <h3>Años lectivos</h3>
  <p>Creá el año con su fecha de inicio y fin, y activalo. El año activo es el que se usa en todas las demás pantallas.</p>
  <div class="nota"><b>Importante:</b> al activar un año nuevo, el anterior se desactiva automáticamente.</div>

  <h3>Aulas</h3>
  <p>Indicá el tipo de cada espacio:</p>
  <ul>
    <li><b>Aula regular</b>: para materias comunes.</li>
    <li><b>Laboratorio / Informática / Gimnasio</b>: se usan solo cuando la materia los requiere.</li>
    <li><b>Inactiva</b>: el sistema no la va a usar, pero conserva su historial.</li>
  </ul>

  <h3>Materias</h3>
  <p>
    Si una materia necesita un espacio especial, elegilo en <b>Aula requerida</b>.
    Por ejemplo, Educación Física → Gimnasio. Así el sistema nunca la va a ubicar en un aula común.
  </p>
  <p>
    Cada materia pertenece a <b>un área de conocimiento</b>. Si necesitás la misma materia
    en otra área, creá otro registro con el mismo nombre y esa área.
    El área se hereda al agregar la materia al plan de un grado.
  </p>

  <h3>Áreas de conocimiento</h3>
  <p>
    Las áreas agrupan materias por campo del saber: Lengua, Ciencias Básicas, Técnicas, etc.
    Cada materia pertenece a un área. Si necesitás la misma materia en otra área,
    creá otro registro de materia con el mismo nombre y esa área.
  </p>
  <p>
    En el listado, la columna <b>Materias</b> cuenta las materias distintas del área.
    Si hacés clic en ese número, se abre el listado filtrado con esas materias.
    El campo <b>Orden</b> solo define el orden de visualización; no afecta la generación del horario.
  <h2><span class="num">4</span>Cargar profesores</h2>
  <p>Para cada docente registrá:</p>
  <ul>
    <li><b>Nombre</b> y documento.</li>
    <li><b>Materias que puede dictar</b>: solo se le van a asignar esas.</li>
    <li><b>Horas semanales</b>: único tope de carga del docente. El sistema no lo supera.</li>
    <li><b>Historial por año</b>: se guarda el valor de cada año lectivo para futuros reportes; no se muestra en el formulario.</li>
  </ul>
  <p>
    Mientras el formulario de alta o edición está abierto, el listado de profesores se oculta.
    Al guardar o cancelar, vuelve el listado. Desde la edición podés ir directo a
    <b>Ver disponibilidad</b>.
  </p>
  <div class="alerta">
    Si no cargás las horas máximas, el sistema no limitará la carga del docente.
    Recomendamos completarlas siempre.
  </div>

  <h2><span class="num">5</span>Disponibilidad de los profesores</h2>
  <p>
    Elegí el docente en el selector: la disponibilidad se actualiza automáticamente,
    sin necesidad de un botón. Cada docente tiene su grilla semanal con dos tipos de franjas:
  </p>
  <ul>
    <li><b>Disponible</b> (verde): el docente solo podrá dar clases dentro de estas franjas.</li>
    <li><b>No disponible</b> (rojo): siempre se descartan, con el motivo que quieras dejar asentado.</li>
  </ul>
  <div class="nota"><b>Tranquilidad:</b> si un profesor no tiene franjas cargadas, se entiende que puede dar clase en cualquier horario.</div>
  <p>Las franjas no pueden superponerse entre sí; el sistema lo controla y avisa si hay conflicto.</p>
  <div class="nota"><b>Formularios y listados:</b> en las pantallas de estructura, al abrir un formulario se oculta el listado para evitar confusiones. Al cerrar o guardar, vuelve.</div>

  <h2><span class="num">6</span>Plantillas de horario</h2>
  <p>
    La plantilla es la grilla base de un turno. Por ejemplo, turno mañana:
    07:00 a 07:45, 07:45 a 08:30, un receso de 09:15 a 09:45 y así hasta el final de la jornada.
  </p>
  <ul>
    <li>Los bloques de tipo <b>clase</b> son los que se pueden asignar a materias.</li>
    <li>Los bloques de tipo <b>receso</b> quedan libres en la grilla.</li>
    <li>Los bloques no pueden solaparse dentro del mismo día.</li>
    <li>Una plantilla puede tener días con distinta cantidad de bloques: por ejemplo, 9 bloques de lunes a viernes y un décimo bloque martes y jueves.</li>
    <li>La duración de la hora cátedra se configura en <b>Configuración</b>, pero es informativa: manda la hora real de cada bloque.</li>
  </ul>

  <h2><span class="num">7</span>Plan de estudios</h2>
  <p>Hay dos niveles de detalle:</p>
  <table>
    <thead><tr><th style="width: 40%">Dónde</th><th>Para qué</th></tr></thead>
    <tbody>
      <tr><td><b>Grados → Plan</b></td><td>Define las materias, horas semanales y tipo de plan (común, específico u optativo) de cada grado. Las áreas se heredan de la materia.</td></tr>
      <tr><td><b>Secciones → Plan</b></td><td>Cada curso concreto puede tener ajustes propios.</td></tr>
    </tbody>
  </table>
  <p>Al crear una sección, el plan del grado se copia automáticamente. Si después cambiás el plan del grado, podés actualizar la sección con el botón <b>Sincronizar desde el grado</b>.</p>
  <p>En <b>Áreas de conocimiento</b> definís las <b>horas máximas por semana</b> del área. Ese máximo se aplica a cada grado: la suma de las materias de esa área no puede superarlo. Por ejemplo, Lengua 7 h puede estar formada por Castellano 5 h + Guaraní 2 h.</p>
  <div class="alerta">
    El sistema avisa si las horas del plan superan los bloques de clase disponibles en la plantilla.
    En ese caso no se puede generar el horario hasta que se ajuste.
  </div>

  <h2><span class="num">8</span>Crear las secciones</h2>
  <p>Una sección es un curso concreto: por ejemplo, <i>1er grado, turno mañana, división A</i>. Para crearla elegís:</p>
  <ul>
    <li>Grado y turno.</li>
    <li>Nombre o división (A, B, Única).</li>
    <li>Plantilla de horario del turno.</li>
    <li>Aula base (opcional).</li>
  </ul>
  <p>Después, en el <b>Plan</b> de cada sección, podés asignar el profesor de cada materia y fijarlo, para que el generador no lo cambie.</p>

  <h2><span class="num">9</span>Reglas del horario</h2>
  <p>Las reglas le dan criterio pedagógico al resultado. Pueden ser:</p>
  <ul>
    <li><b>Obligatorias</b>: nunca se incumplen.</li>
    <li><b>Deseables</b>: se cumplen en la medida de lo posible, según su <b>peso</b>.</li>
  </ul>
  <table>
    <thead><tr><th style="width: 40%">Regla</th><th>Qué busca</th></tr></thead>
    <tbody>
      <tr><td>Antes del receso</td><td>Ubicar una materia antes del primer receso del día.</td></tr>
      <tr><td>Evitar última hora</td><td>No dejar una materia en el último bloque.</td></tr>
      <tr><td>Distribuir en la semana</td><td>Repartir las horas de una materia entre varios días.</td></tr>
      <tr><td>Evitar huecos del profesor</td><td>Evitar horas libres entre clases del mismo docente.</td></tr>
      <tr><td>Máximo de horas diarias</td><td>Limitar cuántas horas seguidas dicta un docente por día.</td></tr>
    </tbody>
  </table>
  <p>Cada regla puede aplicarse a todo el colegio o solo a una materia, un nivel o un profesor.</p>

  <h2><span class="num">10</span>Generar el horario</h2>
  <div class="paso">
    <div class="n">1</div>
    <div><b>Ir a Planificación → Horarios</b><p>Elegí el turno y, si querés, un nombre para la versión.</p></div>
  </div>
  <div class="paso">
    <div class="n">2</div>
    <div><b>Presionar “Generar horario”</b><p>El sistema calcula la mejor combinación. Tarda apenas unos segundos.</p></div>
  </div>
  <div class="paso">
    <div class="n">3</div>
    <div><b>Revisar la grilla</b><p>Entrás directo al detalle. Cada sección muestra sus bloques día por día con materia, docente y aula.</p></div>
  </div>
  <div class="paso">
    <div class="n">4</div>
    <div><b>Ajustar si hace falta</b><p>Podés editar una celda, agregar una clase en un bloque vacío o eliminar una clase.</p></div>
  </div>
  <div class="paso">
    <div class="n">5</div>
    <div><b>Publicar</b><p>Cuando el horario está completo, lo publicás. La versión anterior del mismo turno pasa a archivada.</p></div>
  </div>

  <h3>Si el sistema no puede generar el horario</h3>
  <p>Te va a mostrar el motivo exacto, por ejemplo:</p>
  <ul>
    <li>Un profesor no tiene disponibilidad para una materia.</li>
    <li>No hay aula del tipo requerido libre.</li>
    <li>El plan tiene más horas que bloques disponibles.</li>
    <li>Un profesor supera su carga máxima.</li>
  </ul>
  <p>Corregí ese punto y volvé a generar.</p>

  <h2><span class="num">11</span>Edición manual y bloqueo de celdas</h2>
  <p>
    En la grilla de cada sección podés tocar el lápiz de una celda para cambiar la materia,
    el bloque, el aula o el docente. También podés seguir sumando clase donde haya bloques vacíos.
  </p>
  <div class="nota">
    <b>Celda fijada:</b> al marcarla, esa clase se conserva aunque vuelvas a generar el horario.
    Ideal para las clases que ya se acordaron con los docentes.
  </div>
  <p>
    El sistema impide guardar cualquier cambio que provoque una superposición de docente,
    aula o sección, o que supere las horas planificadas de la materia.
  </p>

  <h2><span class="num">12</span>Versiones de horario</h2>
  <p>Cada generación crea una <b>versión</b>, que puede estar en tres estados:</p>
  <table>
    <thead><tr><th style="width: 30%">Estado</th><th>Significado</th></tr></thead>
    <tbody>
      <tr><td><span class="status-demo">Borrador</span></td><td>En trabajo. Se puede editar libremente.</td></tr>
      <tr><td><span class="status-demo ok">Publicado</span></td><td>Versión oficial. Solo puede haber una por turno y año.</td></tr>
      <tr><td><span class="status-demo off">Archivado</span></td><td>Histórico. Se consulta, no se edita.</td></tr>
    </tbody>
  </table>
  <p>Además podés <b>duplicar</b> una versión para probar cambios sin afectar la publicada, o <b>regenerar</b> conservando las celdas que fijaste.</p>

  <h2><span class="num">13</span>Consultar e imprimir</h2>
  <ul>
    <li><b>Vista por sección</b>: el horario de cada curso.</li>
    <li><b>Vista por profesor</b>: todas las clases de un docente, con curso, aula y día.</li>
    <li><b>Horario general</b>: una tabla con todas las secciones del turno como columnas y los días como pestañas.
        Es la hoja que se imprime y se pega en la sala de profesores.</li>
    <li><b>Horario individual docente</b>: la grilla de un docente con sus horas totales y sus materias,
        separada por ciclo y por turno (por ejemplo “Secundaria · Mañana” y “Secundaria · Tarde”).
        Se imprime desde <i>Horarios docentes</i>.</li>
    <li><b>Distribución de materias</b>: materias por área y tipo de plan, horas semanales y docente
        asignado en cada sección. Se filtra por año, plan y grado.</li>
    <li><b>Presentación para el cliente</b>: resumen visual de funcionalidades en <code>/presentacion</code>.</li>
    <li><b>Imprimir</b>: genera una versión limpia, sin menús, en horizontal, lista para entregar.</li>
  </ul>
  <div class="nota">
    Los nombres de las filas que no son clase (Actividades Formativas, Almuerzo, Receso) se pueden
    personalizar en <code>config.py</code>, en <code>ETIQUETAS_BLOQUES</code>, sin tocar la base de datos.
    La duración informativa de la hora cátedra se configura en <b>Configuración</b>.
  </div>

  <h2><span class="num">14</span>Dashboard</h2>
  <p>Es la pantalla de inicio y responde de un vistazo:</p>
  <ul>
    <li>Cuántas horas del plan ya están asignadas en un horario vigente.</li>
    <li>La carga semanal de cada profesor, en rojo si supera su máximo.</li>
    <li>La distribución de horas por materia y por día.</li>
    <li>Qué aulas están más ocupadas.</li>
    <li>Avisos: secciones sin plan, profesores sin disponibilidad y turnos sin publicar.</li>
  </ul>

  <h2><span class="num">15</span>Usuarios y acceso</h2>
  <p>
    Cada colegio tiene acceso a su propio espacio. Los usuarios se crean desde la pantalla
    <b>Usuarios</b>, y desde <b>Mi perfil</b> cada uno puede cambiar su correo y su contraseña.
  </p>
  <div class="alerta">
    Nunca compartas tu contraseña ni uses la misma que en otros servicios.
    El sistema registra quién está trabajando en cada momento.
  </div>

  <h2><span class="num">16</span>Preguntas frecuentes</h2>
  <h3>Cambié un profesor de baja, ¿qué hago?</h3>
  <p>Marcalo como inactivo en Profesores → Listado. Después, en la sección donde dictaba, asigná otro docente y regenerá el horario.</p>

  <h3>Agregamos un aula nueva</h3>
  <p>Se crea en Estructura → Aulas. Desde ese momento el sistema puede usarla al generar.</p>

  <h3>El horario publicado quedó desactualizado</h3>
  <p>Generá un nuevo horario, revisalo y publicalo. La versión anterior queda archivada automáticamente, sin perder el historial.</p>

  <h3>¿Puedo hacer cambios manuales después de publicar?</h3>
  <p>Sí, pero conviene hacerlos sobre un borrador nuevo (duplicando la publicada) para mantener el registro de la versión oficial intacto.</p>

  <h3>¿Se pueden hacer horarios para varias horas seguidas de una materia?</h3>
  <p>Sí, se marca la materia como “requiere bloque doble” en el plan. El sistema la ubica en bloques consecutivos.</p>

  <footer>
    <span>Chronos — Guía de usuario</span>
    <span>Generada el {fecha}</span>
  </footer>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description='Genera la guía de usuario de Chronos.')
    parser.add_argument('--pdf', action='store_true', help='También convertir a PDF si es posible')
    args = parser.parse_args()

    DESTINO_DIR.mkdir(exist_ok=True)
    fecha = datetime.date.today().strftime('%d/%m/%Y')
    destino = DESTINO_DIR / 'Guia_Chronos.html'
    destino.write_text(html_manual(fecha), encoding='utf-8')
    print(f'HTML generado: {destino}')

    if not args.pdf:
        return

    pdf = DESTINO_DIR / 'Guia_Chronos.pdf'
    convertido = False

    try:
        from weasyprint import HTML  # type: ignore
        HTML(filename=str(destino)).write_pdf(str(pdf))
        convertido = True
    except Exception:
        pass

    if not convertido:
        for binario, argumentos in (
            ('google-chrome', ['--headless', '--disable-gpu', '--no-pdf-header-footer']),
            ('chromium', ['--headless', '--disable-gpu', '--no-pdf-header-footer']),
            ('chromium-browser', ['--headless', '--disable-gpu', '--no-pdf-header-footer']),
        ):
            if shutil.which(binario):
                subprocess.run([binario, *argumentos, f'--print-to-pdf={pdf}', destino.as_uri()],
                               check=False, capture_output=True)
                convertido = pdf.exists()
                break

    if convertido:
        print(f'PDF generado: {pdf}')
    else:
        print('No se pudo generar el PDF (falta weasyprint o un navegador headless).')
        print('El HTML ya está listo: abrilo en el navegador y usá "Imprimir → Guardar como PDF".')
        sys.exit(0)


if __name__ == '__main__':
    main()
