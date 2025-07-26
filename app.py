import pandas as pd
import matplotlib.pyplot as plt
import os
from flask import Flask, request, render_template, jsonify, send_from_directory
from datetime import datetime # ¡Asegúrate de que esta importación esté aquí!
import numpy as np # Necesario para cálculos numéricos
import shutil # Para limpiar la carpeta de uploads

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GRAPH_FOLDER'] = 'graficos_pozos'

# Asegurarse de que las carpetas existan al iniciar la aplicación
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GRAPH_FOLDER'], exist_ok=True)

# --- Configuración de estilo de gráficos (del script original) ---
plt.style.use('seaborn-v0_8-darkgrid')

# --- Funciones de tu script original, adaptadas para ser llamadas internamente ---

def obtener_columnas_semestrales(columnas):
    """Detecta columnas semestrales dinámicamente."""
    return [col for col in columnas if col.startswith('Caudal') and '-' in col]

def calcular_porcentaje_caida(caudal_actual, promedio):
    """Calcula el % de caída de producción."""
    if promedio == 0:
        return 0.0
    return round(((promedio - caudal_actual) / promedio) * 100, 2)

def graficar_historial(pozo, campo, historico, caudal_actual, promedio_historico, caudal_inicial, nombre_archivo):
    """Genera gráfico del pozo con proyección."""
    fig, ax = plt.subplots(figsize=(12, 7)) # Aumentar tamaño para proyección
    
    # Datos históricos
    # Las claves del diccionario 'historico' deben ser strings para el eje X
    fechas = list(historico.keys())
    valores = list(historico.values())

    # Asegurarse de que el último punto histórico sea el Caudal Actual si no hay más fechas
    if not fechas or (fechas and fechas[-1] != "Caudal Actual"):
        # Intentamos derivar el nombre del siguiente semestre si hay fechas históricas
        next_sem_label = "Actual"
        if fechas:
            ultimo_semestre_str = fechas[-1].replace('Caudal ', '')
            try:
                s, y = ultimo_semestre_str.split('-')
                s_num = int(s.replace('S', ''))
                y_num = int(y)
                if s_num == 1:
                    next_sem_label = f"S2-{y_num}"
                else:
                    next_sem_label = f"S1-{y_num + 1}"
            except ValueError:
                next_sem_label = "Actual" # Fallback si el formato no es el esperado
        
        fechas_completas = fechas + [next_sem_label]
        valores_completos = valores + [caudal_actual]
    else:
        fechas_completas = fechas
        valores_completos = valores

    # Graficar datos históricos y actual
    ax.plot(fechas_completas, valores_completos, marker='o', color='royalblue', label='Caudal histórico/Actual')
    ax.axhline(y=caudal_actual, color='red', linestyle='--', label='Caudal Actual')
    
    # Umbral del 20% de caída respecto al CAUDAL INICIAL
    umbral_20_porciento_inicial = caudal_inicial * (1 - 0.20)
    ax.axhline(y=umbral_20_porciento_inicial, color='green', linestyle=':', label='Umbral -20% Caída (Respecto a Caudal Inicial)')

    # --- Proyección Lineal ---
    tasa_declinacion = 0
    if len(valores_completos) >= 2:
        # Usar los dos últimos puntos para una proyección simple
        ultima_val = valores_completos[-1]
        penultima_val = valores_completos[-2]
        tasa_declinacion = (penultima_val - ultima_val)
        if tasa_declinacion <= 0: # Si no hay caída o hay aumento
            # Usar la diferencia entre promedio y actual como tasa si no hay otra tendencia de caída clara
            tasa_declinacion = (promedio_historico - caudal_actual) 
            if tasa_declinacion <=0:
                tasa_declinacion = 5 # Pequeña declinación por defecto si no hay tendencia clara
    elif len(valores_completos) == 1: # Si solo hay un punto (el actual), usamos la diferencia con el promedio
        tasa_declinacion = (promedio_historico - caudal_actual)
        if tasa_declinacion <=0:
            tasa_declinacion = 5 # Pequeña declinación por defecto

    proyeccion_fechas = []
    proyeccion_valores = []
    
    ultimo_caudal = caudal_actual
    num_semestres_proyeccion = 5 
    
    # Determinar el último semestre conocido para continuar la proyección
    ultimo_semestre_conocido = fechas_completas[-1]
    
    ultimo_año = 0
    ultimo_semestre_tipo = ""

    if "S" in str(ultimo_semestre_conocido) and "-" in str(ultimo_semestre_conocido):
        try:
            sem_parte, año_parte = str(ultimo_semestre_conocido).replace('Caudal ', '').split('-')
            ultimo_semestre_tipo = sem_parte 
            ultimo_año = int(año_parte)
        except ValueError:
            # Fallback si el formato no es el esperado
            current_year = datetime.now().year
            current_month = datetime.now().month
            ultimo_semestre_tipo = "S1" if current_month <= 6 else "S2"
            ultimo_año = current_year
    else: 
        current_year = datetime.now().year
        current_month = datetime.now().month
        ultimo_semestre_tipo = "S1" if current_month <= 6 else "S2"
        ultimo_año = current_year

    for i in range(1, num_semestres_proyeccion + 1):
        if ultimo_semestre_tipo == "S1":
            siguiente_semestre_base = f"S2-{ultimo_año}"
            ultimo_semestre_tipo = "S2"
        else: # Si es S2
            ultimo_año += 1
            siguiente_semestre_base = f"S1-{ultimo_año}"
            ultimo_semestre_tipo = "S1"

        proyeccion_fechas.append(siguiente_semestre_base)
        
        proyectado_caudal = ultimo_caudal - tasa_declinacion
        if proyectado_caudal < 0:
            proyectado_caudal = 0
            proyeccion_valores.append(proyectado_caudal)
            break  
        proyeccion_valores.append(proyectado_caudal)
        ultimo_caudal = proyectado_caudal

        if proyectado_caudal <= umbral_20_porciento_inicial:
            break

    todas_fechas = fechas_completas + proyeccion_fechas
    todos_valores = valores_completos + proyeccion_valores

    ax.plot(todas_fechas, todos_valores, marker='x', linestyle='--', color='orange', label='Proyección lineal')

    for i, val in enumerate(todos_valores[len(fechas_completas):]): 
        ax.text(proyeccion_fechas[i], val, f'{val:.1f}', fontsize=8, ha='center', va='bottom', color='orange')

    ax.set_title(f'Pozo: {pozo} | Campo: {campo}', fontsize=14)
    ax.set_xlabel('Semestre')
    ax.set_ylabel('Caudal (l/s)')
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(nombre_archivo)
    plt.close()

