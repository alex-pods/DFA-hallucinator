from lab.automata import NFAState

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


