# Generated from Regex.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .RegexParser import RegexParser
else:
    from RegexParser import RegexParser

# This class defines a complete listener for a parse tree produced by RegexParser.
class RegexListener(ParseTreeListener):

    # Enter a parse tree produced by RegexParser#start.
    def enterStart(self, ctx:RegexParser.StartContext):
        pass

    # Exit a parse tree produced by RegexParser#start.
    def exitStart(self, ctx:RegexParser.StartContext):
        pass


    # Enter a parse tree produced by RegexParser#expression.
    def enterExpression(self, ctx:RegexParser.ExpressionContext):
        pass

    # Exit a parse tree produced by RegexParser#expression.
    def exitExpression(self, ctx:RegexParser.ExpressionContext):
        pass


    # Enter a parse tree produced by RegexParser#concatenation.
    def enterConcatenation(self, ctx:RegexParser.ConcatenationContext):
        pass

    # Exit a parse tree produced by RegexParser#concatenation.
    def exitConcatenation(self, ctx:RegexParser.ConcatenationContext):
        pass


    # Enter a parse tree produced by RegexParser#repetition.
    def enterRepetition(self, ctx:RegexParser.RepetitionContext):
        pass

    # Exit a parse tree produced by RegexParser#repetition.
    def exitRepetition(self, ctx:RegexParser.RepetitionContext):
        pass


    # Enter a parse tree produced by RegexParser#atom.
    def enterAtom(self, ctx:RegexParser.AtomContext):
        pass

    # Exit a parse tree produced by RegexParser#atom.
    def exitAtom(self, ctx:RegexParser.AtomContext):
        pass



del RegexParser