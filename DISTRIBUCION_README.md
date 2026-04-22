# 🏪 Motor de Distribución Retail — Calzado & Apparel

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org/)
[![Retail](https://img.shields.io/badge/Industria-Retail_Outlet-orange?style=flat-square)]()
[![Impacto](https://img.shields.io/badge/Reducción_de_tiempo-80%25-brightgreen?style=flat-square)]()

> **Automatización del proceso de distribución de inventario a nivel talla × tienda para Retail Outlet.**  
> Redujo el tiempo de operación de **4–5 días a 1 día**, una reducción del **~80% en horas hombre**.

---

## 📌 Contexto del Problema

En la operación de un cliente Outlet, el proceso de distribución de mercancía involucraba:

1. **Machear** manualmente el archivo de solicitudes contra el stock disponible
2. **Calcular** la asignación a nivel talla por cada tienda
3. **Validar** que no se excediera el stock disponible
4. **Cargar** el resultado al sistema ERP

Este flujo tomaba entre **4 y 5 días laborales** por ciclo de distribución, con alta exposición a errores humanos en el prorrateo de tallas.

---

## ⚡ Solución

Dos scripts Python que automatizan el proceso completo en minutos:

| Script | Categoría | Lógica de tallas |
|---|---|---|
| `Distribucion_calzado.py` | Footwear (numérico) | Orden numérico + curva de demanda opcional |
| `Distribucion_apparel.py` | Textil / Apparel | Orden por tabla custom (ECH → CH → MED → GDE → EGDE...) |

Ambos scripts comparten el mismo núcleo algorítmico y generan los mismos archivos de salida y auditoría.

---

## 🧠 Algoritmos Implementados

El motor de distribución resuelve un problema de **asignación entera con márgenes duales** (tienda × talla):

### 1. `largest_remainder_round`
Redondeo entero que garantiza que la suma total asignada sea exactamente igual al stock disponible. Distribuye los residuos de fracción de mayor a menor, respetando topes por talla.

### 2. `waterfill_with_caps`
Algoritmo iterativo tipo *waterfilling* que asigna unidades proporcionalmente entre tallas, respetando los topes de stock. Si una talla se satura, el remanente se redistribuye entre las tallas con capacidad restante.

### 3. `build_integer_matrix_with_margins`
Construye una **matriz entera con márgenes fijos**: los totales por fila (tiendas) y por columna (tallas) deben coincidir exactamente con los targets. Usa el método de la fracción más alta (*Largest Remainder*) para la asignación de residuos.

> En conjunto, estos tres algoritmos garantizan que **ninguna tienda recibe más de lo que solicitó** y que **ninguna talla es sobregirada más allá del stock disponible**, cumpliendo al mismo tiempo que la suma total sea exacta.

---

## 📁 Estructura del Proyecto

```
distribucion-retail/
├── Distribucion_calzado.py     # Motor de distribución — Footwear
├── Distribucion_apparel.py     # Motor de distribución — Apparel / Textil
├── README.md
│
├── inputs/  (no incluidos — datos confidenciales)
│   ├── Solicitudes.csv         # Tienda | Modelo | Corrida solicitada
│   ├── Stock.csv               # Modelo | Talla | Stock disponible
│   └── Curva.csv               # (opcional) Modelo | Talla | Peso de curva
│
└── outputs/  (generados al ejecutar)
    ├── distribucion_footwear.csv
    ├── distribucion_apparel.csv
    ├── auditoria_resumen_*.csv
    ├── auditoria_tiendas_*.csv
    ├── auditoria_tallas_*.csv
    └── modelos_fallidos_*.csv
```

---

## ▶️ Cómo Usar

### Requisitos
```bash
pip install pandas numpy
```

### 1. Prepara tus archivos de entrada

**`Solicitudes.csv`** — Lo que cada tienda solicita por modelo:
```
Tienda,Modelo,Corrida
Outlet Norte,MODEL-001,24
Outlet Sur,MODEL-001,18
Outlet Centro,MODEL-002,30
```

**`Stock.csv`** — Disponibilidad por modelo y talla:
```
Modelo,Talla,Stock
MODEL-001,7,12
MODEL-001,7.5,20
MODEL-001,8,18
```

> Los nombres de columnas son **flexibles** — el script acepta sinónimos como `store`, `sku`, `size`, `qty`, `disponible`, etc.

### 2. Coloca los CSV en la misma carpeta que el script y ejecuta:

```bash
# Para calzado / footwear
python Distribucion_calzado.py

# Para apparel / textil
python Distribucion_apparel.py
```

### 3. Revisa los archivos de salida

El script genera automáticamente:

| Archivo | Contenido |
|---|---|
| `distribucion_*.csv` | Asignación final: Tienda / Modelo / Talla / Piezas asignadas |
| `auditoria_resumen_*.csv` | Por modelo: solicitado vs stock vs asignado |
| `auditoria_tiendas_*.csv` | Por tienda: solicitado vs asignado |
| `auditoria_tallas_*.csv` | Por talla: stock vs asignado |
| `modelos_fallidos_*.csv` | Modelos con error y motivo |

---

## ✅ Garantías del Algoritmo

- ✔️ Ninguna tienda recibe más unidades de las que solicitó
- ✔️ Ninguna talla es sobregirada más allá del stock disponible
- ✔️ La suma total asignada es exactamente entera (sin fracciones)
- ✔️ Si hay escasez, el corte se hace proporcionalmente entre tiendas
- ✔️ Modelos con error se registran en `modelos_fallidos.csv` sin detener el proceso

---

## 📊 Impacto Operativo

| Métrica | Antes | Después |
|---|---|---|
| Tiempo por ciclo de distribución | 4–5 días | ~1 día |
| Proceso | Manual en Excel | Automatizado en Python |
| Riesgo de error humano | Alto | Mínimo (validaciones automáticas) |
| Reducción de horas hombre | — | **~80%** |

---

## 👤 Autor

**Ángel** — Account Manager & Data Analytics Specialist  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Conectar-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/angel-jimenez-28696b255)
[![GitHub](https://img.shields.io/badge/GitHub-Angel--jl-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/Angel-jl)

---

## 📄 Licencia

MIT License — Libre para uso y adaptación con atribución.