def run_analysis(filepath):
    """
    Ejecuta el análisis de producción de pozos.
    Retorna una lista de pozos críticos y una lista de rutas a los gráficos generados.
    """
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        return {"error": f"Error al leer el archivo Excel: {e}"}, []

    columnas_semestrales = obtener_columnas_semestrales(df.columns)
    
    if not columnas_semestrales:
        # Advertencia: No se encontraron columnas semestrales, el promedio histórico será 0.
        df['Promedio Histórico'] = 0.0
    else:
        df['Promedio Histórico'] = df[columnas_semestrales].mean(axis=1)
    
    # NUEVA VERIFICACIÓN: 'Caudal Inicial' y 'Caudal Actual'
    if 'Caudal Inicial' not in df.columns:
        return {"error": "La columna 'Caudal Inicial' no se encontró en el archivo Excel. Es necesaria para la proyección."}, []
    if 'Caudal Actual' not in df.columns:
        return {"error": "La columna 'Caudal Actual' no se encontró en el archivo Excel. Asegúrate de que exista y esté correctamente escrita."}, []

    df['% Caída'] = df.apply(lambda x: calcular_porcentaje_caida(x['Caudal Actual'], x['Promedio Histórico']), axis=1)
    df['Estado'] = df['% Caída'].apply(lambda x: 'Crítico' if x > 20 else 'Estable')

    pozos_criticos = df[df['Estado'] == 'Crítico']
    
    # Limpiar la carpeta de gráficos antes de generar nuevos
    for filename in os.listdir(app.config['GRAPH_FOLDER']):
        file_path = os.path.join(app.config['GRAPH_FOLDER'], filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Fallo al borrar {file_path}. Razón: {e}')

    graph_paths = []
    if pozos_criticos.empty:
        return {"message": "No se encontraron pozos con una caída de producción superior al 20%. No se generarán gráficos."}, []
    else:
        for _, fila in pozos_criticos.iterrows():
            historico_data = fila[columnas_semestrales].dropna() # .dropna() para ignorar NaN en históricos
            
            if not historico_data.empty:
                historico = historico_data.to_dict()
                
                pozo_nombre = str(fila['Nombre del Pozo']) if pd.notna(fila['Nombre del Pozo']) else 'Desconocido'
                campo_nombre = str(fila['Campo']) if pd.notna(fila['Campo']) else 'Desconocido'
                
                pozo_nombre_saneado = pozo_nombre.replace(' ', '_').replace('/', '_').replace('\\', '_')
                nombre_archivo_base = f"Pozo_{pozo_nombre_saneado}"
                
                graph_filename = f"{nombre_archivo_base}.png"
                nombre_archivo = os.path.join(app.config['GRAPH_FOLDER'], graph_filename)
                
                graficar_historial(
                    pozo_nombre, 
                    campo_nombre, 
                    historico, 
                    fila['Caudal Actual'], 
                    fila['Promedio Histórico'],
                    fila['Caudal Inicial'], # Nuevo argumento
                    nombre_archivo
                )
                graph_paths.append(graph_filename)
            else:
                print(f"Advertencia: No hay datos históricos válidos para el pozo: {fila.get('Nombre del Pozo', 'Desconocido')}. No se generó gráfico.")

    # Convertir los pozos_criticos a un formato que se pueda enviar como JSON
    # Selecciona solo las columnas que quieres mostrar en la tabla y exportar
    columnas_output = ['Nombre del Pozo', 'Campo', 'Caudal Inicial', 'Caudal Actual', 'Promedio Histórico', '% Caída', 'Estado']
    pozos_criticos_output = pozos_criticos[columnas_output].to_dict(orient='records')
    
    # Generar el archivo Excel de pozos críticos para descarga
    excel_criticos_filename = f"pozos_criticos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    excel_criticos_path = os.path.join(app.config['UPLOAD_FOLDER'], excel_criticos_filename) # Guardar temporalmente en uploads
    pozos_criticos[columnas_output].to_excel(excel_criticos_path, index=False)


    return {"pozos_criticos": pozos_criticos_output, "excel_criticos_filename": excel_criticos_filename}, graph_paths


# --- Rutas de Flask ---

@app.route('/')
def index():
    """Renderiza la página principal y pasa el año actual al template."""
    current_year = datetime.now().year # Obtener el año actual
    return render_template('index.html', year=current_year) # Pasa el año a la plantilla como 'year'

@app.route('/upload', methods=['POST'])
def upload_file():
    """Maneja la subida del archivo Excel y ejecuta el análisis."""
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró el archivo en la solicitud."}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún archivo."}), 400
    
    if file and file.filename.endswith('.xlsx'):
        filename = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        results, graph_paths = run_analysis(filepath)
        
        # Opcional: Eliminar el archivo Excel subido después del análisis si no se necesita
        # Comentado para depuración, pero puedes descomentarlo en producción si el archivo no se necesita persistente.
        # os.remove(filepath)

        if "error" in results:
            return jsonify(results), 400 # Devolver error si el análisis falló
        else:
            return jsonify({
                "success": True, 
                "results": results["pozos_criticos"], 
                "graph_paths": graph_paths,
                "excel_criticos_download": results["excel_criticos_filename"]
            }), 200
    else:
        return jsonify({"error": "Formato de archivo no permitido. Por favor, sube un archivo .xlsx"}), 400

@app.route('/graficos/<path:filename>')
def serve_graph(filename):
    """Sirve los archivos de gráficos PNG."""
    return send_from_directory(app.config['GRAPH_FOLDER'], filename)

@app.route('/download_excel/<filename>')
def download_excel(filename):
    """Permite la descarga del archivo Excel de pozos críticos."""
    # Asegúrate de que el archivo exista en la carpeta de uploads
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    else:
        return jsonify({"error": "Archivo no encontrado para descargar."}), 404


if __name__ == '__main__':
    # app.run(debug=True) # debug=True para desarrollo (recarga el servidor automáticamente)