from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple

"""
Immutable class that represents a single parsed note/rest from `Parser`'s
`parse_to_dict`. It contains all the info from a note except its timing:
- its clef (as a tuple (note, line or octave))
- its name (A to G or R).
- its accidental (see `Parser`'s `alter_to_acc`)
- its octave (-2 to 7).
- its articulations (check musicxml's docs)
With this class, you can determine quickly if a note is a rest, if two notes
are equal, and you can print it in a more natural format.
"""
@dataclass
class Note:
    """Represents a single parsed note/rest entry emitted by the parser."""

    clef: Tuple[str, int]
    name: str
    accidental: str
    octave: str
    articulations: Tuple[str, ...] = field(default_factory=tuple)
    repr_str: str = None

    @property
    def is_rest(self) -> bool:
        return self.name == "R"
    
    def __eq__(self, value):
        if not isinstance(value, Note):
            return False
        return (
            self.clef == value.clef and
            self.name == value.name and
            self.accidental == value.accidental and
            self.octave == value.octave and
            self.articulations == value.articulations
        )
    
    def __repr__(self) -> str:
        if self.repr_str is None:
            base = f"({self.clef[0]},{self.clef[1]}){self.name}{self.accidental}{self.octave}|"
            if self.articulations:
                base += ",".join(self.articulations)
            self.repr_str = base
        return self.repr_str

    @classmethod
    def from_string(cls, note_str: str) -> "Note":
        """
        From a string that follows the format
        
        (note_name,octave)note_name,accidental,octave|articulations

        without the commas. The first parenthesis contains info about the clef,
        and articulations are separated by commas if there are multiple.
        """
        if not note_str:
            raise ValueError("Empty note string")

        #*Get the info about the clef (inside parenthesis)
        clef_part, sep, remainder = note_str.partition(')')
        if sep == '':
            raise ValueError(f"Invalid note string: {note_str}")
        clef_content = clef_part.lstrip('(')
        clef_sign, clef_line = clef_content.split(',')
        clef = (clef_sign, int(clef_line))

        pitch_part, sep, articulation_part = remainder.partition('|')
        if sep == '':
            raise ValueError(f"Invalid note string: {note_str}")

        if not pitch_part:
            raise ValueError(f"Missing pitch info in note string: {note_str}")

        name = pitch_part[0]
        accidental = ''
        octave = pitch_part[1:]

        #*This follows the conventions in Parser
        #*The octave and the note name are gauranteed to be a single character
        #*so the rest is the accidental (will remain empty if there isn't)
        if name != 'R':
            if octave.startswith('bb'):
                accidental = 'bb'
                octave = octave[2:]
            elif octave.startswith(('x', '#', 'b')):
                accidental = octave[0]
                octave = octave[1:]

        #*Get the articulations separated by commas
        articulations = tuple(filter(None, articulation_part.split(','))) if articulation_part else tuple()
        return cls(clef, name, accidental, octave, articulations)

    # def copy(self) -> "Note":
    #     return Note(
    #         clef=(self.clef[0], self.clef[1]),
    #         name=self.name,
    #         accidental=self.accidental,
    #         octave=self.octave,
    #         articulations=tuple(self.articulations) #*returns the original tuple or a shallow copy of it
    #     )

    def to_midi_number(self) -> int | None:
        """
        Mapping from Note to the associated Midi's number.
        """
        if self.is_rest:
            return None

        note_base = {
            "C": 0,
            "D": 2,
            "E": 4,
            "F": 5,
            "G": 7,
            "A": 9,
            "B": 11,
        }
        accidental_map = {
            "": 0,
            "#": 1,
            "b": -1,
            "x": 2,
            "bb": -2,
        }

        if self.name not in note_base:
            raise ValueError(f"Unsupported note name: {self.name}")
        if self.accidental not in accidental_map:
            raise ValueError(f"Unsupported accidental: {self.accidental}")
        if self.octave == "":
            raise ValueError("Missing octave for pitched note")

        semitone = note_base[self.name] + accidental_map[self.accidental]
        midi_number = (int(self.octave) + 1) * 12 + semitone #*add one to start from the 0th octave
        return midi_number
        
#TODO: Create a constructor using a string
if __name__ == "__main__":
    #!Run (from root) as python -m lib.note
    silence = Note(('F', 4), 'R', '', '', '')
    note = Note(('F', 4), 'G', '#', '3', ['staccato'])
    print("Silence:", silence)
    print("Is silence silence?:", silence.is_rest)
    print("Note:", note)
    print("Is note silence?", note.is_rest)
