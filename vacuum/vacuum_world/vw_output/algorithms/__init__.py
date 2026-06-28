from algorithms.uninformed import BFSVacuum, DFSVacuum
from algorithms.informed import GBFSVacuum, AStarVacuum
from algorithms.local_search import HillClimbingVacuum, SimAnnealVacuum
from algorithms.csp import BacktrackingVacuum, ForwardCheckingVacuum
from algorithms.complex_enviroment import BFSUnknown, PartialVacuum
from algorithms.adversarial import MinimaxVacuum, AlphaBetaVacuum

ALGORITHMS = {
    "BFS":                      BFSVacuum,
    "DFS":                      DFSVacuum,
    "GBFS (Greedy)":            GBFSVacuum,
    "A*":                       AStarVacuum,
    "Hill Climbing":            HillClimbingVacuum,
    "Simulated Annealing":      SimAnnealVacuum,
    "Backtracking":             BacktrackingVacuum,
    "Forward Checking":         ForwardCheckingVacuum,
    "Unknown - BFS":            BFSUnknown,
    "Partial Observable (R=2)": PartialVacuum,
    "Minimax":                  MinimaxVacuum,
    "Alpha-Beta":               AlphaBetaVacuum,
}

EXPLORATION_ALGOS = {"Unknown - BFS", "Partial Observable (R=2)"}
ADVERSARIAL_ALGOS = {"Minimax", "Alpha-Beta"}
DUAL_ALGOS        = {"Unknown - BFS", "Partial Observable (R=2)"}
