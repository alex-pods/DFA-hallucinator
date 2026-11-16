"""Старые и новые тесты проекта. Запуск из корня:
python -m unittest lab.tests.test_project -q

Генерируемые случаи имеют отдельные имена в unittest, фиксированные seed.
Сеть запрещена; ответы API подменяются. Файлы пишутся только во временные папки.
Проверки новых требований намеренно падают, если изменения ещё не внесены.
"""
import importlib
import io
import os
import re
import sys
import tempfile
import unittest
from collections import deque
from contextlib import redirect_stdout
from itertools import product
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from lab.automata import State, NFAState, DFA, NFA, algorithms
from lab.experiments import answer_parser
from lab.experiments import storage as fileIO


def make_dfa(transitions, finish_ids, alphabet=None, start_id=0):
    if alphabet is None:
        alphabet = ["0", "1"]
    states = []
    for i in range(len(transitions)):
        states.append(State(i, {}))
    for i, row in enumerate(transitions):
        for j, letter in enumerate(alphabet):
            if row[j] is not None:
                states[i].add_transition(letter, states[row[j]])
    dfa = DFA(states[start_id], list(alphabet), [states[i] for i in finish_ids])
    dfa.states = states
    dfa.total_states = len(states)
    return dfa


def make_nfa(transitions, start_ids, finish_ids, alphabet=None):
    if alphabet is None:
        alphabet = ["0", "1"]
    states = []
    for i in range(len(transitions)):
        states.append(NFAState(i, {}))
    for i, row in enumerate(transitions):
        for j, letter in enumerate(alphabet):
            for target in row[j]:
                states[i].add_transition(letter, states[target])
    return NFA([states[i] for i in start_ids], list(alphabet),
               [states[i] for i in finish_ids])


def words(alphabet, max_length):
    for length in range(max_length + 1):
        for letters in product(alphabet, repeat=length):
            yield "".join(letters)


def reachable_states(dfa):
    visited = {dfa.start_state}
    waiting = deque([dfa.start_state])
    while waiting:
        st = waiting.popleft()
        for letter in dfa.alphabet:
            target = st.next(letter)
            if target is not None and target not in visited:
                visited.add(target)
                waiting.append(target)
    return visited


def distinguishing_word(first, second):
    # Независимая проверка сохранения языка при минимизации и записи.
    # None в паре считается неявным непринимающим стоком.
    alphabet = sorted(set(first.alphabet) | set(second.alphabet))
    waiting = deque([(first.start_state, second.start_state, "")])
    visited = {(first.start_state, second.start_state)}
    while waiting:
        left, right, word = waiting.popleft()
        if (left in first.finish_states) != (right in second.finish_states):
            return word
        for letter in alphabet:
            next_left = left.next(letter) if left is not None else None
            next_right = right.next(letter) if right is not None else None
            pair = (next_left, next_right)
            if pair not in visited:
                visited.add(pair)
                waiting.append((next_left, next_right, word + letter))
    return None


def indistinguishable_pairs(dfa):
    # Проверка минимальности таблицей различимых пар.
    # Она не вызывает проверяемые minimize_dfa/equivalent_dfa.
    states = list(reachable_states(dfa))
    indices = {st: i for i, st in enumerate(states)}
    pairs = {(i, j) for i in range(len(states)) for j in range(i + 1, len(states))}
    marked = set()
    for i, j in pairs:
        if (states[i] in dfa.finish_states) != (states[j] in dfa.finish_states):
            marked.add((i, j))
    while True:
        count = len(marked)
        for i, j in pairs - marked:
            for letter in dfa.alphabet:
                left = indices[states[i].next(letter)]
                right = indices[states[j].next(letter)]
                if tuple(sorted((left, right))) in marked:
                    marked.add((i, j))
                    break
        if len(marked) == count:
            return pairs - marked


def require_function(test, module, name):
    function = getattr(module, name, None)
    test.assertTrue(callable(function), "Нет функции " + module.__name__ + "." + name)
    return function


def load_requester():
    return importlib.import_module("lab.llm_requests")


def load_experiment():
    return importlib.import_module("lab.experiments.experiment_DFA_NFA")


class AutomataTestCase(unittest.TestCase):
    def assert_same_language(self, first, second):
        witness = distinguishing_word(first, second)
        self.assertIsNone(witness, "Автоматы различаются на слове " + repr(witness))

    def assert_complete_minimal(self, dfa, expected_count):
        self.assertEqual(dfa.total_states, expected_count)
        self.assertEqual(len(dfa.states), expected_count)
        self.assertEqual(set(dfa.states), reachable_states(dfa), "Есть недостижимые состояния")
        self.assertIn(dfa.start_state, dfa.states)
        self.assertTrue(set(dfa.finish_states) <= set(dfa.states))
        for st in dfa.states:
            for letter in dfa.alphabet:
                self.assertIn(st.next(letter), dfa.states, "DFA неполный")
        self.assertFalse(indistinguishable_pairs(dfa), "Есть эквивалентные состояния")


class TemporaryFolderTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.addCleanup(os.chdir, Path.cwd())
        self.root = Path(folder.name)
        os.chdir(self.root)


class TestStates(unittest.TestCase):
    def test_dfa_transition_and_missing_letter(self):
        first, second = State(0, {}), State(1, {})
        self.assertIsNone(first.next("a"))
        first.add_transition("a", second)
        self.assertIs(first.next("a"), second)
        self.assertIsNone(first.next("b"))

    def test_dfa_transition_is_replaced(self):
        first, second, third = State(0, {}), State(1, {}), State(2, {})
        first.add_transition("a", second)
        first.add_transition("a", third)
        self.assertIs(first.next("a"), third)

    def test_state_transitions_are_independent(self):
        first, second = State(0, {}), State(1, {})
        first.add_transition("a", first)
        self.assertIsNone(second.next("a"))

    def test_nfa_preserves_multiple_targets(self):
        first, second, third = NFAState(0, {}), NFAState(1, {}), NFAState(2, {})
        first.add_transition("a", second)
        first.add_transition("a", third)
        self.assertEqual(set(first.next("a")), {second, third})
        self.assertEqual(first.next("b"), [])

    def test_next_requires_one_character(self):
        for st in [State(0, {}), NFAState(0, {})]:
            for letter in ["", "ab"]:
                with self.subTest(state=type(st).__name__, letter=letter):
                    with self.assertRaises(AssertionError):
                        st.next(letter)

    def test_unicode_letter(self):
        st = State(0, {})
        st.add_transition("я", st)
        self.assertIs(st.next("я"), st)

    def test_state_string_contains_transition(self):
        for cls in [State, NFAState]:
            with self.subTest(state=cls.__name__):
                first, second = cls(4, {}), cls(7, {})
                first.add_transition("a", second)
                self.assertIn("4 ---(a)--> 7", str(first))


class TestDFA(unittest.TestCase):
    def test_empty_word_depends_on_start_state(self):
        self.assertEqual(make_dfa([[0, 0]], [0]).compute(""), "accept")
        self.assertEqual(make_dfa([[0, 0]], []).compute(""), "deny")

    def test_parity_language(self):
        dfa = make_dfa([[0, 1], [1, 0]], [0])
        for word in words("01", 7):
            with self.subTest(word=word):
                expected = "accept" if word.count("1") % 2 == 0 else "deny"
                self.assertEqual(dfa.compute(word), expected)

    def test_missing_transition_rejects(self):
        dfa = make_dfa([[None, 0]], [0])
        for word in ["0", "10", "101"]:
            self.assertEqual(dfa.compute(word), "deny")

    def test_unknown_letter_rejects(self):
        self.assertEqual(make_dfa([[0, 0]], [0]).compute("1a0"), "deny")

    def test_calls_start_from_initial_state(self):
        dfa = make_dfa([[0, 1], [1, 0]], [0])
        self.assertEqual(dfa.compute("1"), "deny")
        self.assertEqual(dfa.compute("1"), "deny")
        self.assertEqual(dfa.compute(""), "accept")


