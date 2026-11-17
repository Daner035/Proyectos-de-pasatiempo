import sqlite3
import streamlit as st
import pandas as pd

# --- 1. CONFIGURACIÓN DE BASE DE DATOS (SQLite) ---
def init_db():
    conn = sqlite3.connect("raci_system.db")
    c = conn.cursor()
    
    # Tablas principales
    c.execute('''CREATE TABLE IF NOT EXISTS miembros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    rol_base TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cualidades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE)''')
                    
    # Relación Muchos-a-Muchos: Dominio del estudiante (1 a 5)
    c.execute('''CREATE TABLE IF NOT EXISTS miembro_cualidades (
                    miembro_id INTEGER,
                    cualidad_id INTEGER,
                    nivel INTEGER,
                    PRIMARY KEY (miembro_id, cualidad_id))''')

    # Seed inicial (datos de prueba si la BD está vacía)
    c.execute("SELECT COUNT(*) FROM miembros")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO cualidades (nombre) VALUES (?)", 
                      [("Programación",), ("Normalización BD",), ("Diagramación/UML",), ("Redacción Informes",)])
        
        c.executemany("INSERT INTO miembros (nombre, rol_base) VALUES (?, ?)", 
                      [("Diego", "Líder Técnico"), ("Pedro", "Analista"), ("Eduardo", "Desarrollador"), ("Ixela", "Documentación")])
        
        # Asignar niveles (id_miembro, id_cualidad, nivel 1-5)
        niveles = [
            (1, 1, 5), (1, 2, 5), (1, 3, 4), (1, 4, 3), # Diego
            (2, 1, 3), (2, 2, 4), (2, 3, 5), (2, 4, 4), # Pedro
            (3, 1, 5), (3, 2, 3), (3, 3, 3), (3, 4, 2), # Eduardo
            (4, 1, 2), (4, 2, 3), (4, 3, 4), (4, 4, 5), # Ixela
        ]
        c.executemany("INSERT INTO miembro_cualidades VALUES (?, ?, ?)", niveles)
        conn.commit()
    conn.close()

# --- 2. MOTOR DE CÁLCULO RACI POR PROBABILIDAD ---
def calcular_raci(pesos_tarea):
    conn = sqlite3.connect("raci_system.db")
    miembros = pd.read_sql_query("SELECT * FROM miembros", conn)
    cualidades = pd.read_sql_query("SELECT * FROM cualidades", conn)
    mc = pd.read_sql_query("SELECT * FROM miembro_cualidades", conn)
    conn.close()

    resultados = []
    peso_total = sum(pesos_tarea.values())
    
    for _, m in miembros.iterrows():
        puntaje = 0
        for cid, peso in pesos_tarea.items():
            if peso > 0:
                fila = mc[(mc["miembro_id"] == m["id"]) & (mc["cualidad_id"] == cid)]
                nivel = fila["nivel"].values[0] if not fila.empty else 0
                puntaje += (nivel / 5.0) * peso
        
        afinidad = round((puntaje / peso_total) * 100, 1) if peso_total > 0 else 0
        resultados.append({"Miembro": m["nombre"], "Rol Base": m["rol_base"], "Afinidad (%)": afinidad})

    df_res = pd.DataFrame(resultados).sort_values(by="Afinidad (%)", ascending=False).reset_index(drop=True)
    
    # Asignación automática de Roles RACI según ranking de afinidad
    roles = []
    for idx in range(len(df_res)):
        if idx == 0:
            roles.append("R (Responsible - Ejecuta)")
        elif idx == 1:
            roles.append("A (Accountable - Aprueba)")
        elif idx == 2:
            roles.append("C (Consulted - Apoya)")
        else:
            roles.append("I (Informed - Notificado)")
            
    df_res["Rol RACI Sugerido"] = roles
    return df_res

# --- 3. INTERFAZ DEL DASHBOARD ---
st.set_page_config(page_title="RACI Smart Dashboard", layout="wide")
init_db()

st.title("📊 Dashboard de Asignación RACI Probabilística")
st.markdown("Prototipo v0.1 - Asignación automática basada en competencias técnicas del equipo.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Definir Nueva Actividad")
    nombre_tarea = st.text_input("Nombre de la actividad:", "Normalización de Base de Datos y Diagrama ER")
    
    st.write("**Peso de competencias requeridas (0 a 10):**")
    conn = sqlite3.connect("raci_system.db")
    cualidades_df = pd.read_sql_query("SELECT * FROM cualidades", conn)
    conn.close()
    
    pesos = {}
    for _, row in cualidades_df.iterrows():
        pesos[row["id"]] = st.slider(row["nombre"], 0, 10, 5 if row["id"] in [2, 3] else 1)

with col2:
    st.subheader(f"2. Matriz RACI Calculada: *{nombre_tarea}*")
    df_raci = calcular_raci(pesos)
    
    # Mostrar tabla de resultados con el nuevo formato de ancho
    st.dataframe(df_raci, width='stretch')
    
    # Gráfico de barras de afinidad
    st.subheader("Probabilidad de Afinidad por Estudiante")
    st.bar_chart(df_raci.set_index("Miembro")["Afinidad (%)"])