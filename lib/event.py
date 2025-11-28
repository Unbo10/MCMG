
from fractions import Fraction
from typing import List, Sequence, Tuple

from .note import Note

"""
Contains all the information of a single note (including a silence) or chord,
i.e., a list whose first entry is a list of Note objects, and whose second
entry refers to the timing of the note/chord, since it contains:
- its type (as a fraction, check `Parser`'s `type_to_frac`)
- its duration.
Using this class, you can: determine quickly if an event in one or multiple
parsed sheets is a chord or a note, represent it as a comprehensible string,
determine whether two events are equal.
"""
class Event:
    def __init__(
        self,
        notes: Sequence[Note],
        timing: Tuple[Fraction, str | None],
    ) -> None:
        if not notes:
            raise ValueError("Event requires at least one note/rest entry")

        self.notes: List[Note] = list(notes)
        self.type: Fraction = timing[0]
        self.duration: str | None = timing[1]
        self.repr_str: str = None

    @property
    def is_chord(self) -> bool:
        return len(self.notes) > 1

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Event):
            return False
        return (
            self.notes == value.notes
            and self.type == value.type
            and self.duration == value.duration
        )

    def __repr__(self) -> str:
        if self.repr_str is None:
            repr_str: str = ""
            for note in self.notes:
                repr_str += str(note) + ">"
            # repr_str = repr_str[:-1] #*keep the last > to distinguish between notes and timing
            repr_str += f">{self.type.numerator}/{self.type.denominator}|{self.duration}"
            self.repr_str = repr_str
        
        return self.repr_str
    
if __name__ == "__main__":
    #!Run (from root) as python -m lib.event
    event1 = Event(notes=[Note(('F', 4), 'R', '', '', '')], timing=(Fraction(1, 2), '4'))
    event2 = Event(notes=[Note(('F', 4), 'G', '#', '3', ['staccato']), Note(('F', 4), 'B', '', '3', [''])], timing=(Fraction(1, 8), '1'))
    print(event1)
    print(event2)
