"""
    Signal management system for starting & stopping long term monitoring
    Copyright (C) 2021  Emerson Dove

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import typing

from typing import List

import blankly
from blankly.exchanges.exchange import Exchange
from blankly.strategy.signal_state import SignalState
from copy import deepcopy


class Signal:
    def __init__(self, exchange: Exchange,
                 evaluator: typing.Callable,
                 symbols: List[str],
                 init: typing.Callable = None,
                 teardown: typing.Callable = None,
                 formatter: typing.Callable = None):
        """
        Create a new signal.

        This heavily differs from Strategy objects. While a Strategy is optimized for the implementation of
         short or long-term trading strategies, a Signal is optimized for long-term monitoring & reporting of many
         symbols. Signals are designed to be scheduled to run over intervals of days & weeks. When deployed live,
         a signal-based script will only start when scheduled, then exit entirely.

        Args:
            exchange: An exchange object to construct the signal on
            evaluator: The function that can take information about a signal & classify that signal based on parameters
            symbols: A list of symbols to run on.
            init: Optional setup code to run when the program starts
            teardown: Optional teardown code to run before the program finishes
            formatter: Optional formatting function that pretties the results form the evaluator
        """

        self.exchange = exchange
        self.symbols = symbols

        # Store callables as a dictionary
        self.__callables = {
            'evaluator': evaluator,
            'init': init,
            'teardown': teardown,
            'formatter': formatter
        }
        self.interface = exchange.interface

        # Creat the signal state and pass in this signal object
        self.signal_state = SignalState(self)

        self.raw_results = {}
        self.formatted_results = {}

        self.__run()

    def __run(self):
        init = self.__callables['init']
        if callable(init):
            init(self.signal_state)

        # Evaluate using the evaluator function
        # 'symbol': {
        #     # This can all be custom
        #     'classification': 'pass/fail or True / False'
        #     'notes': {
        #         'custom_note': 'this stock was cool'
        #         'current_rsi': .45
        #     }
        # }

        evaluator = self.__callables['evaluator']
        if not callable(evaluator):
            raise TypeError("Must pass a callable for the evaluator.")

        for i in self.symbols:
            self.raw_results[i] = evaluator(i, self.signal_state)

        # Copy the evaluator results so that they can be formatted
        self.formatted_results = deepcopy(self.raw_results)

        formatter = self.__callables['formatter']
        if callable(formatter):
            # Mutate the copied dictionary
            self.formatted_results = formatter(self.formatted_results, self.signal_state)

        teardown = self.__callables['teardown']
        if callable(teardown):
            teardown(self.signal_state)

    def notify(self, output: str = None):
        """
        Send an email to your organization email. This only works while deployed live.

        output: Optionally fill this with a different string to notify with. If not filled it will notify using the
         formatted results evaluated on construction
        """
        use_str = self.formatted_results
        if output is not None:
            use_str = output

        blankly.reporter.email(use_str)