class TestNFA(unittest.TestCase):
    def test_one_accepting_branch_is_enough(self):
        nfa = make_nfa([[[1, 2], []], [[], []], [[], [3]], [[], []]], [0], [3])
        self.assertEqual(nfa.compute("01"), "accept")
        self.assertEqual(nfa.compute("0"), "deny")
        self.assertEqual(nfa.compute("010"), "deny")

    def test_multiple_start_states(self):
        nfa = make_nfa([[[0], []], [[], [1]]], [0, 1], [1])
        for word, expected in [("", "accept"), ("111", "accept"), ("000", "deny"), ("01", "deny")]:
            self.assertEqual(nfa.compute(word), expected)

    def test_no_start_states_reject_everything(self):
        nfa = make_nfa([[[0], [0]]], [], [0])
        for word in ["", "0", "111"]:
            self.assertEqual(nfa.compute(word), "deny")

    def test_no_finish_states_reject_everything(self):
        nfa = make_nfa([[[0], [0]]], [0], [])
        for word in ["", "01"]:
            self.assertEqual(nfa.compute(word), "deny")

    def test_duplicate_edges_do_not_change_language(self):
        nfa = make_nfa([[[1, 1], []], [[], []]], [0], [1])
        self.assertEqual(nfa.compute("0"), "accept")
        self.assertEqual(nfa.compute("00"), "deny")

    def test_missing_or_unknown_letter_rejects(self):
        nfa = make_nfa([[[0], []]], [0], [0])
        self.assertEqual(nfa.compute("1"), "deny")
        self.assertEqual(nfa.compute("a"), "deny")

    def test_compute_does_not_modify_start_states(self):
        nfa = make_nfa([[[1], []], [[], []]], [0], [1])
        before = list(nfa.start_states)
        self.assertEqual(nfa.compute("0"), "accept")
        self.assertEqual(nfa.compute("0"), "accept")
        self.assertEqual(nfa.start_states, before)


class TestParser(unittest.TestCase):
    def test_valid_answer_builds_connected_objects(self):
        parsed = answer_parser.parse_answer("2\n2\n0\n1\n0 0 0\n0 1 1\n1 0 0\n1 1 1")
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(parsed.alphabet, {"0", "1"})
        self.assertEqual([st.state_id for st in parsed.states], [0, 1])
        self.assertIs(parsed.start_states[0], parsed.states[0])
        self.assertIs(parsed.finish_states[0], parsed.states[1])
        self.assertIs(parsed.states[0].next("1")[0], parsed.states[1])

    def test_multiple_starts_finishes_and_targets(self):
        parsed = answer_parser.parse_answer("3\n1\n0 1\n1 2\n0 a 1\n0 a 2")
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(len(parsed.start_states), 2)
        self.assertEqual(len(parsed.finish_states), 2)
        self.assertEqual(set(parsed.states[0].next("a")), {parsed.states[1], parsed.states[2]})

    def test_empty_start_and_finish_lines(self):
        parsed = answer_parser.parse_answer("1\n0\n\n")
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(parsed.start_states, [])
        self.assertEqual(parsed.finish_states, [])
        self.assertEqual(parsed.alphabet, set())

    def test_invalid_headers(self):
        cases = [
            ("", "format not matching"),
            ("1\n1\n0", "format not matching"),
            ("x\n1\n0\n0", "format not matching"),
            ("1\nx\n0\n0", "format not matching"),
            ("0\n1\n\n", "impossible state count"),
            ("-2\n1\n\n", "impossible state count"),
            ("1\n-1\n0\n0", "impossible alphabet size"),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.assertEqual(answer_parser.parse_answer(answer), expected)

    def test_invalid_state_references(self):
        for answer in [
            "2\n1\n-1\n1", "2\n1\n2\n1", "2\n1\n0\n-1", "2\n1\n0\n2",
            "2\n1\n0\n1\n-1 a 0", "2\n1\n0\n1\n2 a 0",
            "2\n1\n0\n1\n0 a -1", "2\n1\n0\n1\n0 a 2",
        ]:
            with self.subTest(answer=answer):
                self.assertEqual(answer_parser.parse_answer(answer), "non existing state")

    def test_non_numeric_state_references(self):
        for answer in ["2\n1\nx\n1", "2\n1\n0\nx", "2\n1\n0\n1\nx a 1", "2\n1\n0\n1\n0 a x"]:
            with self.subTest(answer=answer):
                self.assertEqual(answer_parser.parse_answer(answer), "format not matching")

    def test_invalid_transition_rows(self):
        for row in ["0 a", "0 a 1 extra", "0 ab 1", "comment"]:
            with self.subTest(row=row):
                self.assertEqual(answer_parser.parse_answer("2\n1\n0\n1\n" + row), "format not matching")

    def test_more_letters_than_declared(self):
        self.assertEqual(answer_parser.parse_answer("1\n1\n0\n0\n0 a 0\n0 b 0"), "more letters than specified")

    def test_unused_alphabet_letters_are_allowed(self):
        parsed = answer_parser.parse_answer("1\n2\n0\n0\n0 a 0")
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(parsed.alphabet, {"a"})

    def test_whitespace_blank_lines_and_unicode(self):
        parsed = answer_parser.parse_answer("2\r\n1\r\n 0 \r\n 1 \r\n\r\n 0  я  1 \r\n")
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(NFA(parsed.start_states, parsed.alphabet, parsed.finish_states).compute("я"), "accept")

    def test_duplicate_transition_lines_keep_same_language(self):
        parsed = answer_parser.parse_answer("2\n1\n0\n1\n0 a 1\n0 a 1")
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(NFA(parsed.start_states, parsed.alphabet, parsed.finish_states).compute("a"), "accept")

    def test_parsed_answer_string_is_readable(self):
        parsed = answer_parser.parse_answer("2\n1\n0\n1\n0 a 1")
        self.assertIn("0 ---(a)--> 1", str(parsed))


class TestDeterminization(unittest.TestCase):
    def test_branching_language_is_preserved(self):
        nfa = make_nfa([[[0], [0, 1]], [[2], [2]], [[], []]], [0], [2])
        dfa = algorithms.nfa_to_dfa(nfa)
        for word in words("01", 8):
            with self.subTest(word=word):
                expected = "accept" if len(word) >= 2 and word[-2] == "1" else "deny"
                self.assertEqual(nfa.compute(word), expected)
                self.assertEqual(dfa.compute(word), expected)

    def test_empty_subset_becomes_sink(self):
        nfa = make_nfa([[[1], []], [[], []]], [0], [1])
        dfa = algorithms.nfa_to_dfa(nfa)
        sink = dfa.start_state.next("1")
        self.assertIsNotNone(sink)
        self.assertNotIn(sink, dfa.finish_states)
        self.assertIs(sink.next("0"), sink)
        self.assertIs(sink.next("1"), sink)
        self.assertEqual(dfa.total_states, 3)

    def test_accepting_initial_subset(self):
        nfa = make_nfa([[[], []], [[], []]], [0, 1], [1])
        self.assertEqual(algorithms.nfa_to_dfa(nfa).compute(""), "accept")

    def test_empty_start_subset(self):
        dfa = algorithms.nfa_to_dfa(make_nfa([[[0], [0]]], [], [0]))
        self.assertEqual(dfa.total_states, 1)
        self.assertEqual(dfa.compute(""), "deny")
        self.assertIs(dfa.start_state.next("0"), dfa.start_state)

    def test_unreachable_nfa_states_do_not_appear(self):
        nfa = make_nfa([[[0], [0]], [[1], [1]]], [0], [1])
        dfa = algorithms.nfa_to_dfa(nfa)
        self.assertEqual(dfa.total_states, 1)
        self.assertEqual(dfa.finish_states, [])

    def test_empty_alphabet(self):
        nfa = make_nfa([[]], [0], [0], [])
        dfa = algorithms.nfa_to_dfa(nfa)
        self.assertEqual(dfa.total_states, 1)
        self.assertEqual(dfa.compute(""), "accept")

    def test_fourth_symbol_requires_sixteen_subsets(self):
        nfa = make_nfa([[[0], [0, 1]], [[2], [2]], [[3], [3]], [[4], [4]], [[], []]], [0], [4])
        dfa = algorithms.nfa_to_dfa(nfa)
        self.assertEqual(dfa.total_states, 16)
        self.assertEqual(len(reachable_states(dfa)), 16)
        for word in words("01", 8):
            expected = "accept" if len(word) >= 4 and word[-4] == "1" else "deny"
            self.assertEqual(dfa.compute(word), expected, repr(word))

    def test_source_nfa_is_not_modified(self):
        nfa = make_nfa([[[0], [0, 1]], [[], []]], [0], [1])
        before = [nfa.compute(word) for word in words("01", 5)]
        algorithms.nfa_to_dfa(nfa)
        self.assertEqual([nfa.compute(word) for word in words("01", 5)], before)


class TestMinimization(AutomataTestCase):
    def minimize(self, dfa):
        return require_function(self, algorithms, "minimize_dfa")(dfa)

    def test_equivalent_accepting_states_merge(self):
        dfa = make_dfa([[1, 2], [1, 1], [2, 2]], [1, 2])
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 2)
        self.assert_same_language(dfa, result)

    def test_refinement_requires_multiple_rounds(self):
        dfa = make_dfa([[1, 1], [2, 2], [3, 3], [3, 3]], [3])
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 4)
        self.assert_same_language(dfa, result)

    def test_empty_language(self):
        dfa = make_dfa([[1, 0], [2, 1], [0, 2]], [])
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 1)
        self.assert_same_language(dfa, result)

    def test_universal_language(self):
        dfa = make_dfa([[1, 0], [2, 1], [0, 2]], [0, 1, 2])
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 1)
        self.assert_same_language(dfa, result)

    def test_only_empty_word(self):
        dfa = make_dfa([[1, 1], [1, 1]], [0])
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 2)
        self.assert_same_language(dfa, result)

    def test_empty_alphabet(self):
        for finish_ids in [[], [0]]:
            with self.subTest(finish_ids=finish_ids):
                dfa = make_dfa([[]], finish_ids, [])
                result = self.minimize(dfa)
                self.assert_complete_minimal(result, 1)
                self.assert_same_language(dfa, result)

    def test_unreachable_states_are_removed(self):
        # Состояние 2 недостижимо и распознаёт отдельный остаточный язык.
        dfa = make_dfa([[1, 0], [1, 1], [2, 2]], [1])
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 2)
        self.assert_same_language(dfa, result)

    def test_state_numbers_and_list_order_do_not_define_semantics(self):
        dfa = make_dfa([[1, 0], [0, 1]], [0])
        dfa.states[0].state_id = 50
        dfa.states[1].state_id = 90
        dfa.states.reverse()
        result = self.minimize(dfa)
        self.assert_complete_minimal(result, 2)
        self.assert_same_language(dfa, result)

    def test_idempotence(self):
        original = make_dfa([[1, 2], [1, 1], [2, 2]], [1, 2])
        first = self.minimize(original)
        second = self.minimize(first)
        self.assert_complete_minimal(second, first.total_states)
        self.assert_same_language(first, second)

    def test_source_automaton_is_not_modified(self):
        dfa = make_dfa([[1, 2], [1, 1], [2, 2]], [1, 2])
        before_states = list(dfa.states)
        before_transitions = [dict(st.transitions) for st in dfa.states]
        before_finish = list(dfa.finish_states)
        start = dfa.start_state
        self.minimize(dfa)
        self.assertEqual(dfa.states, before_states)
        self.assertEqual([st.transitions for st in dfa.states], before_transitions)
        self.assertEqual(dfa.finish_states, before_finish)
        self.assertIs(dfa.start_state, start)


