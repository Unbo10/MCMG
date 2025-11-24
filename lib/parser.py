from fractions import Fraction
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

class Parser:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.score_file = None
        
        self.parsed_dict: dict = {}
        self.type_to_float: dict = {
            "breve": Fraction(2, 1), #*to avoid rounding issues
            "whole": Fraction(1, 1),
            "half": Fraction(1, 2),
            "quarter": Fraction(1, 4),
            "eighth": Fraction(1, 8),
            "16th": Fraction(1, 16),
            "32nd": Fraction(1, 32),
            "64th": Fraction(1, 64),
        }
        self.alter_to_acc: dict = {
            None: "",
            0: "",
            1: "#",
            2: "x",
            -1: "b",
            -2: "bb",
        }

    def mxl_to_xml(self, save_container: bool = False) -> None:
        """
        If self's `file_name` is a `.mxl` file, checks if there already
        exists a previous unpacking. Otherwise, it unpacks its `.xml` score file
        and saves it using `file_name` without its suffix. Optionally, it
        saves the `container.xml` preceeded by `file_name` without its
        suffix and an underscore

        Parameters
        ----------
        - save_container: bool, optional
            If True, saves `container.xml`, resulting from the unzipping of
            the `mxl` file, using `file_name` without its suffix. Defaults
            to False.

        Raises
        ------
        ValueError: If self's `file_name` doesn't have an mxl extension.
        """
        if not self.file_name.endswith('.mxl'):
            raise ValueError("File must have .mxl extension")
        
        prefix = Path(self.file_name).stem #*remove the suffix
        if f"{prefix}_score.xml" in os.listdir("Data/"):
            print(f"{prefix}_score.xml found in the Data/ folder. Skipping conversion to xml.")
            return

        print("Prefix:", prefix)
        #*No need to create a .zip since .mxl's internal structure is the same
        with zipfile.ZipFile(self.file_name, 'r') as zip_ref:
            file_list = zip_ref.namelist() #*should contain score and META-INF/container
            score_path = 'score.xml'
            if save_container:
                if "META-INF/container.xml" in file_list:
                    with zip_ref.open("META-INF/container.xml") as source, open(f'Data/{prefix}_container.xml', 'wb') as target:
                        target.write(source.read()) #*write source.xml into prefix_source.xml

            with zip_ref.open('META-INF/container.xml') as container:
                tree = ET.parse(container)
                rootfile = tree.find('rootfiles/rootfile')
                if rootfile is not None:
                    score_path = rootfile.get("full-path", score_path)

            print("File list:", file_list)
            print("Score path:", score_path)
            if score_path in file_list:
                with zip_ref.open(score_path) as source, open(f'Data/{prefix}_source.xml', 'wb') as target:
                    target.write(source.read()) #*write source.xml into prefix_source.xml
                self.score_file = f'Data/{prefix}_source.xml'
            

    def parse_to_list(self) -> dict:
        """
        Parses self's `source_file` (if not found, calls `mxl_to_xml`), into a
        dictionary whose keys will be the instruments with which each part is
        played, and its items, lists of a list and a tuple: the list will contain
        a tuple (if it is a note) or multiple tuples with three strings (if it
        is a chord):

        (clef, note_name, accidental, octave, articulation)

        - clef will be a tuple (note_name, octave (?)) that depends on the notes'
        measure.
        - note_name will be a string from A to G or R to represent rest.
        - accidental will be '' if natural, '#' if sharp, 'b' if flat, 'x' if
        double-sharp, or 'bb' if double-flat.
        - octave will be a number representing the scale in which the note
        is played (?)
        - articulation refers to particular ways a note may be played

        on the other hand, the tuple will contain two strings:

        (type, duration)

        - type will be the inverse of a non-negative power of 2 up to the
        inverse of 2^6 = 64 (so from 1 to 1/64).
        - duration will be the length of the note depending on the melody's
        beats (?).
        """
        #! The duration may not be necessary if we store the divisions tag from the attributes of each part
        #TODO: Get tempo
        if self.score_file is None:
            self.mxl_to_xml()
        parsed_dict: str = {}
        #*1) Set the score-partwise tag as root
        root = ET.parse(self.score_file).getroot()
        
        #*2) Map each part's id to the instrument it corresponds to
        part_list = root.find('part-list').findall('score-part')
        p_to_inst: dict = {}
        for part in part_list:
            p_to_inst[part.get('id')] = part.find('part-name').text

        for pid, inst in p_to_inst.items():
            parsed_dict[inst] = None #*create the dictionary of staves for each instrument

        #*3) Get each part's info
        parts = root.findall('part')
        is_chord: bool = False
        clefs: list = {}
        for part in parts:
            id: str = part.get('id')
            inst: str = p_to_inst[id]
            print("Instrument:", inst)
            staves = part.find('measure/attributes/staves')
            # print("Staves:", staves.text)
            if staves is not None:
                parsed_dict[inst] = {str(staff): [] for staff in range(1, int(staves.text)+1)}
            else:
                parsed_dict[inst] = {'1': []}
                # raise ValueError("Unsupported: there must be at least two staves in the file")

            print(parsed_dict)
            print("Measures:", list(part.find('measure')))
            for measure in part.findall('measure'):
                if measure.find('attributes/clef') is not None:
                    for clef in measure.findall('attributes/clef'):
                        clefs[clef.get('number')] = (clef.find('sign').text, int(clef.find('line').text))
                    print("Clefs:", clefs)

                notes = list(measure.findall('note'))
                i: int = 0
                j: int = 0
                while i < len(notes):
                    note = notes[i]

                    type = self.type_to_float[note.find('type').text]
                    # print(note.attrib)
                    try:
                        duration = note.find('duration').text
                    except: #*grace note
                        duration = None
                    # print(type, duration)
                    staff = note.find('staff').text if note.find('staff') is not None else "1"
                    if note.find('rest') is not None:
                        parsed_dict[inst][staff].append([[(clefs[staff], 'R', '', '', '')], (type, duration)])
                        i += 1
                    else:
                        try:
                            alter = int(note.find('pitch/alter').text)
                        except:
                            alter = None
                        try:
                            note_name = note.find('pitch/step').text
                        except:
                            #!Weird error
                            continue
                        octave = note.find('pitch/octave').text
                        if note.find('notations/articulations') is not None:
                            articulations = []
                            # print("Articulations:", note.findall('notations/articulations/*')[0].tag)
                            for artic in note.findall('notations/articulations/*'):
                                articulations.append(artic.tag)
                        else:
                            articulations = ['']

                        #*Check if it is a chord
                        if note.find('chord') is not None:
                            is_chord = True
                        else:
                            is_chord = False

                        if is_chord:
                            #*Add the note, with the same duration and type as the first of the chord, to the lists of notes of the chord
                            staff_length = len(parsed_dict[inst][staff])
                            parsed_dict[inst][staff][staff_length - 1][0].append((clefs[staff], note_name, self.alter_to_acc[alter], octave, articulations))
                        else:
                            #*Add a new note
                            parsed_dict[inst][staff].append([[(clefs[staff], note_name, self.alter_to_acc[alter], octave, articulations)], (type, duration)])

                    i += 1

        return parsed_dict
    
#TODO: Create ChordNote class that includes a string representation of the object to work with it in the transition matrix
#TODO: 
    

if __name__ == "__main__":
    # parser = Parser("Data/Nocturne_in_E_flat_Major_Op.9_No.2_Easy.mxl")
    parser = Parser("Data/Bella_Ciao.mxl")
    print(parser.score_file)
    parser.mxl_to_xml(save_container=False)
    lst = parser.parse_to_list()
    print(lst['Piano']['2'])


        
