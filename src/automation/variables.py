"""
Generator-backed variable system for serverless automation.

Variables support lazy evaluation via Python generators, allowing values to be
computed on demand, streamed, or composed into pipelines without eager loading.
"""

from typing import Any, Callable, Generator, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class GeneratorVariable:
    """
    A variable whose value is produced by a Python generator.

    Values are computed lazily: each call to ``next()`` or iteration
    yields the next value from the underlying generator factory.

    Examples::

        counter = GeneratorVariable(lambda: (i for i in range(10)))
        print(counter.next())   # 0
        print(counter.next())   # 1

        seq = GeneratorVariable.from_iterable([10, 20, 30])
        for v in seq:
            print(v)
    """

    def __init__(self, factory: Callable[[], Generator]) -> None:
        """
        Args:
            factory: Zero-argument callable that returns a fresh generator
                     each time the variable is reset or first accessed.
        """
        self._factory = factory
        self._gen: Optional[Iterator] = None
        self._peeked: bool = False
        self._peeked_value: Any = None

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def _ensure_gen(self) -> Iterator:
        if self._gen is None:
            self._gen = self._factory()
        return self._gen

    def next(self, default: Any = None) -> Any:
        """Return the next value, or *default* when the generator is exhausted."""
        if self._peeked:
            self._peeked = False
            return self._peeked_value
        try:
            return next(self._ensure_gen())
        except StopIteration:
            return default

    def reset(self) -> "GeneratorVariable":
        """Restart the generator from the beginning."""
        self._gen = self._factory()
        self._peeked = False
        self._peeked_value = None
        return self

    def peek(self) -> Any:
        """
        Return the next value without advancing the generator.

        Consecutive calls to ``peek()`` return the same value until
        ``next()`` or iteration consumes it.  Returns ``None`` when
        the generator is exhausted.
        """
        if self._peeked:
            return self._peeked_value
        try:
            self._peeked_value = next(self._ensure_gen())
            self._peeked = True
            return self._peeked_value
        except StopIteration:
            return None

def collect(self) -> list:
    """Drain all remaining values into a list."""
    values: list[Any] = []
    if self._peeked:
        values.append(self._peeked_value)
        self._peeked = False
        self._peeked_value = None
    values.extend(list(self._ensure_gen()))
    return values

    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------

    def map(self, fn: Callable[[Any], Any]) -> "GeneratorVariable":
        """Return a new variable that applies *fn* to each value."""
        source_factory = self._factory

        def _mapped():
            for v in source_factory():
                yield fn(v)

        return GeneratorVariable(_mapped)

    def filter(self, predicate: Callable[[Any], bool]) -> "GeneratorVariable":
        """Return a new variable that yields only values matching *predicate*."""
        source_factory = self._factory

        def _filtered():
            for v in source_factory():
                if predicate(v):
                    yield v

        return GeneratorVariable(_filtered)

    def take(self, n: int) -> "GeneratorVariable":
        """Return a new variable limited to the first *n* values."""
        source_factory = self._factory

        def _taken():
            for i, v in enumerate(source_factory()):
                if i >= n:
                    break
                yield v

        return GeneratorVariable(_taken)

    def chain(self, other: "GeneratorVariable") -> "GeneratorVariable":
        """Concatenate this variable with *other*."""
        a_factory = self._factory
        b_factory = other._factory

        def _chained():
            yield from a_factory()
            yield from b_factory()

        return GeneratorVariable(_chained)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_iterable(cls, iterable: Iterable) -> "GeneratorVariable":
        """Create a variable that replays a fixed iterable on each reset."""
        items = list(iterable)
        return cls(lambda: iter(items))

    @classmethod
    def from_value(cls, value: Any) -> "GeneratorVariable":
        """Create a variable that yields a single value once."""
        return cls(lambda: iter([value]))

    @classmethod
    def constant(cls, value: Any) -> "GeneratorVariable":
        """Create an infinite variable that always yields *value*."""

        def _infinite():
            while True:
                yield value

        return cls(_infinite)

    @classmethod
    def counter(cls, start: int = 0, step: int = 1) -> "GeneratorVariable":
        """Create an infinite counter variable."""

        def _count():
            n = start
            while True:
                yield n
                n += step

        return cls(_count)

    # ------------------------------------------------------------------
    # Python protocol support
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Any:
        if self._peeked:
            self._peeked = False
            return self._peeked_value
        return next(self._ensure_gen())

    def __repr__(self) -> str:
        return f"GeneratorVariable(factory={self._factory!r})"


class VariableRegistry:
    """
    Named registry of :class:`GeneratorVariable` instances.

    Allows automation components to share and look up variables by name.
    """

    def __init__(self) -> None:
        self._vars: dict[str, GeneratorVariable] = {}

    def register(self, name: str, variable: GeneratorVariable) -> "VariableRegistry":
        """Register *variable* under *name*. Returns self for chaining."""
        self._vars[name] = variable
        return self

    def define(self, name: str, factory: Callable[[], Generator]) -> GeneratorVariable:
        """Create a :class:`GeneratorVariable` from *factory* and register it."""
        var = GeneratorVariable(factory)
        self._vars[name] = var
        return var

    def get(self, name: str) -> Optional[GeneratorVariable]:
        """Return the variable registered as *name*, or ``None``."""
        return self._vars.get(name)

    def require(self, name: str) -> GeneratorVariable:
        """Return the variable registered as *name*; raise ``KeyError`` if absent."""
        if name not in self._vars:
            raise KeyError(f"Variable '{name}' not found in registry")
        return self._vars[name]

    def names(self) -> list[str]:
        """Return the list of registered variable names."""
        return list(self._vars.keys())

    def reset_all(self) -> None:
        """Reset every registered variable to its initial state."""
        for var in self._vars.values():
            var.reset()

    def __contains__(self, name: str) -> bool:
        return name in self._vars

    def __len__(self) -> int:
        return len(self._vars)

    def __repr__(self) -> str:
        return f"VariableRegistry({list(self._vars.keys())!r})"