class TestEquivalence(unittest.TestCase):
    def equivalent(self, first, second):
        return require_function(self, algorithms, "equivalent_dfa")(first, second)

    def test_same_automaton(self):
        dfa = make_dfa([[0, 1], [1, 0]], [0])
        self.assertTrue(self.equivalent(dfa, dfa))

    def test_renamed_states_and_different_start_index(self):
        first = make_dfa([[0, 1], [1, 0]], [0])
        second = make_dfa([[0, 1], [1, 0]], [1], start_id=1)
        for st in second.states:
            st.state_id += 100
        self.assertTrue(self.equivalent(first, second))

    def test_different_sizes_same_language(self):
        first = make_dfa([[1, 1], [1, 1]], [1])
        second = make_dfa([[1, 2], [1, 1], [2, 2]], [1, 2])
        self.assertTrue(self.equivalent(first, second))
        self.assertTrue(self.equivalent(second, first))

    def test_difference_on_empty_word(self):
        self.assertFalse(self.equivalent(make_dfa([[0, 0]], [0]), make_dfa([[0, 0]], [])))

    def test_same_number_of_states_different_languages(self):
        ends_zero = make_dfa([[1, 0], [1, 0]], [1])
        ends_one = make_dfa([[0, 1], [0, 1]], [1])
        self.assertFalse(self.equivalent(ends_zero, ends_one))
        self.assertFalse(self.equivalent(ends_one, ends_zero))

    def test_difference_only_on_long_word(self):
        word = "1010" * 7
        dead = len(word) + 1
        rows = []
        for i, letter in enumerate(word):
            row = [dead, dead]
            row[int(letter)] = i + 1
            rows.append(row)
        rows.append([dead, dead])
        rows.append([dead, dead])
        one_word = make_dfa(rows, [len(word)])
        empty = make_dfa([[0, 0]], [])
        self.assertFalse(self.equivalent(one_word, empty))

    def test_alphabet_order_does_not_matter(self):
        first = make_dfa([[0, 1], [0, 1]], [1])
        second = make_dfa([[1, 0], [1, 0]], [1], ["1", "0"])
        self.assertTrue(self.equivalent(first, second))

    def test_empty_alphabet(self):
        self.assertTrue(self.equivalent(make_dfa([[]], [0], []), make_dfa([[]], [0], [])))
        self.assertFalse(self.equivalent(make_dfa([[]], [0], []), make_dfa([[]], [], [])))

    def test_unreachable_accepting_state_does_not_matter(self):
        first = make_dfa([[0, 0]], [])
        second = make_dfa([[0, 0], [1, 1]], [1])
        self.assertTrue(self.equivalent(first, second))


class TestFileIO(TemporaryFolderTestCase):
    def test_answer_path_normalizes_model_and_number(self):
        expected = Path("experiments/run_test/openrouter/vendor__model__free/basic/vendor__model__free__basic__007.txt")
        self.assertEqual(fileIO.answer_path("run_test", "vendor/model:free", "basic", 7), expected)

    def test_answer_path_does_not_create_directories(self):
        path = fileIO.answer_path("run_test", "model", "basic", 1000)
        self.assertTrue(path.name.endswith("__1000.txt"))
        self.assertFalse(path.parent.exists())

    def test_save_answer_creates_folders_and_preserves_utf8(self):
        answer = "Состояние я\n0 я 1\n"
        fileIO.save_answer("run_test", "vendor/model", "basic", 0, answer)
        path = fileIO.answer_path("run_test", "vendor/model", "basic", 0)
        self.assertEqual(path.read_text(encoding="utf-8"), answer)

    def test_save_answer_does_not_overwrite_existing_file(self):
        args = ("run_test", "model", "basic", 0)
        fileIO.save_answer(*args, "first")
        with self.assertRaises(FileExistsError):
            fileIO.save_answer(*args, "second")
        self.assertEqual(fileIO.answer_path(*args).read_text(encoding="utf-8"), "first")


class TestSaveDFA(TemporaryFolderTestCase, AutomataTestCase):
    def save(self, dfa, path):
        require_function(self, fileIO, "save_dfa")(dfa, path)

    def read_dfa(self, path):
        parsed = answer_parser.parse_answer(path.read_text(encoding="utf-8"))
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        return algorithms.nfa_to_dfa(NFA(parsed.start_states, parsed.alphabet, parsed.finish_states))

    def test_roundtrip_and_nonsequential_state_ids(self):
        dfa = make_dfa([[0, 1], [1, 0]], [0])
        dfa.states[0].state_id = 40
        dfa.states[1].state_id = 80
        path = Path("minimized/nested/answer.txt")
        self.save(dfa, path)
        self.assertTrue(path.is_file())
        self.assert_same_language(dfa, self.read_dfa(path))
        self.assertEqual([st.state_id for st in dfa.states], [40, 80])

    def test_no_finish_states_keeps_blank_fourth_line(self):
        path = Path("empty.txt")
        dfa = make_dfa([[0, 0]], [])
        self.save(dfa, path)
        self.assertEqual(path.read_text(encoding="utf-8").split("\n")[3], "")
        self.assert_same_language(dfa, self.read_dfa(path))

    def test_unicode_alphabet_roundtrip(self):
        dfa = make_dfa([[0, 1], [0, 1]], [1], ["я", "🙂"])
        path = Path("unicode.txt")
        self.save(dfa, path)
        self.assert_same_language(dfa, self.read_dfa(path))

    def test_empty_alphabet_roundtrip(self):
        for finish in [[], [0]]:
            with self.subTest(finish=finish):
                dfa = make_dfa([[]], finish, [])
                path = Path("zero_letters.txt")
                self.save(dfa, path)
                self.assert_same_language(dfa, self.read_dfa(path))

    def test_second_save_overwrites_previous_result(self):
        path = Path("answer.txt")
        self.save(make_dfa([[0, 0]], [0]), path)
        second = make_dfa([[0, 0]], [])
        self.save(second, path)
        self.assert_same_language(second, self.read_dfa(path))


