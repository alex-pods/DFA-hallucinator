from automata import *

def build_dfa(alphabet : list[str], transitions : list[list[int]],
               finish_ids : list[int], start_id : int = 0) -> DFA :
    states = []
    for i in range(len(transitions)) :
        states.append(State(i, {}))

    for i, row in enumerate(transitions) :
        for j, letter in enumerate(alphabet) :
            states[i].add_transition(letter, states[row[j]])

    finish_states = []
    for state_id in finish_ids :
        finish_states.append(states[state_id])

    dfa = DFA(states[start_id], alphabet, finish_states)
    dfa.states = states
    dfa.total_states = len(states)

    return dfa

def build_basic() -> DFA :
    transitions = [
        [1, 2],
        [9, 3],
        [4, 9],
        [5, 9],
        [9, 6],
        [9, 7],
        [8, 9],
        [1, 9],
        [9, 2],
        [9, 9]
    ]

    return build_dfa(["0", "1"], transitions, [2,5])

def build_4th_symbol() -> DFA :
    transitions = [
        [0, 1],
        [2, 3],
        [4, 5],
        [6, 7],
        [8, 9],
        [10, 11],
        [12, 13],
        [14, 15],
        [0, 1],
        [2, 3],
        [4, 5],
        [6, 7],
        [8, 9],
        [10, 11],
        [12, 13],
        [14, 15]
    ]

    return build_dfa(["0", "1"], transitions, [8, 9, 10, 11, 12, 13, 14, 15])

def build_employer() -> DFA :
    alphabet = ["A", "M", "C", "S", "P", "B", "0", "1", "2", "3", "4", "5"]
    transitions = [
        # A   M   C   S   P   B   0   1   2   3   4   5
        [ 2,  2,  2,  1,  2,  2, 11, 11, 11, 11, 11, 11],
        [ 4,  4,  4,  4,  3,  4, 11, 11, 11, 11, 11, 11],
        [ 4,  4,  4,  4,  4,  4, 11, 11, 11, 11, 11, 11],
        [ 6,  6,  6,  6,  6,  5, 11, 11, 11, 11, 11, 11],
        [ 6,  6,  6,  6,  6,  6, 11, 11, 11, 11, 11, 11],
        [11, 11, 11, 11, 11, 11, 11,  7,  7,  7,  7,  7],
        [11, 11, 11, 11, 11, 11,  7,  7,  7,  7,  7,  7],
        [11, 11, 11, 11, 11, 11,  8,  8,  8,  8,  8,  8],
        [11, 11, 11, 11, 11, 11,  9,  9,  9,  9,  9,  9],
        [11, 11, 11, 11, 11, 11, 10, 10, 10, 10, 10, 10],
        [11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11],
        [11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]
    ]

    return build_dfa(alphabet, transitions, [10])

def build_intersection() -> DFA :
    transitions = [
        [3, 1],
        [6, 2],
        [8, 2],
        [10, 4],
        [10, 5],
        [10, 9],
        [10, 7],
        [10, 5],
        [10, 7],
        [10, 9],
        [10, 10]
    ]

    return build_dfa(["0", "1"], transitions, [7, 8, 9])

def build_abc_bca_cab() -> DFA :

    transitions = [
        [1, 3, 5],
        [7, 2, 7],
        [7, 7, 0],
        [7, 7, 4],
        [0, 7, 7],
        [6, 7, 7],
        [7, 0, 7],
        [7, 7, 7]
    ]
    return build_dfa(["a", "b", "c"], transitions, [0])

ground_truth_builders = {
    "basic": build_basic,
    "4th-symbol": build_4th_symbol,
    "employer": build_employer,
    "intersection": build_intersection,
    "abc-bca-cab": build_abc_bca_cab,
}