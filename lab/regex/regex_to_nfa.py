from lab.automata import NFA, NFAState

from lab.regex.generated.RegexParser import RegexParser
from lab.regex.generated.RegexVisitor import RegexVisitor
from lab.regex.regex_parser import parse_regex

class ThompsonVisitor(RegexVisitor) :
    def __init__(self) :
        self.states = []

    def new_state(self) -> NFAState :
        state = NFAState(len(self.states), {})
        self.states.append(state)
        return state

    def visitStart(self, ctx:RegexParser.StartContext) -> tuple[NFAState, NFAState] :
        return self.visit(ctx.expression())

    def visitAtom(self, ctx)-> tuple[NFAState, NFAState]:
        symbol = ctx.SYMBOL()
        if symbol is not None :
            start = self.new_state()
            finish = self.new_state()

            start.add_transition(symbol.getText(), finish)

            return start,finish

        return self.visit(ctx.expression())

    def visitConcatenation(self, ctx:RegexParser.ConcatenationContext) -> tuple[NFAState, NFAState]:
        parts = ctx.repetition()
        start, finish = self.visit(parts[0])
        for part in parts[1:] :
            new_start, new_finish = self.visit(part)

            finish.add_epsilon_transition(new_start)
            finish = new_finish
        return start, finish

    def visitExpression(self, ctx:RegexParser.ExpressionContext) -> tuple[NFAState, NFAState]:
        parts = ctx.concatenation()
        start,finish = self.visit(parts[0])

        for part in parts[1:] :
            next_start, next_finish = self.visit(part)

            new_start = self.new_state()
            new_finish = self.new_state()
            new_start.add_epsilon_transition(start)
            new_start.add_epsilon_transition(next_start)

            finish.add_epsilon_transition(new_finish)
            next_finish.add_epsilon_transition(new_finish)

            start = new_start
            finish = new_finish

        return start, finish

    def visitRepetition(self, ctx) -> tuple[NFAState, NFAState] :

        start, finish = self.visit(ctx.atom())

        if ctx.getChildCount() == 1:
            return start, finish

        new_start = self.new_state()
        new_finish = self.new_state()

        new_start.add_epsilon_transition(start)
        new_start.add_epsilon_transition(new_finish)

        finish.add_epsilon_transition(start)
        finish.add_epsilon_transition(new_finish)

        start = new_start
        finish = new_finish

        return start, finish


def regex_to_nfa(text : str, alphabet : list[str]) -> NFA | str :
    tree = parse_regex(text, alphabet)

    if isinstance(tree, str) :
        return tree

    visitor = ThompsonVisitor()
    start, finish = visitor.visit(tree)

    return NFA([start], alphabet, [finish])