from fractions import Fraction
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from .event import Event
from .note import Note

class Parser:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.score_file = file_name if file_name.endswith('xml') else None
        
        self.parsed_dict: dict = {}
        #!We may want to move this dicts to another object
        self.type_to_frac: dict = {
            "breve": Fraction(2, 1), #*To avoid rounding issues
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
            
    def parse_to_dict(self) -> dict:
        """
        Parses self's score into a dictionary whose keys are instruments and
        whose values are dictionaries keyed by staff number. Each staff maps to
        a list of `Event` instances, and each `Event` carries the one or many
        `Note` objects that sounded simultaneously plus their rhythmic info.
        """
        #! The duration may not be necessary if we store the divisions tag from the attributes of each part
        #TODO: Get tempo
        if self.score_file is None:
            self.mxl_to_xml()
        parsed_dict: dict = {}
        #*1) Set the score-partwise tag as root
        root = ET.parse(self.score_file).getroot()
        
        #*2) Map each part's id to the instrument it corresponds to
        part_list = root.find('part-list').findall('score-part')
        p_to_inst: dict = {}
        for part in part_list:
            p_to_inst[part.get('id')] = part.find('part-name').text

        for pid, inst in p_to_inst.items():
            #TODO: Consider the case when there are multiple instruments of the same type
            # if inst in parsed_dict.keys():
            #     inst += '1'
            parsed_dict[inst] = None #*create the dictionary of staves for each instrument

        #*4) Get general info (divisions and tempo)
        info_measure = root.find('part/measure')
        n_divisions: int = int(info_measure.find('attributes/divisions').text)
        try:
            tempo: int = int(float(info_measure.find('direction/sound').get('tempo')))
        except TypeError: #*Instead of having the tempo attribute, some files may have 'dynamics'
            tempo: int = int(float(info_measure.find('direction/sound').get('dynamics')))
        parsed_dict['Info'] = [n_divisions, tempo]

        #*3) Get each part's info
        parts = root.findall('part')
        for part in parts:
            part_id: str = part.get('id')
            inst: str = p_to_inst[part_id]
            print("Instrument:", inst)

            #*Count staves of the first measure
            first_measure = part.find('measure')
            staves_count = 1
            if first_measure is not None:
                staves_tag = first_measure.find('attributes/staves')
                if staves_tag is not None and staves_tag.text:
                    staves_count = int(staves_tag.text)
            parsed_dict[inst] = {str(staff): [] for staff in range(1, staves_count + 1)}

            clefs: dict = {}

            #TODO: Document the rest of the code
            def build_note(note_element: ET.Element, staff_id: str) -> Note:
                clef = clefs.get(staff_id)
                # if clef is None:
                #     raise ValueError(f"Clef not defined for staff {staff_id} in instrument {inst}")
                if note_element.find('rest') is not None:
                    return Note(clef, 'R', '', '', tuple())

                pitch = note_element.find('pitch')
                if pitch is None:
                    raise ValueError("Note without pitch encountered")
                note_name = pitch.findtext('step')
                octave = pitch.findtext('octave', '')
                alter = pitch.findtext('alter')
                alter_val = int(alter) if alter is not None else None
                accidental = self.alter_to_acc.get(alter_val, '')
                if note_name is None:
                    raise ValueError("Pitch step missing in note")

                if note_element.find('notations/articulations') is not None:
                    articulations = tuple(
                        artic.tag for artic in note_element.findall('notations/articulations/*')
                    )
                else:
                    articulations = tuple()

                return Note(clef, note_name, accidental, octave, articulations)

            for measure in part.findall('measure'):
                attributes = measure.find('attributes')
                #*Update the cleff if a measure has a different one
                if attributes is not None:
                    for clef in attributes.findall('clef'):
                        clef_number = clef.get('number', '1')
                        clefs[clef_number] = (clef.find('sign').text, int(clef.find('line').text))
                    print("Clefs:", clefs)

                notes = list(measure.findall('note'))
                i: int = 0
                while i < len(notes):
                    note_element = notes[i]
                    type_tag = note_element.find('type')
                    if type_tag is None or type_tag.text not in self.type_to_frac:
                        i += 1
                        continue
                    note_type = self.type_to_frac[type_tag.text]
                    duration = note_element.findtext('duration')
                    staff = note_element.findtext('staff', '1')

                    staff_events = parsed_dict[inst][staff]
                    note_list = [build_note(note_element, staff)]

                    if note_element.find('rest') is not None:
                        staff_events.append(Event(note_list, (note_type, duration)))
                        i += 1
                        continue

                    j = i + 1
                    while j < len(notes) and notes[j].find('chord') is not None:
                        chord_staff = notes[j].findtext('staff', staff)
                        note_list.append(build_note(notes[j], chord_staff))
                        j += 1

                    staff_events.append(Event(note_list, (note_type, duration)))
                    i = j

        return parsed_dict
    

if __name__ == "__main__":
    # parser = Parser("Data/Nocturne_in_E_flat_Major_Op.9_No.2_Easy.mxl")
    parser = Parser("Data/Bella_Ciao.mxl")
    print(parser.score_file)
    parser.mxl_to_xml(save_container=False)
    lst = parser.parse_to_dict()
    # print(lst['Piano']['2'])
    # print("Parsed dict keys")
    # for key, elem in lst.items():
        # print(key)
    print("Info:", lst['Info'])


        
