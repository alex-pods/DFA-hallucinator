from automata import *
from collections import deque

class ParsedAnswer:
    start_states = []
    states = []
    alphabet = []
    finish_states = []
    def __init__(self, start_states, states, alphabet, finish_states) :
        self.start_states = start_states
        self.states = states
        self.alphabet = alphabet
        self.finish_states = finish_states
    def __str__(self) :
        str_repr = "Входящие состояния: " + str([i.state_id for i in self.start_states]) + "\n"
        str_repr = str_repr + "Выходящие состояния: " + str([i.state_id for i in self.finish_states])  + "\n"
        str_repr = str_repr + "Алфавит: " + str(self.alphabet) + "\n"
        str_repr = str_repr + "Все состояния:\n" + "\n".join([str(i) for i in self.states]) + "\n"
        return str_repr


def parse_answer(answer : str) -> ParsedAnswer | str:
    parts = answer.split("\n")
    if len(parts) < 4 :
        return "format not matching"

    try:
        num_states = int(parts[0])
    except ValueError:
        return "format not matching"

    if num_states <= 0 :
        return "impossible state count"

    states = []
    for i in range(0, num_states) :
        states.append(NFAState(i, {}))

    try:
        num_letters = int(parts[1])
    except ValueError:
        return "format not matching"

    if num_letters < 0:
        return "impossible alphabet size"

    alphabet = set()

    in_states_str = parts[2].split()
    out_states_str = parts[3].split()

    start_states = []

    for st_str in in_states_str :
        try:
            st_n = int(st_str)
        except ValueError:
            return "format not matching"
        if num_states-1 < st_n or st_n < 0  :
            return "non existing state"
        start_states.append(states[st_n])

    finish_states = []

    for st_str in out_states_str :
        try:
            st_n = int(st_str)
        except ValueError:
            return "format not matching"

        if num_states-1 < st_n or st_n < 0 :
            return "non existing state"

        finish_states.append(states[st_n])

    for i in range(4, len(parts)) :

        if not parts[i].strip():
            continue

        st_parts = parts[i].split()
        if len(st_parts) != 3 or len(st_parts[1]) != 1:
            return "format not matching"
        alphabet.add(st_parts[1])
        if len(alphabet) > num_letters :
            return "more letters than specified"

        try:
            in_state_ind = int(st_parts[0])
        except ValueError:
            return "format not matching"
        if not 0 <= in_state_ind < num_states:
            return "non existing state"

        try:
            out_state_ind = int(st_parts[2])
        except ValueError:
            return "format not matching"
        if not 0 <= out_state_ind < num_states:
            return "non existing state"

        states[in_state_ind].add_transition(st_parts[1], states[out_state_ind])

    ans = ParsedAnswer(start_states, states, alphabet, finish_states)

    return ans




def nfa_to_dfa(nfa : NFA) -> DFA :

    nfa_start_states = nfa.start_states
    nfa_finish_states = nfa.finish_states
    dfa_finish_states = []

    dfa_start_state = State(0, {})

    if any(st in nfa_finish_states for st in nfa_start_states):
        dfa_finish_states.append(dfa_start_state)

    states = {frozenset(nfa_start_states) : dfa_start_state}

    alphabet = nfa.alphabet

    waiting_states = deque()
    waiting_states.append(nfa_start_states)

    while len(waiting_states) > 0 :
        cur_states = waiting_states.popleft()
        for letter in alphabet :
            next_states = set()

            for st in cur_states :
                next_states.update(st.next(letter))

            if frozenset(next_states) in states :
                states[frozenset(cur_states)].add_transition(letter, states[frozenset(next_states)])
            else :
                new_state = State(len(states),{})
                if any((element in next_states) for element in nfa_finish_states) :
                    dfa_finish_states.append(new_state)

                states[frozenset(next_states)] = new_state
                waiting_states.append(next_states)

                states[frozenset(cur_states)].add_transition(letter, new_state)
    dfa = DFA(dfa_start_state, alphabet, dfa_finish_states)
    dfa.states = list(states.values())
    dfa.total_states = len(states)
    return dfa

def minimize_dfa(dfa : DFA) -> DFA :
    reachable = {dfa.start_state}
    waiting_states = deque([dfa.start_state])

    while waiting_states:
        cur_state = waiting_states.popleft()

        for letter in dfa.alphabet:
            next_state = cur_state.next(letter)

            if next_state is not None and next_state not in reachable:
                reachable.add(next_state)
                waiting_states.append(next_state)
    finish_set = set(dfa.finish_states)

    not_finish_states = list(reachable - finish_set)
    finish_states = list(reachable & finish_set)
    groups = []
    if not_finish_states:
        groups.append(not_finish_states)
    if finish_states:
        groups.append(finish_states)

    state_group = {}
    for i, gr in enumerate(groups):
        for st in gr:
            state_group[st] = i

    alphabet = dfa.alphabet

    group_index = 0
    while group_index < len(groups) :

        gr = groups[group_index]
        subgroups = {}

        for st in gr :

            signature = []
            for letter in alphabet :
                next_state = st.next(letter)
                signature.append(state_group[next_state])

            signature = tuple(signature)
            subgroups.setdefault(signature, []).append(st)

        if len(subgroups) > 1:
            k, v = subgroups.popitem()
            groups[group_index] = v

            for (key, value) in subgroups.items():
                groups.append(value)
                ind = len(groups) - 1
                for s in value:
                    state_group[s] = ind

            group_index = 0

        else:
            group_index += 1


    new_states = []
    for i in range(len(groups)) :
        new_states.append(State(i, {}))
    new_finish_states = []

    for i, gr in enumerate(groups) :
        r = gr[0]
        if r in dfa.finish_states :
            new_finish_states.append(new_states[i])

        for letter in alphabet :
            old_next_state = r.next(letter)
            next_group_index = state_group[old_next_state]

            new_states[i].add_transition(
                letter,
                new_states[next_group_index]
            )

    new_start_state  = new_states[state_group[dfa.start_state]]

    minimized_dfa = DFA(
        new_start_state,
        alphabet,
         new_finish_states
    )

    minimized_dfa.states = new_states
    minimized_dfa.total_states = len(new_states)

    return minimized_dfa

def equivalent_dfa(first: DFA, second: DFA) -> bool :
    start_first, start_second = first.start_state, second.start_state
    if set(first.alphabet) != set(second.alphabet) :
        return False
    alphabet = first.alphabet
    waiting_states = deque([(start_first, start_second)])
    visited = {(start_first, start_second)}

    while len(waiting_states) > 0 :
        first_state, second_state = waiting_states.popleft()

        if (first_state in first.finish_states) != (second_state in second.finish_states) :
            return False

        for letter in alphabet :
            next_pair = (
                first_state.next(letter),
                second_state.next(letter)
            )

            if next_pair not in visited :
                visited.add(next_pair)
                waiting_states.append(next_pair)
    return True



