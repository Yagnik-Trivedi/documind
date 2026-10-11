"""Streaming-safe filters for model output."""


def _partial_suffix(s: str, tag: str) -> int:
    """Length of the longest suffix of s that is a proper prefix of tag."""
    for n in range(min(len(tag) - 1, len(s)), 0, -1):
        if s.endswith(tag[:n]):
            return n
    return 0


class ThinkStripper:
    """Removes <think>...</think> reasoning blocks from a token stream, even when the tags are
    split across chunks ("<thi" + "nk>"). Leading whitespace of the visible answer is dropped."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.buf = ""
        self.in_think = False
        self.started = False

    def feed(self, text: str) -> str:
        self.buf += text
        out: list[str] = []
        while True:
            if self.in_think:
                i = self.buf.find(self.CLOSE)
                if i == -1:
                    keep = _partial_suffix(self.buf, self.CLOSE)
                    self.buf = self.buf[-keep:] if keep else ""
                    break
                self.buf = self.buf[i + len(self.CLOSE) :]
                self.in_think = False
            else:
                i = self.buf.find(self.OPEN)
                if i == -1:
                    keep = _partial_suffix(self.buf, self.OPEN)
                    visible = self.buf[: len(self.buf) - keep]
                    self.buf = self.buf[len(self.buf) - keep :]
                    out.append(visible)
                    break
                out.append(self.buf[:i])
                self.buf = self.buf[i + len(self.OPEN) :]
                self.in_think = True
        return self._emit("".join(out))

    def flush(self) -> str:
        rest = "" if self.in_think else self.buf
        self.buf = ""
        return self._emit(rest)

    def _emit(self, text: str) -> str:
        if not self.started:
            text = text.lstrip()
            if text:
                self.started = True
        return text
