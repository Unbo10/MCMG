# MCMG
Markov Chain-based Music Generator

## Descripción

Se desarrollará un generador de música *clásica, ...* aleatorio (? puede ser libre también, es decir, que inicie con una secuencia dada por el usuario, o por un autor de su elección con el que se elija qué cadenas utilizar) basado en una cadena de Markov (Director) que controle cuándo se les permite tocar a las demás, que serán algunos entre *piano, violín (?), trompeta (?), saxofón (?), ...*.

La cadena de Markov asociada a cada instrumento tendrá tantos estados como combinaciones de (combinaciones de notas (?), duración de la nota)[^1] hayan en todas las canciones con las que se definirá la matriz de transición de esta.

[^1]: Siguiendo a [Markov Chain for Computer Music Generation](https://www.researchgate.net/publication/353985934_Markov_Chains_for_Computer_Music_Generation).

## Ruta de acción
1. Obtener las canciones en formato MIDI.
2. Crear un *parser* para pasar de MIDI a tupla de un instrumento en particular ([combinaciones de notas], duración de la combinación).
3. Separar las combinaciones que corresponden a cada instrumento.
4. 'Entrenar' cada cadena de Markov asociada a un instrumento, es decir, hallar su matriz de transición utilizando el *parser* y las canciones en que se use el instrumento para determinar la frecuencia con que cada combinación aparece en la canción.
5. 'Entrenar' a los directores, es decir, una cadena de Markov con tantos estados como instrumentos se vayan a utilizar y un extra que será silencio. Por cada pentagrama dividido en 8 (?), se harán arreglos binarios de cada instrumento con los que los directores sepan cuándo puede tocar y cuándo no.
6. Diseñar una manera de simular las cadenas. Debe producir sonido.
7. Diseñar una UI para la simulación (?).

## Ayudas
- Librería `pretty_midi`

## Ideas
- Que el Director controle el tempo y la clave o tonalidad.
- Posible extra: determinar dentro de qué estado de ánimo se clasifica la pieza generada.
- La mayoría podría incorporarse dentro de una librería.
- Agrupar las piezas por movimientos, épocas o autores.
- Absorbentes (?). Recurrentes (?).
- Volumen para cada estado de cada instrumento.

## Notas
- El atributo `text` da acceso a lo que hay en cada tag del `.xml`.

## Referencias y bibliografía
- https://www.researchgate.net/publication/353985934_Markov_Chains_for_Computer_Music_Generation (publicación guía)
- https://musetrainer.github.io/library/ repositorio con partituras de piano de composiciones en formato *musicxml* (`.mxl`).

