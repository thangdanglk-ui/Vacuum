"""
Adversarial Search — Alpha-Beta Pruning.
"""
from algorithms.adversarial.minimax import (
    _h, _passable, _evaluate, _AdversarialBase)
from map_generator import get_neighbors, GRID_ROWS, GRID_COLS


class AlphaBetaVacuum(_AdversarialBase):
    DEPTH = 5

    def _search(self, robot_pos, pet_pos, dust_set, battery,
                depth, is_max, alpha=-999999, beta=999999):
        if depth == 0 or not dust_set or battery <= 0:
            return _evaluate(robot_pos, pet_pos, dust_set, battery)

        if is_max:
            best = -999999
            moves = _passable(self.grid, robot_pos, self.rows, self.cols)
            if not moves:
                return _evaluate(robot_pos, pet_pos, dust_set, battery)
            moves = sorted(moves,
                           key=lambda nb: (0 if nb in dust_set else 1,
                                           min((_h(nb, d) for d in dust_set), default=0)))
            for nb in moves:
                new_dust = set(dust_set); new_dust.discard(nb)
                val = self._search(nb, pet_pos, new_dust, battery-1,
                                   depth-1, False, alpha, beta)
                best  = max(best, val)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best if best != -999999 else _evaluate(robot_pos, pet_pos, dust_set, battery)
        else:
            worst = 999999
            moves = _passable(self.grid, pet_pos, self.rows, self.cols)
            if not moves:
                return _evaluate(robot_pos, pet_pos, dust_set, battery)
            moves = sorted(moves, key=lambda nb: _h(nb, robot_pos))
            for nb in moves:
                val = self._search(robot_pos, nb, dust_set, battery,
                                   depth-1, True, alpha, beta)
                worst = min(worst, val)
                beta  = min(beta, worst)
                if beta <= alpha:
                    break
            return worst if worst != 999999 else _evaluate(robot_pos, pet_pos, dust_set, battery)

    def _move_pet(self):
        """Alpha-Beta pet: chặn target robot đang hướng đến."""
        from algorithms.pathfinder import astar_path
        if not self.dust_remaining:
            self._pet_step_toward(self.dock)
            return

        robot_target = getattr(self, '_current_target', None)
        if robot_target is None or robot_target not in self.dust_remaining:
            robot_target = min(self.dust_remaining, key=lambda d: _h(self.pos, d))

        path_r, _ = astar_path(self.grid, self.pos, robot_target, get_neighbors)

        if len(path_r) < 2:
            self._pet_step_toward(robot_target)
            return

        best_block = path_r[-1]
        for step, candidate in enumerate(path_r[1:], 1):
            if _h(self.pet_pos, candidate) <= step:
                best_block = candidate

        self._pet_step_toward(best_block)