class TestGroundTruth(AutomataTestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module("lab.experiments.specs.ground_truth")

    def test_all_five_builders_exist(self):
        self.assertEqual(set(self.module.ground_truth_builders),
                         {"basic", "4th-symbol", "employer", "intersection", "abc-bca-cab"})

    def test_complete_reachable_minimal_automata(self):
        counts = {"basic": 10, "4th-symbol": 16, "employer": 12, "intersection": 11, "abc-bca-cab": 8}
        for task, count in counts.items():
            with self.subTest(task=task):
                self.assert_complete_minimal(self.module.ground_truth_builders[task](), count)

    def test_basic_against_language_definition(self):
        dfa = self.module.ground_truth_builders["basic"]()
        for word in words("01", 9):
            expected = word.count("0") % 2 == 0 and word.count("1") % 2 == 1 and "00" not in word and "11" not in word
            self.assertEqual(dfa.compute(word) == "accept", expected, repr(word))

    def test_fourth_symbol_against_language_definition(self):
        dfa = self.module.ground_truth_builders["4th-symbol"]()
        for word in words("01", 9):
            self.assertEqual(dfa.compute(word) == "accept", len(word) >= 4 and word[-4] == "1", repr(word))

    def test_intersection_against_language_definition(self):
        dfa = self.module.ground_truth_builders["intersection"]()
        for word in words("01", 9):
            expected = len(word) >= 3 and word[-3] == "1" and word.count("0") == 1
            self.assertEqual(dfa.compute(word) == "accept", expected, repr(word))

    def test_block_language_against_definition(self):
        dfa = self.module.ground_truth_builders["abc-bca-cab"]()
        for word in words("abc", 7):
            expected = len(word) % 3 == 0 and all(
                word[i:i + 3] in ["abc", "bca", "cab"] for i in range(0, len(word), 3))
            self.assertEqual(dfa.compute(word) == "accept", expected, repr(word))

    def test_employer_all_regions_and_first_digits(self):
        dfa = self.module.ground_truth_builders["employer"]()
        for letters in product("AMCSPB", repeat=3):
            region = "".join(letters)
            for first_digit in "012345":
                for tail in ["000", "234", "555"]:
                    word = region + first_digit + tail
                    expected = region != "SPB" or first_digit != "0"
                    self.assertEqual(dfa.compute(word) == "accept", expected, word)

    def test_employer_wrong_length_order_and_characters(self):
        dfa = self.module.ground_truth_builders["employer"]()
        cases = ["", "SPB", "SPB123", "SPB12345", "SP1234", "SPBA1234", "1PB1234", "SPB12A4", "XYZ1234", "SPB6789"]
        for word in cases:
            with self.subTest(word=word):
                expected = re.fullmatch(r"[AMCSPB]{3}[0-5]{4}", word) is not None
                if expected and word[:3] == "SPB" and word[3] == "0":
                    expected = False
                self.assertEqual(dfa.compute(word) == "accept", expected)

    def test_builders_create_independent_objects(self):
        for task, builder in self.module.ground_truth_builders.items():
            with self.subTest(task=task):
                first, second = builder(), builder()
                self.assertTrue(set(first.states).isdisjoint(second.states))
                first.start_state.transitions.clear()
                self.assertEqual(len(second.start_state.transitions), len(second.alphabet))

    def test_existing_examples_from_experiment(self):
        experiment = load_experiment()
        for task, cases in experiment.tasks_tests.items():
            dfa = self.module.ground_truth_builders[task]()
            for word, expected in cases.items():
                with self.subTest(task=task, word=word):
                    self.assertEqual(dfa.compute(word), expected)


class TestOpenRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requester = load_requester()

    def run_request(self, content, usage):
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")],
            usage=usage,
        )
        client = MagicMock()
        client.chat.send.return_value = response
        with patch.object(self.requester, "OpenRouter") as factory:
            factory.return_value.__enter__.return_value = client
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "unit-test-key"}):
                with redirect_stdout(io.StringIO()):
                    result = self.requester.openrouter_request("test/model", "test task", "system prompt")
            factory.assert_called_once_with(api_key="unit-test-key")
        self.assertEqual(len(result), 3)
        self.assertGreaterEqual(result[2], 0)
        return result, client

    def test_text_cost_and_request_parameters(self):
        usage = SimpleNamespace(cost=0.0123, prompt_tokens=10, completion_tokens=20)
        result, client = self.run_request("answer", usage)
        self.assertEqual(result[:2], ("answer", 0.0123))
        client.chat.send.assert_called_once()
        kwargs = client.chat.send.call_args.kwargs
        self.assertEqual(kwargs["model"], "test/model")
        self.assertTrue(any(m["role"] == "system" and m["content"] for m in kwargs["messages"]))
        self.assertIn({"role": "user", "content": "test task"}, kwargs["messages"])

    def test_missing_usage_means_zero_cost(self):
        result, _ = self.run_request("answer", None)
        self.assertEqual(result[:2], ("answer", 0.0))

    def test_non_numeric_cost_means_zero(self):
        for cost in [None, "unknown"]:
            with self.subTest(cost=cost):
                usage = SimpleNamespace(cost=cost, prompt_tokens=1, completion_tokens=2)
                result, _ = self.run_request("answer", usage)
                self.assertEqual(result[:2], ("answer", 0.0))

    def test_integer_cost_is_supported(self):
        usage = SimpleNamespace(cost=2, prompt_tokens=1, completion_tokens=2)
        result, _ = self.run_request("answer", usage)
        self.assertEqual(result[:2], ("answer", 2.0))

    def test_empty_string_stays_empty(self):
        result, _ = self.run_request("", None)
        self.assertEqual(result[:2], ("", 0.0))

    def test_missing_content_becomes_empty_string(self):
        # Регрессия: str(None) даёт "None", а не пустую строку.
        result, _ = self.run_request(None, None)
        self.assertEqual(result[:2], ("", 0.0))

    def test_api_exception_is_not_reported_as_success(self):
        with patch.object(self.requester, "OpenRouter") as factory:
            client = factory.return_value.__enter__.return_value
            client.chat.send.side_effect = RuntimeError("test API failure")
            with self.assertRaisesRegex(RuntimeError, "test API failure"):
                self.requester.openrouter_request("test/model", "task", "system prompt")


class ExperimentTestCase(TemporaryFolderTestCase):
    @classmethod
    def setUpClass(cls):
        cls.experiment = load_experiment()

    def setUp(self):
        super().setUp()
        patches = [
            patch.object(self.experiment, "RUN_NAME", "unit_test_run"),
            patch.object(self.experiment, "tasks", {"sample": "test task"}),
            patch.object(self.experiment, "tasks_tests", {"sample": {"": "deny", "0": "deny", "1": "accept"}}),
            patch.object(self.experiment, "tasks_alphabets", {"sample": ["0", "1"]}, create=True),
            patch.object(self.experiment, "ground_truth_builders", {"sample": lambda: make_dfa([[0, 1], [0, 1]], [1])},
                         create=True),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)


