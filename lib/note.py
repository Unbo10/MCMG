from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence, Tuple

"""
Immutable class that represents a single parsed note/rest from `Parser`'s
`parse_to_list`. It contains all the info from a note except its timing:
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
    
    def __repr__(self):
        if self.repr_str is None:
            repr_str: str = f"({self.clef[0]},{self.clef[1]}){self.name}{self.accidental}{self.octave}|"
            if len(self.articulations) > 0:
                for articulation in self.articulations:
                    repr_str += articulation + ","
                    self.repr_str = repr_str[:-1] #*eliminate the last comma
            else:
                self.repr_str = repr_str
        return self.repr_str
        
#TODO: Create a constructor using a string
if __name__ == "__main__":
    #!Run (from root) as python -m lib.note
    silence = Note(('F', 4), 'R', '', '', '')
    note = Note(('F', 4), 'G', '#', '3', ['staccato'])
    print("Silence:", silence)
    print("Is silence silence?:", silence.is_rest)
    print("Note:", note)
    print("Is note silence?", note.is_rest)

