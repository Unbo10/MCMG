# MCMG
Markov Chain-based Music Generator

## Descripción

Generador de música basada en un número arbitrario de composiciones musicales en formato .xml a partir de cadenas de Markov.

## Uso en cuadernos (notebooks)

1. **Instala el paquete en modo editable**  
   Desde la raíz del repositorio (donde está `pyproject.toml`), activa tu entorno virtual e instala:  
   ```bash
   pip install -e .
   ```
   Así podrás importar `mcmg` sin modificar `sys.path`.

2. **Selecciona el intérprete del notebook**  
   Usa el kernel asociado a tu venv (en VS Code: “Python: Select Interpreter”; en Jupyter clásico registra el kernel con `python -m ipykernel install --user --name mcmg-venv --display-name "mcmg (.venv)"`).

3. **Importa los módulos**  
   ```python
   from mcmg.parser import Parser
   from mcmg.instrument import Instrument
   ```
   (Opcional) Habilita autoreload para reflejar cambios sin reiniciar:  
   ```python
   %load_ext autoreload
   %autoreload 2
   ```

4. **Rutas personalizadas**  
   `Parser` acepta el parámetro `data_dir` para indicar dónde guardar/leer los `.xml` descomprimidos:  
   ```python
   parser = Parser("scores/MiTema.mxl", data_dir="mis_datos")
   ```

## Notas
- El atributo `text` da acceso a lo que hay en cada tag del `.xml`.

## Referencias y bibliografía
- https://www.researchgate.net/publication/353985934_Markov_Chains_for_Computer_Music_Generation (publicación guía)
- https://musetrainer.github.io/library/ repositorio con partituras de piano de composiciones en formato *musicxml* (`.mxl`).