class TestExperiment(ExperimentTestCase):
    def test_strip_reasoning(self):
        cases = [
            ("  answer  ", "answer"),
            ("<think>reasoning\nmore</think>\n answer ", "answer"),
            ("</think>first</think>second", "second"),
            ("<think>reasoning</think>", ""),
        ]
        for answer, expected in cases:
            with self.subTest(answer=answer):
                self.assertEqual(self.experiment.parse_qwen_answer(answer), expected)

    def test_get_answers_saves_text_and_sums_costs(self):
        responses = [("<think>x</think>first", 0.01, 2.0), (" second ", 0.02, 3.0)]
        with patch.object(self.experiment, "request_for", return_value=MagicMock(side_effect=responses)) as factory:
            with redirect_stdout(io.StringIO()):
                cost = self.experiment.get_answers("vendor/model", 2, "sample")
        self.assertAlmostEqual(cost[0], 0.03)
        self.assertEqual(factory.return_value.call_count, 2)
        factory.return_value.assert_called_with("vendor/model", "test task", self.experiment.AUTOMATA_SYSTEM_REQUEST)
        for number, expected in enumerate(["first", "second"]):
            path = fileIO.answer_path("unit_test_run", "vendor/model", "sample", number)
            self.assertEqual(path.read_text(encoding="utf-8"), expected)

    def test_existing_answers_are_skipped(self):
        fileIO.save_answer("unit_test_run", "model", "sample", 0, "old")
        with patch.object(self.experiment, "request_for", return_value=MagicMock(return_value=("new", 0.02, 1.0))) as factory:
            with redirect_stdout(io.StringIO()):
                cost = self.experiment.get_answers("model", 2, "sample")
        factory.return_value.assert_called_once_with("model", "test task", self.experiment.AUTOMATA_SYSTEM_REQUEST)
        self.assertAlmostEqual(cost[0], 0.02)
        self.assertEqual(fileIO.answer_path("unit_test_run", "model", "sample", 0).read_text(encoding="utf-8"), "old")

    def test_zero_iterations_do_not_call_api(self):
        with patch.object(self.experiment, "request_for", return_value=MagicMock()) as factory:
            self.assertEqual(self.experiment.get_answers("model", 0, "sample"), (0.0, 0.0))
        factory.return_value.assert_not_called()

    def test_failed_request_does_not_save_an_answer(self):
        with patch.object(self.experiment, "request_for", return_value=MagicMock(side_effect=RuntimeError("failed"))):
            with self.assertRaises(RuntimeError):
                self.experiment.get_answers("model", 1, "sample")
        self.assertFalse(fileIO.answer_path("unit_test_run", "model", "sample", 0).exists())

    def test_check_results_counts_invalid_answers(self):
        answers = [
            "2\n2\n0\n1\n0 0 0\n0 1 1\n1 0 0\n1 1 1",
            "1\n2\n0\n0\n0 0 0\n0 1 0",
            "broken",
        ]
        for i, answer in enumerate(answers):
            fileIO.save_answer("unit_test_run", "test_model", "sample", i, answer)
        output = io.StringIO()
        with redirect_stdout(output):
            self.experiment.check_results("test_model")
        text = output.getvalue()
        for expected in ["Всего ответов: 3", "Корректный формат: 2", "Ошибки формата: 1", "DFA: 2", "NFA: 0",
                         "Прошли все тесты: 1"]:
            self.assertIn(expected, text)

    def test_check_results_counts_nfa(self):
        answer = "2\n2\n0\n1\n0 0 0\n0 1 0\n0 1 1"
        fileIO.save_answer("unit_test_run", "model", "sample", 0, answer)
        output = io.StringIO()
        with redirect_stdout(output):
            self.experiment.check_results("model")
        self.assertRegex(output.getvalue(), r"(?m)^DFA: 0$")
        self.assertRegex(output.getvalue(), r"(?m)^NFA: 1$")

    def test_check_results_handles_empty_folder(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.experiment.check_results("missing_model")
        self.assertIn("Всего ответов: 0", output.getvalue())

    def test_check_results_handles_only_format_errors(self):
        fileIO.save_answer("unit_test_run", "model", "sample", 0, "broken")
        output = io.StringIO()
        with redirect_stdout(output):
            self.experiment.check_results("model")
        self.assertIn("Ошибки формата: 1", output.getvalue())
        self.assertIn("Корректный формат: 0", output.getvalue())


class TestUpdatedExperiment(ExperimentTestCase):
    def test_exact_correctness_and_mean_minimal_size(self):
        # Оба валидных автомата проходят три примера, но второй ошибается на "10".
        answers = [
            "2\n2\n0\n1\n0 0 0\n0 1 1\n1 0 0\n1 1 1",
            "3\n2\n0\n2\n0 0 1\n0 1 2\n1 0 2\n1 1 2\n2 0 2\n2 1 2",
            "broken",
        ]
        for i, answer in enumerate(answers):
            fileIO.save_answer("unit_test_run", "model", "sample", i, answer)
        output = io.StringIO()
        with redirect_stdout(output):
            self.experiment.check_results("model")
        text = output.getvalue()
        self.assertIn("Прошли все тесты: 2", text)
        self.assertIn("Процент корректных автоматов: 33.33%", text)
        self.assertIn(
            "Среднее число состояний в минимизированном DFA: 2.50",
            text
        )

    def test_letters_outside_task_alphabet_are_format_errors(self):
        answer = "1\n3\n0\n0\n0 0 0\n0 1 0\n0 a 0"
        fileIO.save_answer("unit_test_run", "model", "sample", 0, answer)
        output = io.StringIO()
        with redirect_stdout(output):
            self.experiment.check_results("model")
        self.assertIn("Корректный формат: 0", output.getvalue())
        self.assertIn("Ошибки формата: 1", output.getvalue())

    def test_task_alphabet_is_used_even_when_a_letter_has_no_transitions(self):
        answer = "2\n2\n0\n1\n0 1 1\n1 1 1"
        fileIO.save_answer("unit_test_run", "model", "sample", 0, answer)
        with redirect_stdout(io.StringIO()):
            self.experiment.check_results("model")
        path = Path("minimized/unit_test_run/openrouter/model/sample/model__sample__000.txt")
        self.assertTrue(path.is_file(), "Минимизированный DFA не сохранён отдельно")
        parsed = answer_parser.parse_answer(path.read_text(encoding="utf-8"))
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        self.assertEqual(parsed.alphabet, {"0", "1"})
        self.assertEqual(len(parsed.states), 3)

    def test_second_analysis_does_not_count_minimized_files_as_answers(self):
        answer = "2\n2\n0\n1\n0 0 0\n0 1 1\n1 0 0\n1 1 1"
        fileIO.save_answer("unit_test_run", "model", "sample", 0, answer)
        for _ in range(2):
            output = io.StringIO()
            with redirect_stdout(output):
                self.experiment.check_results("model")
            self.assertIn("Всего ответов: 1", output.getvalue())
            self.assertIn(
                "Процент корректных автоматов: 100.00%",
                output.getvalue()
            )
        originals = list(Path("experiments").rglob("*.txt"))
        minimized = list(Path("minimized").rglob("*.txt"))
        self.assertEqual(len(originals), 1)
        self.assertEqual(len(minimized), 1)


class TestPipeline(TemporaryFolderTestCase, AutomataTestCase):
    def test_parse_determinize_minimize_save_read(self):
        # Этот NFA принимает слова, заканчивающиеся на 1.
        answer = "2\n2\n0\n1\n0 0 0\n0 1 0\n0 1 1"
        parsed = answer_parser.parse_answer(answer)
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        dfa = algorithms.nfa_to_dfa(NFA(parsed.start_states, ["0", "1"], parsed.finish_states))
        self.assertEqual(set(dfa.states), reachable_states(dfa))
        minimized = require_function(self, algorithms, "minimize_dfa")(dfa)
        reference = make_dfa([[0, 1], [0, 1]], [1])
        self.assert_complete_minimal(minimized, 2)
        self.assert_same_language(reference, minimized)
        self.assertTrue(require_function(self, algorithms, "equivalent_dfa")(minimized, reference))
        path = Path("minimized/pipeline.txt")
        require_function(self, fileIO, "save_dfa")(minimized, path)
        parsed_again = answer_parser.parse_answer(path.read_text(encoding="utf-8"))
        self.assertIsInstance(parsed_again, answer_parser.ParsedAnswer)
        restored = algorithms.nfa_to_dfa(NFA(parsed_again.start_states, ["0", "1"], parsed_again.finish_states))
        self.assert_same_language(reference, restored)




# Новые проверки: регулярки, epsilon, pipeline, статистика, API и запуск.
import json
import random
from functools import lru_cache
from lab.automata import epsilon_closure
from lab.regex.regex_parser import parse_regex
from lab.regex.regex_to_nfa import regex_to_nfa
from lab.experiments import stats
from lab.experiments.specs.ground_truth import ground_truth_builders
from lab.experiments.specs.tasks import tasks_alphabets

repair_module = importlib.import_module('lab.experiments.pipelines.repair')
parallel_module = importlib.import_module('lab.experiments.pipelines.parallel_tests')
finalizer_module = importlib.import_module('lab.experiments.pipelines.finalizer')


# Даже при ошибке в mock настоящий HTTP-запрос не уйдёт.
def setUpModule():
    global network_guard
    network_guard = patch('socket.socket.connect', side_effect=AssertionError('Тест попытался выйти в сеть'))
    network_guard.start()


def tearDownModule():
    network_guard.stop()


class QuietTestCase(unittest.TestCase):
    def setUp(self):
        output = redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)


