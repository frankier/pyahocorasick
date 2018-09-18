import ahocorasick
from copy import copy


class TokenAutomatonSearchIter(object):
    def __init__(self, wrapped, index):
        self.wrapped = wrapped
        self.index = index

    def is_root(self):
        return self.wrapped.is_root()

    def pos_id(self):
        return self.wrapped.pos_id()

    def set(self, string, *reset):
        self.wrapped.set(self.index.convert_key(string), *reset)

    def __copy__(self):
        return TokenAutomatonSearchIter(copy(self.wrapped), self.index)

    def __iter__(self):
        return self.wrapped


class TokenIndex(object):
    def __init__(self):
        self.tokens = [None]
        self.index = {None: 0}

    def add_get_token(self, token):
        if token in self.index:
            return self.index[token]
        idx = len(self.tokens)
        self.index[token] = idx
        self.tokens.append(token)
        return idx

    def get_token(self, token):
        return self.index.get(token, 0)

    def _convert_key(self, key, getter):
        lst = []
        for token in key:
            lst.append(getter(token))
        return tuple(lst)

    def convert_key(self, key):
        return self._convert_key(key, self.get_token)

    def convert_add_key(self, key):
        return self._convert_key(key, self.add_get_token)


class TokenAutomaton(object):
    """
    Implements a similar interface to Automaton, but instead of dealing with
    strings or tuples of integers, deals with tuples of tokens, that is strings
    picked from some vocabulary.
    """

    def __init__(self, store=ahocorasick.STORE_ANY):
        self.index = TokenIndex()
        self.wrapped = ahocorasick.Automaton(store, ahocorasick.KEY_SEQUENCE)

    def add_word(self, key, value):
        self.wrapped.add_word(self.index.convert_add_key(key), value)

    def iter(self, haystack, *args, **kwargs):
        print("In iter")
        return TokenAutomatonSearchIter(
            self.wrapped.iter(self.index.convert_key(haystack), *args, **kwargs),
            self.index
        )


def mk_index_wrapped_meth(method_name):
    def wrapper(self, key, *args, **kwargs):
        wrapped = getattr(self.wrapped, method_name)
        print("method_name", method_name)
        return wrapped(self.index.convert_key(key), *args, **kwargs)
    return wrapper


for method_name in [
    "exists", "match", "get", "keys", "values", "items"
]:
    setattr(TokenAutomaton, method_name, mk_index_wrapped_meth(method_name))


def mk_plain_wrapped_meth(method_name):
    def wrapper(self, *args, **kwargs):
        wrapped = getattr(self.wrapped, method_name)
        print("method_name", method_name)
        return wrapped(*args, **kwargs)
    return wrapper


for method_name in [
    "clear",
    "make_automaton",
    "get_stats",
    "dump",
]:
    setattr(TokenAutomaton, method_name, mk_plain_wrapped_meth(method_name))


def conf_net_search(auto, conf_net):
    """
    Searches a confusion network (encoded as an iterable of iterables) with an
    Aho-Corasick Automaton (ACA). It does this by keeping several pointers into
    the ACA. Pointer uniqueness is maintained.

    Theoretically, we can remove dominated nodes, which are redundant, Given
    some pointer which has a some route r_1 from the start node, it is
    dominated by a pointer with route r_2 from the start node if r_1 is a
    suffix of r_2 and r_2 is longer than r_1. So if we have pointers and routes
    like so:

    start->a->b->c->pointer 1
    start->b->c->pointer 2
    start->c->pointer 3

    Then pointers 2 and 3 are dominated by pointer 1 and pointer 3 is dominated
    by pointer 2. This means that all pointers apart from pointer 1 are
    redundant.

    Currently, this isn't fully utilised. Instead, the root is removed if there
    are any other pointers, which is the trivial example of this case.
    """
    root = auto.iter(())
    root_id = root.pos_id()
    auto_its = [root]

    for opts in conf_net:
        # Don't add the root pointer to begin with
        seen_auto_its = {root_id}
        next_auto_its = []
        # We can get duplicates with the current scheme, so filter
        elems = set()
        # Save the current root to ensure the right character index
        cur_root = None
        for auto_it in auto_its:
            for opt in opts:
                new_auto_it = copy(auto_it)
                new_auto_it.set((opt,))
                for elem in new_auto_it:
                    if new_auto_it.pos_id() in next_auto_its:
                        break
                    elems.add(elem)
                if new_auto_it.pos_id() not in seen_auto_its:
                    seen_auto_its.add(new_auto_it.pos_id())
                    next_auto_its.append(new_auto_it)
                elif new_auto_it.pos_id() == root_id:
                    cur_root = new_auto_it
        for elem in elems:
            yield elem
        # If we end up with nothing, add back the root
        if len(next_auto_its) == 0:
            next_auto_its.append(cur_root)
        auto_its = next_auto_its
