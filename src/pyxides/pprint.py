from dataclasses import dataclass
from typing import Union, Callable


@dataclass(repr=False)
class PrettyPrinter:
    """
    Flexible string representation for list-like containers.  This object can
    act as a replacement for the builtin `__repr__` or `__str__` methods.
    Inherit from `PrettyPrinter` to get pretty representations of
    your container built in.
    """

    max_width: str = 120
    edge_items: str = 2
    wrap: bool = True
    max_items: int = 20
    max_lines: int = 10
    per_line: Union[int, None] = None
    sep: str = ', '
    brackets: str = '[]'
    show_size: bool = True
    alias: Union[str, None] = None
    item_str: Callable = str
    trunc: str = ' ... '
    hang: bool = False
    indent: None = None
    # fmt: str = '{pre}: {joined}'

    def __post_init__(self):
        # self.parent = parent
        # self.name = alias or parent.__class__.__name__

        # Check brackets ok
        if len(self.brackets) in (0, 1):
            self.brackets = (self.brackets, ) * 2
        self.brackets = tuple(self.brackets)
        assert len(self.brackets) == 2

        #
        # if '\n' in self.sep:
        #     self.per_line = 1
        #     self.sep = self.sep.replace('\n', ' ')

    def __call__(self, l):
        pre = self.pre(l)
        if self.indent is None:
            self.indent = len(pre)
        return pre + self.joined(l)

        # **self.__dict__,
        # **{name: p.fget(self) for name, p in
        #    inspect.getmembers(self.__class__, is_property)})

    # def __str__(self):
    #     return self()

    # def __repr__(self):
    #     return self()

    # @property
    def sized(self, l):
        if self.show_size:
            return f'(size {len(l)})'
        return ''

    # @property
    def pre(self, l):
        name = self.alias or l.__class__.__name__
        return f'{name}{self.sized(l)}: '

    # @property
    def joined(self, l):

        # first check if more than one line needed for repr
        sep = self.sep
        ei = self.edge_items
        mw = self.max_width
        n_per_line = self.per_line
        size = len(l)

        # guess how many per line if not requested
        if (size > 0) and (n_per_line is None):
            # note this logic for fixed width items
            first = self.item_str(l[0])
            n_per_line = mw // (len(first) + len(sep))

        # # repr fits into a single line
        # if size <= n_per_line:
        #     return self.trunc.join(
        #         (self._joined(l[:ei]),
        #          self._joined(l[-ei:]))
        #     ).join(self.brackets)

        if (size <= n_per_line) or not self.wrap:
            return self._joined(l).join(self.brackets)

        # check if we need to truncate
        fmt = self.item_str
        mx = self.max_items
        if size > mx:
            ei = self.edge_items
            l = (*map(fmt, l[:(mx - ei)]),
                 '...',
                 *map(fmt, l[-ei:]))
            return self.wrapped(list(l), self.indent).join(self.brackets)

        # need wrapped repr
        l = list(map(fmt, l))
        return self.wrapped(l, self.indent).join(self.brackets)

    def wrapped(self, l, indent=0):
        # get wrapped repr

        ei = self.edge_items
        mw = self.max_width
        npl = self.per_line
        sep = self.sep

        loc = indent
        line_count = 1  # start counting here so we break 1 line early
        end = self.max_items - ei
        newline = '\n' + ' ' * indent
        s = newline * self.hang
        for i, item in enumerate(l):
            items_per_line = npl or round(i / line_count)
            if line_count - items_per_line >= self.max_lines:
                s += self.wrapped([self.trunc] + l[-ei:], indent)
                break

            # check if we should go to the next line
            if i and (npl and (i % npl == 0) or loc + len(item) > mw):
                # if len(si) > mw:
                #     'problem'

                s += newline
                loc = indent
                line_count += 1

            s += item + sep
            loc = len(s) % mw

        return s.strip(sep)

    def _joined(self, items):
        return self.sep.join(map(str, (map(self.item_str, items))))


class PPrintContainer:
    # """
    # If you inherit from this class, add
    # >>> self._repr = ReprContainer(self)
    # to your `__init__` method, and add  whatever option you want for the
    # representation. If your container is an attribute of another class, use
    # >>> self._repr = ReprContainer(self.data)
    # where 'self.data' is the container you want to represent
    # """

    # default pprint
    pretty = PrettyPrinter()

    def __repr__(self):
        return self.pretty(self)

    def __str__(self):
        return self.pretty(self)