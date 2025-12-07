
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
            notes_repr = ">".join(str(note) for note in self.notes)
            self.repr_str = f"{notes_repr}>>{self.type.numerator}/{self.type.denominator}|{self.duration}"
        return self.repr_str

    @classmethod
    def from_string(cls, event_str: str) -> "Event":
        """
        From a string that follows the format s1>s2>...>sn>>type|duration,
        where si is a string of the format
        
        (note_name,octave)note_name,accidental,octave|articulations

        without the commas. The first parenthesis contains info about the clef,
        and articulations are separated by commas if there are multiple.
        """
        notes_part, sep, timing_part = event_str.rpartition(">>")
        if sep == "":
            raise ValueError(f"Invalid event string: {event_str}")

        #*Get notes separated by >
        note_strings = [n for n in notes_part.split(">") if n]
        if not note_strings:
            raise ValueError(f"No notes found in event string: {event_str}")
        notes = [Note.from_string(ns) for ns in note_strings]

        #*The symbol | marks the start of the articulations (if there are any)
        frac_part, sep, duration_part = timing_part.partition("|")
        if sep == "":
            raise ValueError(f"Invalid timing in event string: {event_str}")
        note_type = Fraction(frac_part)
        duration = duration_part if duration_part != "None" else None

        return cls(notes, (note_type, duration))

    # def copy(self) -> "Event":
    #     return Event([note.copy() for note in self.notes], (Fraction(self.type), self.duration))


if __name__ == "__main__":
    #!Run (from root) as python -m lib.event
    event1 = Event(notes=[Note(('F', 4), 'R', '', '', '')], timing=(Fraction(1, 2), '4'))
    event2 = Event(notes=[Note(('F', 4), 'G', '#', '3', ['staccato']), Note(('F', 4), 'B', '', '3', [''])], timing=(Fraction(1, 8), '1'))
    print(event1)
    print(Event.from_string(str(event1)))
    print(event2)
    print(Event.from_string(str(event2)))
