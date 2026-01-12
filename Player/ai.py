# ai.py
# IA base para el Snake
# Este archivo SOLO define la estructura mínima que el juego espera.
# NO hay lógica implementada a propósito.

class PlayerAI:
    def __init__(self):
        """
        Inicializa el estado interno de la IA.

        Aquí deberías:
        - Definir variables internas (modo, dificultad, contadores, etc.)
        - Inicializar estructuras para debug (mapas de coste, caminos, etc.)
        """

        # Nivel de dificultad actual (0–9)
        self.difficulty = 0

        # Nivel de riesgo que se muestra en el HUD
        # Puede ser un número que tú calcules dinámicamente
        self.risk = 0

        # Mapa de pesos/costes por celda para debug visual
        # Formato esperado: {(x, y): coste}
        self.debug_weight_map = {}

        # Camino actual que la IA planea seguir (para debug)
        # Formato: [(x1, y1), (x2, y2), ...]
        self.debug_path = []

    def get_next_move(self, juego):
        """
        MÉTODO MÁS IMPORTANTE.
        El juego llama a este método para pedir la siguiente dirección.

        Recibe el objeto 'juego', desde el que puedes acceder a:
        - juego.snake.cuerpo
        - juego.snake.direccion
        - juego.frutas
        - juego.minas
        - juego.casillas_x / casillas_y
        - juego.velocidad
        - etc.

        Debes devolver UNA de estas direcciones:
            (-1, 0)  -> izquierda
            (1, 0)   -> derecha
            (0, -1)  -> arriba
            (0, 1)   -> abajo

        O devolver None si no quieres cambiar la dirección.
        """

        # Aquí deberías:
        # - Analizar el estado actual del juego
        # - Decidir hacia dónde moverte
        # - Evitar choques, minas, paredes, etc.
        # - (Opcional) calcular caminos con BFS / A* / heurísticas

        # NO IMPLEMENTAR LÓGICA AQUÍ TODAVÍA
        return None

    def finalize_game(self, won: bool):
        """
        Se llama cuando la partida termina (victoria o game over).

        Parámetro:
        - won = True  -> victoria
        - won = False -> derrota

        Aquí deberías:
        - Resetear estados internos si hace falta
        - Guardar estadísticas
        - Limpiar mapas de debug
        - Preparar la IA para la siguiente partida
        """

        # Ejemplos de cosas que podrías hacer:
        # - Vaciar self.debug_weight_map
        # - Vaciar self.debug_path
        # - Resetear contadores internos
        # - Ajustar dificultad automáticamente según resultado

        self.debug_weight_map = {}
        self.debug_path = {}

        pass

    def set_difficulty(self, level: int):
        """
        Se llama cada vez que el usuario pulsa una tecla 0–9
        o desde triggers externos.

        Aquí deberías:
        - Guardar el nivel de dificultad
        - Ajustar parámetros internos según el nivel
          (agresividad, riesgo, profundidad de búsqueda, etc.)
        """

        self.difficulty = level

        # Ejemplo de cosas que podrías hacer (NO IMPLEMENTAR AQUÍ):
        # - Cambiar pesos de heurística
        # - Activar/desactivar evitar minas
        # - Ajustar tolerancia al riesgo
        # - Cambiar frecuencia de recalcular caminos

        pass


