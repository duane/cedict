YTP_INTERNAL_BUF_CAPACITY = 5
import unicodedata
import pdb


class RingBufSizedString:
    """
    A circular buffer implementation with a fixed maximum size.

    Attributes:
        max_size (int): The maximum size of the buffer.
        buf (list): The buffer to store items.
        writer (int): The index of the writer position.
        reader (int): The index of the reader position.
        count (int): The number of items currently in the buffer.
    """

    def __init__(self, max_size):
        """
        Initializes a RingBufSizedString object.

        Args:
            max_size (int): The maximum size of the buffer.
        """
        self.max_size = max_size
        self.buf = [None] * max_size
        self.writer = 0
        self.reader = 0
        self.count = 0

    def __getitem__(self, key):
        if isinstance(key, slice):
            # Get the start, stop, and step from the slice
            return [self[ii] for ii in range(*key.indices(len(self)))]
        elif isinstance(key, int):
            if key >= self.max_size:
                raise IndexError
            item = self.buf[(self.reader + key) % self.max_size]
            if not item:
                raise IndexError
            return item
        else:
            raise TypeError("Invalid argument type.")

    def __len__(self):
        if self.reader == self.writer:
            return self.count
        cmp = self.writer - self.reader
        if cmp < 0:
            cmp += 5
        return cmp

    def append(self, item):
        """
        Appends an item to the buffer.

        Args:
            item: The item to be appended.
        """
        self.buf[self.writer] = item
        if self.count < self.max_size:
            self.count += 1
        self.advance_writer()

    def append_with_output(self, item):
        """
        Appends an item to the buffer.

        Args:
            item: The item to be appended.
        """
        result = None
        if self.count < self.max_size:
            self.count += 1
        else:
            result = self.buf[self.writer]
        self.buf[self.writer] = item
        self.advance_writer()
        return result

    def pop(self):
        """
        Removes and returns the item at the reader position.

        Returns:
            The item at the reader position.
        """
        item = self.buf[self.reader]
        self.buf[self.reader] = None
        self.advance_reader()
        self.count -= 1
        return item

    def advance_reader(self):
        """
        Advances the reader position.

        Returns:
            bool: True if the reader position was advanced, False otherwise.
        """
        self.reader = (self.reader + 1) % self.max_size

    def advance_writer(self):
        """
        Advances the writer position.
        """
        if self.writer == self.reader and self.count == self.max_size:
            self.advance_reader()
        self.writer = (self.writer + 1) % self.max_size

    def in_order(self):
        return [c for c in self.buf[self.reader :] + self.buf[: self.reader] if c]

    def __str__(self):
        return "".join(self.in_order())


def is_tonable_char(char):
    return char in "aeiouAEIOU"


def is_tone_digit_char(char):
    return char in "012345"


def idx_for_tone(vowels):
    vowels = [c.lower() for c in vowels]
    if vowels[0] in "ae":
        return 0
    if vowels[0:2] == ["o", "u"]:
        return 0
    if vowels[0:3] in [["i", "a", "o"], ["u", "a", "i"]]:
        return 1
    if len(vowels) > 1 and is_tonable_char(vowels[1]):
        if len(vowels) > 2 and is_tonable_char(vowels[2]):
            return 2
        return 1
    return 0


def tone_combining_diactric_mark_for_digit(digit):
    if digit == "0" or digit == "5":
        return ""
    if digit == "1":
        return "\u0304"
    if digit == "2":
        return "\u0301"
    if digit == "3":
        return "\u0306"
    if digit == "4":
        return "\u0300"


class TonePlacementBuf:
    def __init__(self, start=""):
        self.buf = list(start)
        self.searching_for_digit = False

    def process_fully(self, s):
        for c in s:
            for output in self.append_with_output(c):
                yield output
        for toned in self.flush():
            yield toned

    def convert_string(self, s):
        return "".join(self.process_fully(s))

    def append_with_output(self, c):
        if is_tonable_char(c):
            self.searching_for_digit = True
            self.buf.append(c)
        elif is_tone_digit_char(c) and self.searching_for_digit:
            for toned in self.flush(c):
                yield toned
        elif self.searching_for_digit and c in "ngNG":
            if len(self.buf) > 5:
                for too_large in self.flush():
                    yield too_large
                self.buf = []
                yield c
            else:
                self.buf.append(c)
        else:
            for toned in self.flush():
                yield toned
            self.buf = []
            yield c

    def append(self, item):
        self.buf.append(item)

    def has_tonable(self):
        return len(self.buf) > 0

    def spliced_tone(self, idx, tone):
        return unicodedata.normalize(
            "NFC", "".join(self.buf[: idx + 1]) + tone + "".join(self.buf[idx + 1 :])
        )

    def spliced_combining_diacritic(self, tone):
        return self.spliced_tone(idx_for_tone(self.buf), tone)

    def spliced_tone_digit(self, digit):
        return self.spliced_combining_diacritic(
            tone_combining_diactric_mark_for_digit(digit)
        )

    def flush(self, tone_digit="5"):
        if self.buf:
            result = self.spliced_tone_digit(tone_digit)
            self.buf = []
            return result
        self.searching_for_digit = False
        return []

    def __repr__(self):
        return repr(self.buf.in_order())


def digit_to_diacritic(in_buf):
    # buffer = RingBufSizedString(5)
    return TonePlacementBuf().process_fully(in_buf)


def s_digit_to_diacritic(in_buf):
    return "".join(c for c in digit_to_diacritic(in_buf))
