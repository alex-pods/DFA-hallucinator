from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener

from lab.regex.generated.RegexLexer import RegexLexer
from lab.regex.generated.RegexParser import RegexParser


class RegexErrorListener(ErrorListener) :
    def __init__(self) :
        self.has_error = False

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e) :
        self.has_error = True


def parse_regex(text : str, alphabet) :
    error_listener = RegexErrorListener()

    lexer = RegexLexer(InputStream(text.strip()))
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    tokens = CommonTokenStream(lexer)
    tokens.fill()

    if error_listener.has_error :
        return "invalid regex format"

    alphabet = set(alphabet)

    for token in tokens.tokens :
        if token.type == RegexLexer.SYMBOL and token.text not in alphabet :
            return "unexpected alphabet symbol"

    parser = RegexParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    tree = parser.start()

    if error_listener.has_error :
        return "invalid regex format"

    return tree

if __name__ == "__main__" :
    examples = [
        "0*1",
        "(0|1)*1",
        "0|",
        "(0|1",
        "0@1",
        "0|a",
        ""
    ]

    for text in examples :
        result = parse_regex(text, ["0", "1"])

        if isinstance(result, str) :
            print(repr(text), "->", result)
        else :
            print(repr(text), "-> корректный формат")