class TestGenerated(AutomataTestCase):
    pass


def add_case(name, function, *args):
    # Значения фиксируются в замыкании, каждый случай виден отдельно в unittest.
    def test(self):
        function(self, *args)
    test.__name__ = 'test_' + name
    setattr(TestGenerated, test.__name__, test)


@lru_cache(maxsize=None)
def regex_machines(expression):
    nfa = regex_to_nfa(expression, ['0', '1'])
    if isinstance(nfa, str):
        raise AssertionError((expression, nfa))
    dfa = algorithms.nfa_to_dfa(nfa)
    return nfa, dfa, algorithms.minimize_dfa(dfa)


def regex_case(self, expression, word):
    # Python re — независимый эталон для разрешённого подмножества синтаксиса.
    expected = 'accept' if re.fullmatch(expression, word) else 'deny'
    for machine in regex_machines(expression):
        self.assertEqual(machine.compute(word), expected, (expression, word))


atoms = ['0', '1', '0*', '1*', '(0|1)', '(01)*', '(10)*', '(0|11)*']
expressions = list(atoms)
for left in atoms:
    for right in atoms:
        expressions.append(left + right)
expressions += ['0|11', '01|0', '(0*)*', '(0|1)*', '(01|10)*', '01(0101)*0|(1010)*1']
# 60 различных выражений × 15 слов = 900 проверок.
for i, expression in enumerate(expressions[:60]):
    for j, word in enumerate(words('01', 3)):
        add_case(f'regex_{i:02d}_word_{j:02d}', regex_case, expression, word)


def random_dfa(seed):
    rng = random.Random(seed)
    size = rng.randint(1, 8)
    rows = [[rng.randrange(size), rng.randrange(size)] for _ in range(size)]
    finishes = [i for i in range(size) if rng.choice([False, True])]
    return make_dfa(rows, finishes, start_id=rng.randrange(size))


def minimize_case(self, seed):
    original = random_dfa(seed)
    before = [dict(st.transitions) for st in original.states]
    result = algorithms.minimize_dfa(original)
    self.assert_same_language(original, result)
    self.assert_complete_minimal(result, len(result.states))
    self.assertEqual(before, [st.transitions for st in original.states])
    again = algorithms.minimize_dfa(result)
    self.assertEqual(again.total_states, result.total_states)


for seed in range(400):
    add_case(f'minimize_seed_{seed:03d}', minimize_case, seed)


def equivalence_case(self, seed):
    first, second = random_dfa(seed), random_dfa(seed + 2000)
    expected = distinguishing_word(first, second) is None
    self.assertEqual(algorithms.equivalent_dfa(first, second), expected)
    self.assertEqual(algorithms.equivalent_dfa(second, first), expected)


for seed in range(200):
    add_case(f'equivalence_seed_{seed:03d}', equivalence_case, seed)


def epsilon_case(self, seed):
    rng = random.Random(seed)
    nodes = [NFAState(i, {}) for i in range(5)]
    for node in nodes:
        for target in nodes:
            if rng.random() < .2:
                node.add_epsilon_transition(target)
            for letter in '01':
                if rng.random() < .12:
                    node.add_transition(letter, target)
    starts = [nodes[i] for i in range(5) if rng.random() < .5]
    finishes = [nodes[i] for i in range(5) if rng.random() < .5]
    nfa = NFA(starts, ['0', '1'], finishes)
    dfa = algorithms.nfa_to_dfa(nfa)
    # Независимый поиск по парам (состояние, позиция), без epsilon_closure.
    for word in words('01', 3):
        seen = set()
        stack = [(node, 0) for node in starts]
        accepted = False
        while stack:
            node, pos = stack.pop()
            if (node, pos) in seen:
                continue
            seen.add((node, pos))
            if pos == len(word) and node in finishes:
                accepted = True
            stack.extend((target, pos) for target in node.epsilon_transitions)
            if pos < len(word):
                stack.extend((target, pos + 1) for target in node.next(word[pos]))
        expected = 'accept' if accepted else 'deny'
        self.assertEqual(nfa.compute(word), expected)
        self.assertEqual(dfa.compute(word), expected)
    closure = epsilon_closure(starts)
    self.assertTrue(set(starts) <= closure)
    self.assertEqual(epsilon_closure(closure), closure)


for seed in range(100):
    add_case(f'epsilon_seed_{seed:03d}', epsilon_case, seed)


def parser_case(self, seed):
    dfa = random_dfa(seed)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'answer.txt'
        fileIO.save_dfa(dfa, path)
        parsed = answer_parser.parse_answer(path.read_text(encoding='utf-8'))
        self.assertIsInstance(parsed, answer_parser.ParsedAnswer)
        restored = algorithms.nfa_to_dfa(NFA(parsed.start_states, ['0', '1'], parsed.finish_states))
        self.assert_same_language(dfa, restored)
        # Гарантированно неверная ссылка на состояние в последнем переходе.
        bad = path.read_text(encoding='utf-8') + f'0 0 {len(dfa.states)}\n'
        self.assertEqual(answer_parser.parse_answer(bad), 'non existing state')


for seed in range(100):
    add_case(f'parser_roundtrip_{seed:03d}', parser_case, seed)


def extraction_case(self, seed):
    rng = random.Random(seed)
    valid = list(words('01', 5))
    rng.shuffle(valid)
    items = valid[:12] + [12, None, True, 'a', '0a', ' ', valid[0]]
    rng.shuffle(items)
    limit = 1 + seed % 12
    expected = []
    for item in items:
        if isinstance(item, str) and set(item) <= set('01') and item not in expected:
            expected.append(item)
    payload = json.dumps(items)
    if seed % 3 == 1:
        payload = '```json\n' + payload + '\n```'
    if seed % 3 == 2:
        payload = json.dumps({'words': items})
    self.assertEqual(parallel_module.extract_test_words(payload, '01', limit), expected[:limit])


for seed in range(100):
    add_case(f'test_word_extraction_{seed:03d}', extraction_case, seed)


class TestRegexFormat(unittest.TestCase):
    def test_invalid_syntax(self):
        for expression in ['', '()', '0|', '|0', '0||1', '*0', '0**', '(0', '0)', '0+', '0?', '[01]', '0{2}', '^0$', '0.1', '0@1']:
            with self.subTest(expression=expression):
                self.assertIsInstance(parse_regex(expression, '01'), str)
                self.assertIsInstance(regex_to_nfa(expression, ['0', '1']), str)

    def test_wrong_alphabet(self):
        self.assertEqual(parse_regex('a|0', '01'), 'unexpected alphabet symbol')

    def test_nested_star_and_precedence(self):
        for expression in ['(0*)*', '0|11*', '(0|1)*0', '(01|10)*']:
            for word in words('01', 5):
                regex_case(self, expression, word)


