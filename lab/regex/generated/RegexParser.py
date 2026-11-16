# Generated from Regex.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,5,38,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,1,0,1,0,1,0,1,1,
        1,1,1,1,5,1,17,8,1,10,1,12,1,20,9,1,1,2,4,2,23,8,2,11,2,12,2,24,
        1,3,1,3,3,3,29,8,3,1,4,1,4,1,4,1,4,1,4,3,4,36,8,4,1,4,0,0,5,0,2,
        4,6,8,0,0,36,0,10,1,0,0,0,2,13,1,0,0,0,4,22,1,0,0,0,6,26,1,0,0,0,
        8,35,1,0,0,0,10,11,3,2,1,0,11,12,5,0,0,1,12,1,1,0,0,0,13,18,3,4,
        2,0,14,15,5,1,0,0,15,17,3,4,2,0,16,14,1,0,0,0,17,20,1,0,0,0,18,16,
        1,0,0,0,18,19,1,0,0,0,19,3,1,0,0,0,20,18,1,0,0,0,21,23,3,6,3,0,22,
        21,1,0,0,0,23,24,1,0,0,0,24,22,1,0,0,0,24,25,1,0,0,0,25,5,1,0,0,
        0,26,28,3,8,4,0,27,29,5,2,0,0,28,27,1,0,0,0,28,29,1,0,0,0,29,7,1,
        0,0,0,30,36,5,5,0,0,31,32,5,3,0,0,32,33,3,2,1,0,33,34,5,4,0,0,34,
        36,1,0,0,0,35,30,1,0,0,0,35,31,1,0,0,0,36,9,1,0,0,0,4,18,24,28,35
    ]

class RegexParser ( Parser ):

    grammarFileName = "Regex.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'|'", "'*'", "'('", "')'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "SYMBOL" ]

    RULE_start = 0
    RULE_expression = 1
    RULE_concatenation = 2
    RULE_repetition = 3
    RULE_atom = 4

    ruleNames =  [ "start", "expression", "concatenation", "repetition", 
                   "atom" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    SYMBOL=5

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class StartContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expression(self):
            return self.getTypedRuleContext(RegexParser.ExpressionContext,0)


        def EOF(self):
            return self.getToken(RegexParser.EOF, 0)

        def getRuleIndex(self):
            return RegexParser.RULE_start

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStart" ):
                listener.enterStart(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStart" ):
                listener.exitStart(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStart" ):
                return visitor.visitStart(self)
            else:
                return visitor.visitChildren(self)




    def start(self):

        localctx = RegexParser.StartContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_start)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 10
            self.expression()
            self.state = 11
            self.match(RegexParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExpressionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def concatenation(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(RegexParser.ConcatenationContext)
            else:
                return self.getTypedRuleContext(RegexParser.ConcatenationContext,i)


        def getRuleIndex(self):
            return RegexParser.RULE_expression

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpression" ):
                listener.enterExpression(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpression" ):
                listener.exitExpression(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpression" ):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)




    def expression(self):

        localctx = RegexParser.ExpressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_expression)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 13
            self.concatenation()
            self.state = 18
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==1:
                self.state = 14
                self.match(RegexParser.T__0)
                self.state = 15
                self.concatenation()
                self.state = 20
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ConcatenationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def repetition(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(RegexParser.RepetitionContext)
            else:
                return self.getTypedRuleContext(RegexParser.RepetitionContext,i)


        def getRuleIndex(self):
            return RegexParser.RULE_concatenation

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterConcatenation" ):
                listener.enterConcatenation(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitConcatenation" ):
                listener.exitConcatenation(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitConcatenation" ):
                return visitor.visitConcatenation(self)
            else:
                return visitor.visitChildren(self)




    def concatenation(self):

        localctx = RegexParser.ConcatenationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_concatenation)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 22 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 21
                self.repetition()
                self.state = 24 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==3 or _la==5):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RepetitionContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def atom(self):
            return self.getTypedRuleContext(RegexParser.AtomContext,0)


        def getRuleIndex(self):
            return RegexParser.RULE_repetition

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRepetition" ):
                listener.enterRepetition(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRepetition" ):
                listener.exitRepetition(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRepetition" ):
                return visitor.visitRepetition(self)
            else:
                return visitor.visitChildren(self)




    def repetition(self):

        localctx = RegexParser.RepetitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_repetition)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 26
            self.atom()
            self.state = 28
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==2:
                self.state = 27
                self.match(RegexParser.T__1)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SYMBOL(self):
            return self.getToken(RegexParser.SYMBOL, 0)

        def expression(self):
            return self.getTypedRuleContext(RegexParser.ExpressionContext,0)


        def getRuleIndex(self):
            return RegexParser.RULE_atom

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterAtom" ):
                listener.enterAtom(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitAtom" ):
                listener.exitAtom(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAtom" ):
                return visitor.visitAtom(self)
            else:
                return visitor.visitChildren(self)




    def atom(self):

        localctx = RegexParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_atom)
        try:
            self.state = 35
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [5]:
                self.enterOuterAlt(localctx, 1)
                self.state = 30
                self.match(RegexParser.SYMBOL)
                pass
            elif token in [3]:
                self.enterOuterAlt(localctx, 2)
                self.state = 31
                self.match(RegexParser.T__2)
                self.state = 32
                self.expression()
                self.state = 33
                self.match(RegexParser.T__3)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





