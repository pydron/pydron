from __future__ import print_function
__author__ = 'Roman Bolzern'

#: Set of callables that are assumed to be functional even without having a
#: `@functional` decorator.
functional_whitelist = {len, print}