class TestStatisticsAndStorage(TemporaryFolderTestCase):
    def test_settings_same_allowed_changed_rejected(self):
        path = self.root / 'settings.json'
        fileIO.save_settings(path, {'prompt': 'условие'})
        fileIO.save_settings(path, {'prompt': 'условие'})
        with self.assertRaises(ValueError):
            fileIO.save_settings(path, {'prompt': 'другое'})
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8")),
            {'prompt': 'условие'}
        )

    def test_sources_and_minimized_separated(self):
        paths = [fileIO.automata_run_dir('run', source, minimized=mini)
                 for source in ('local', 'openrouter') for mini in (False, True)]
        self.assertEqual(len(set(paths)), 4)
        self.assertNotEqual(fileIO.regex_answer_path('r', 'local', 'm', 'basic', 0),
                            fileIO.regex_answer_path('r', 'openrouter', 'm', 'basic', 0))
        with self.assertRaises(ValueError):
            fileIO.automata_run_dir('r', 'wrong')

    def test_artifacts_roundtrip(self):
        path = self.root / 'basic__000.txt'
        data = {'draft': '0', 'generated_tests': ['', '01'], 'test_report': 'ошибка'}
        result = fileIO.save_pipeline_artifacts(path, data)
        self.assertEqual(result.name, 'basic__000__pipeline.json')
        self.assertEqual(json.loads(result.read_text(encoding='utf-8')), data)
        self.assertFalse(list(self.root.glob('*.tmp')))
        self.assertFalse(path.exists())

    def test_resume_restore_and_accumulate(self):
        with patch.object(stats, 'checked_correct', return_value=True):
            for i in range(3):
                path = self.root / f'basic__{i:03d}.txt'
                stats.save_attempt(path, i, 'regex', 'basic', '1', '1', i + 1.0, .1, False)
                path.unlink()
                self.assertTrue(stats.already_saved(path, i))
                self.assertEqual(path.read_text(encoding="utf-8"), '1')
        records = stats.load_statistics(self.root)['attempts']
        self.assertEqual(len(records), 3)
        self.assertEqual(sum(r['elapsed'] for r in records.values()), 6)
        self.assertAlmostEqual(sum(r['cost'] for r in records.values()), .3)

    def test_duplicate_attempt_does_not_double_time(self):
        path = self.root / 'basic__000.txt'
        with patch.object(stats, 'checked_correct', return_value=True):
            stats.save_attempt(path, 0, 'regex', 'basic', '1', '1', 12, 0, False)
            with self.assertRaises(FileExistsError):
                stats.save_attempt(path, 0, 'regex', 'basic', '1', '1', 12, 0, False)
        self.assertEqual(len(stats.load_statistics(self.root)['attempts']), 1)

    def test_conflicting_txt_rejected(self):
        stats.write_statistics(self.root, {'version': 1, 'attempts': {'0': {'answer': '1'}}})
        path = self.root / 'basic__000.txt'
        path.write_text('0')
        with self.assertRaises(ValueError):
            stats.already_saved(path, 0)

    def test_legacy_answer_preserved(self):
        path = self.root / 'basic__000.txt'
        path.write_text('old')
        self.assertTrue(stats.already_saved(path, 0))
        self.assertEqual(path.read_text(encoding="utf-8"), 'old')

    def test_corrupt_statistics_rejected(self):
        for data in [{'version': 2, 'attempts': {}}, {'version': 1, 'attempts': []}]:
            (self.root / 'statistics.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                stats.load_statistics(self.root)

    def test_unknown_correctness_not_false(self):
        with patch.object(stats, 'is_correct', side_effect=RuntimeError('broken checker')):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(stats.checked_correct('regex', 'basic', '1'))

    def test_exact_check_not_only_examples(self):
        self.assertTrue(stats.is_correct('regex', 'basic', '01(0101)*0|(1010)*1'))
        self.assertFalse(stats.is_correct('regex', 'basic', '1|010|10101'))


def fake_responses(items):
    iterator = iter(items)
    def request(model, task, prompt, **kwargs):
        try:
            answer, reason, cost, seconds = next(iterator)
        except StopIteration:
            raise AssertionError("Лишний запрос к модели: ответы mock уже закончились") from None
        kwargs.get('details', {}).update(done_reason=reason, thinking='previous thoughts')
        return answer, cost, seconds
    return request


class TestRepairAndFinalizer(QuietTestCase):
    def test_correct_draft_skips_repair(self):
        info = {}
        with patch.object(repair_module, 'local_request', side_effect=fake_responses([('1', 'stop', .1, 2)])) as ask:
            with patch.object(repair_module, 'first_issue', return_value=None):
                answer, cost, elapsed = repair_module.repair('regex', 'm', 'basic', 'task', metrics=info)
        self.assertEqual((answer, cost), ('1', .1))
        self.assertEqual(ask.call_count, 1)
        self.assertFalse(info['repair_attempted'])
        self.assertGreaterEqual(elapsed, 0)

    def test_bad_repair_keeps_draft(self):
        with patch.object(repair_module, 'local_request', side_effect=fake_responses([('0', 'stop', .1, 2), ('00', 'stop', .2, 3)])):
            with patch.object(repair_module, 'first_issue', side_effect=['wrong', 'still wrong']):
                answer, cost, _ = repair_module.repair('regex', 'm', 'basic', 'task')
        self.assertEqual(answer, '0')
        self.assertAlmostEqual(cost, .3)

    def test_both_truncated_calls_are_finalized(self):
        info = {}
        with patch.object(repair_module, 'local_request', side_effect=fake_responses([('', 'length', .1, 2), ('partial', 'length', .2, 3)])):
            with patch.object(repair_module, 'finalize_answer', side_effect=[('0', .03, 1), ('1', .04, 1)]) as finish:
                with patch.object(repair_module, 'first_issue', side_effect=['wrong', None]):
                    answer, cost, _ = repair_module.repair('regex', 'm', 'basic', 'task', metrics=info)
        self.assertEqual(answer, '1')
        self.assertEqual(finish.call_count, 2)
        self.assertAlmostEqual(cost, .37)
        self.assertEqual(info['draft'], '0')
        self.assertTrue(info['repair_attempted'])

    def test_empty_draft_stops(self):
        with patch.object(repair_module, 'local_request', side_effect=fake_responses([('', 'stop', 0, 2)])) as ask:
            self.assertEqual(repair_module.repair('regex', 'm', 'basic', 'task')[0], '')
        self.assertEqual(ask.call_count, 1)

    def test_finalizer_has_task_tail_and_no_thinking(self):
        thinking = 'BEGIN' + 'x' * 13000 + 'END'
        with patch.object(finalizer_module, 'local_request', side_effect=fake_responses([('1', 'stop', .1, 2)])) as ask:
            self.assertEqual(finalizer_module.finalize_answer('regex', 'm', 'TASK', thinking, 'PART'), ('1', .1, 2))
        task = ask.call_args.args[1]
        self.assertIn('TASK', task)
        self.assertIn('PART', task)
        self.assertIn('END', task)
        self.assertNotIn('BEGIN', task)
        self.assertFalse(ask.call_args.kwargs['think'])

    def test_finalizer_does_not_accept_truncated_output(self):
        with patch.object(finalizer_module, 'local_request', side_effect=fake_responses([('partial', 'length', .1, 2)])):
            self.assertEqual(finalizer_module.finalize_answer('regex', 'm', 'task', 'thought'), ('', .1, 2))

    def test_empty_finalizer_no_request(self):
        with patch.object(finalizer_module, 'local_request') as ask:
            self.assertEqual(finalizer_module.finalize_answer('regex', 'm', 'task', ''), ('', 0, 0))
        ask.assert_not_called()

    def test_invalid_limits(self):
        for limit in [0, -2]:
            with self.assertRaises(ValueError):
                repair_module.repair('regex', 'm', 'basic', 't', draft_limit=limit)
            with self.assertRaises(ValueError):
                finalizer_module.finalize_answer('regex', 'm', 't', 'x', limit=limit)
            with self.assertRaises(ValueError):
                parallel_module.parallel_tests('regex', 'm', 'basic', 't', test_limit=limit)


class TestParallelTests(QuietTestCase):
    def test_report_contains_every_failure(self):
        report = parallel_module.build_test_report('regex', 'basic', '0', ['1', '010', '10101'])
        text = report[0] if isinstance(report, tuple) else report
        for word in ['1', '010', '10101']:
            self.assertIn(repr(word), text)
        self.assertIn('Не пройдено: 3', text)

    def test_empty_tests_are_not_success(self):
        report = parallel_module.build_test_report('regex', 'basic', '1', [])
        self.assertIsInstance(report, tuple, 'Нужно вернуть (report, all_passed)')
        self.assertFalse(report[1])

    def test_all_passed_skips_review(self):
        info = {}
        with patch.object(parallel_module, 'local_request', side_effect=fake_responses([
            ('01(0101)*0|(1010)*1', 'stop', .1, 10), ('["1", "010"]', 'stop', .2, 7)
        ])) as ask:
            answer, cost, elapsed = parallel_module.parallel_tests('regex', 'm', 'basic', 'task', metrics=info)
        self.assertEqual(ask.call_count, 2, 'После успешных тестов третий запрос не нужен')
        self.assertEqual(answer, info['draft'])
        self.assertAlmostEqual(cost, .3)
        self.assertEqual(elapsed, 10)
        self.assertEqual(info['actual_total_time'], 17)
        self.assertFalse(info['repair_attempted'])

    def test_times_costs_and_all_failures_sent_to_review(self):
        info = {}
        with patch.object(parallel_module, 'local_request', side_effect=fake_responses([
            ('0', 'length', .1, 10), ('["1", "010", "10101"]', 'stop', .2, 20), ('partial', 'length', .3, 30)
        ])) as ask:
            with patch.object(parallel_module, 'finalize_answer', side_effect=[('0', .04, 4), ('1', .05, 5)]):
                answer, cost, elapsed = parallel_module.parallel_tests('regex', 'm', 'basic', 'task', metrics=info)
        self.assertEqual(answer, '1')
        self.assertEqual(elapsed, max(10 + 4, 20) + 30 + 5)
        self.assertEqual(info['actual_total_time'], 10 + 4 + 20 + 30 + 5)
        self.assertAlmostEqual(cost, .69)
        for word in ['1', '010', '10101']:
            self.assertIn(repr(word), ask.call_args_list[2].args[1])
        self.assertEqual(info['generated_tests'], ['1', '010', '10101'])

    def test_empty_review_keeps_draft(self):
        with patch.object(parallel_module, 'local_request', side_effect=fake_responses([
            ('0', 'stop', 0, 1), ('["1"]', 'stop', 0, 1), ('', 'stop', 0, 1)
        ])):
            self.assertEqual(parallel_module.parallel_tests('regex', 'm', 'basic', 'task')[0], '0')

    def test_format_error_not_success_even_if_words_reject(self):
        report = parallel_module.build_test_report('regex', 'basic', '(', ['00'])
        text = report[0] if isinstance(report, tuple) else report
        self.assertIn('Ошибка формата', text)
        if isinstance(report, tuple):
            self.assertFalse(report[1])


class TestLocalRequest(QuietTestCase):
    def request(self, parts, **kwargs):
        module = load_requester()
        response = MagicMock()
        response.iter_lines.return_value = [json.dumps(p).encode() if p else b'' for p in parts]
        with patch.object(module.requests, 'post') as post:
            post.return_value.__enter__.return_value = response
            result = module.local_request('m', 'task', 'prompt', **kwargs)
        return result, post.call_args.kwargs

    def test_stream_content_thinking_and_options(self):
        info = {}
        result, kwargs = self.request([
            {}, {'message': {'thinking': 'a'}}, {'message': {'thinking': 'b', 'content': '0'}},
            {'message': {'content': '1'}, 'done': True, 'done_reason': 'stop'}
        ], details=info, num_predict=512, think=False)
        self.assertEqual(result[:2], ('01', 0))
        self.assertEqual(info['thinking'], 'ab')
        self.assertEqual(info['done_reason'], 'stop')
        self.assertEqual(kwargs['json']['options']['num_predict'], 512)
        self.assertFalse(kwargs['json']['think'])

    def test_broken_stream_raises(self):
        with self.assertRaises(RuntimeError):
            self.request([{'message': {'content': 'partial'}}])

    def test_server_error_raises(self):
        with self.assertRaisesRegex(RuntimeError, 'model missing'):
            self.request([{'error': 'model missing'}])

    def test_null_content_is_empty(self):
        result, _ = self.request([{'message': {'content': None}, 'done': True, 'done_reason': 'stop'}])
        self.assertEqual(result[0], '')

    def test_source_routing(self):
        module = load_requester()
        self.assertIs(module.request_for('local'), module.local_request)
        self.assertIs(module.request_for('openrouter'), module.openrouter_request)
        with self.assertRaises(ValueError):
            module.request_for('wrong')





class TestCollectors(TemporaryFolderTestCase):
    pass


def collector_case(kind, pipeline, task_name):
    def test(self):
        module_name = 'experiment_regex' if kind == 'regex' else 'experiment_DFA_NFA'
        module = importlib.import_module('lab.experiments.' + module_name)
        collect = module.get_regex_answers if kind == 'regex' else module.get_answers
        def pipeline_answer(*args, **kwargs):
            received_kind = kwargs.get('kind', args[0] if args else None)
            self.assertEqual(received_kind, kind, 'Коллектор передал неправильный тип задачи')
            kwargs['metrics'].update(draft='DRAFT', repair_attempted=True)
            return 'FINAL', .25, 10.0
        ask = MagicMock(return_value=('FINAL', .25, 10.0))
        with patch.object(module, 'request_for', return_value=ask), \
             patch.object(module, 'repair', side_effect=pipeline_answer), \
             patch.object(module, 'parallel_tests', side_effect=pipeline_answer), \
             patch.object(module, 'save_attempt') as save, \
             patch.object(module, 'save_pipeline_artifacts') as artifacts, \
             redirect_stdout(io.StringIO()):
            result = collect('m', 1, task_name, 'local', pipeline=pipeline,
                             draft_limit=100, repair_limit=200, test_limit=50)
        self.assertEqual(result, (.25, 10.0))
        save.assert_called_once()
        self.assertEqual(save.call_args.args[2:4], (kind, task_name))
        self.assertEqual(save.call_args.args[4], 'FINAL' if pipeline == 'single' else 'DRAFT')
        self.assertEqual(save.call_args.args[5], 'FINAL')
        if pipeline == 'parallel_tests':
            artifacts.assert_called_once()
        if pipeline == 'single':
            ask.assert_called_once()
        else:
            ask.assert_not_called()
    return test


for kind in ['regex', 'automata']:
    for pipeline in ['single', 'repair', 'parallel_tests']:
        for task_name in tasks_alphabets:
            setattr(TestCollectors, f'test_{kind}_{pipeline}_{task_name.replace("-", "_")}',
                    collector_case(kind, pipeline, task_name))


class TestCommandLine(QuietTestCase):
    pass


def cli_case(kind, options, accepted):
    def test(self):
        runner = importlib.import_module('lab.run_experiment')
        experiment = runner.EXPERIMENTS[kind]
        argv = ['run_experiment', kind, 'm', '--iterations', '1'] + options
        with patch.object(sys, 'argv', argv), patch.object(experiment, 'run') as run, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if accepted:
                runner.main()
                run.assert_called_once()
                self.assertEqual(run.call_args.args[:2], ('m', 1))
                if '--pipeline' in options:
                    self.assertEqual(run.call_args.kwargs['pipeline'], options[options.index('--pipeline') + 1])
                if '--test-limit' in options:
                    self.assertEqual(run.call_args.kwargs['test_limit'], 512)
            else:
                with self.assertRaises(SystemExit) as error:
                    runner.main()
                self.assertNotEqual(error.exception.code, 0)
                run.assert_not_called()
    return test


from contextlib import redirect_stderr
cli_cases = [
    ([], True),
    (['--source', 'local'], True),
    (['--source', 'openrouter'], True),
    (['--source', 'local', '--pipeline', 'repair'], True),
    (['--source', 'local', '--pipeline', 'parallel_tests', '--test-limit', '512'], True),
    (['--iterations', '0'], False),
    (['--draft-limit', '0'], False),
    (['--repair-limit', '-2'], False),
    (['--source', 'bad'], False),
    (['--source', 'openrouter', '--pipeline', 'repair'], False),
]
for kind in ['regex', 'automata']:
    for index, (options, accepted) in enumerate(cli_cases):
        setattr(TestCommandLine, f'test_{kind}_{index:02d}', cli_case(kind, options, accepted))


class TestStatisticsCases(TemporaryFolderTestCase):
    pass


def stats_case(draft_correct, final_correct, seconds):
    def test(self):
        path = self.root / 'basic__000.txt'
        with patch.object(stats, 'checked_correct', side_effect=[draft_correct, final_correct]):
            stats.save_attempt(path, 0, 'regex', 'basic', 'DRAFT', 'FINAL', seconds, .02, True)
        saved = stats.load_statistics(self.root)['attempts']['0']
        self.assertIs(saved['draft_correct'], draft_correct)
        self.assertIs(saved['final_correct'], final_correct)
        self.assertEqual(saved['elapsed'], seconds)
        self.assertEqual(saved['cost'], .02)
        self.assertEqual(path.read_text(encoding="utf-8"), 'FINAL')
        self.assertTrue(stats.already_saved(path, 0))
        self.assertEqual(stats.load_statistics(self.root)['attempts']['0'], saved)
    return test


for draft_ok in [False, True]:
    for final_ok in [False, True]:
        for seconds in [0.0, .1, 10.0, 3600.0, 23748.0]:
            setattr(TestStatisticsCases, f'test_{draft_ok}_{final_ok}_{str(seconds).replace(".", "_")}',
                    stats_case(draft_ok, final_ok, seconds))


if __name__ == '__main__':
    unittest.main(verbosity=2)
