class State:
    state_id = 0
    transitions = {}

    def __init__(self, state_id : int, transitions: dict) :
        self.state_id = state_id
        self.transitions = transitions

    def __str__(self):
        str_repr = "State id : " + str(self.state_id) + "\n" + "Transitions :" + "\n"
        for key,val in self.transitions.items() :
            str_repr += str(self.state_id) + " ---(" + key + ")--> " + str(val.state_id) + "\n"
        return str_repr

    def next(self, letter : str) -> "State | None":
        assert len(letter) == 1
        if letter in self.transitions :
            return self.transitions[letter]
        else :
            return None
    def add_transition(self, letter : str, out : "State") :
        self.transitions[letter] = out

class NFAState(State):

    def next(self, letter: str) -> list["NFAState"]:
        assert len(letter) == 1
        if letter in self.transitions :
            return self.transitions[letter]
        else :
            return []

    def add_transition(self, letter : str, out : "NFAState"):
        self.transitions.setdefault(letter, []).append(out)

    def __str__(self):
        str_repr = "State id : " + str(self.state_id) + "\n" + "Transitions :" + "\n"
        for key, val in self.transitions.items():
            for v in val :
                str_repr += str(self.state_id) + " ---(" + key + ")--> " + str(v.state_id) + "\n"
        return str_repr


class DFA:
    start_state = None
    finish_states = []
    alphabet = []
    states = []
    total_states = 0

    def __init__(self, start_state, alphabet, finish_states) :
        self.start_state = start_state
        self.alphabet = alphabet
        self.finish_states = finish_states

    def compute(self, word: str) -> str :
        cur_state = self.start_state
        for letter in word :
            tmp_state = cur_state.next(letter)
            if tmp_state is None :
                return "deny"
            cur_state = tmp_state
        if cur_state in self.finish_states :
            return "accept"
        return "deny"

class NFA:
    start_states = []
    finish_states = []
    alphabet = []
    def __init__(self, start_states, alphabet, finish_states) :
        self.start_states = start_states
        self.alphabet = alphabet
        self.finish_states = finish_states

    def compute(self, word: str) -> str :
        cur_states = self.start_states

        for letter in word :
            tmp_states = set()
            for st in cur_states :
                tmp_states.update(st.next(letter))
            cur_states = tmp_states

        if any((element in cur_states) for element in self.finish_states) :
            return "accept"
        return "deny"
