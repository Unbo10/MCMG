import random

import pandas as pd
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from .event import Event

"""
A musical instrument based on an n-th Markov chain built using one or multiple musical pieces.
"""
class Instrument:
    def __init__(self, parsed_mxls: list[dict], mc_order: int = 1, name: str = 'piano1', multiple_voices: bool = False, voices: list[int] = [1]) -> None:
        self.parsed_mxls: list[dict] = parsed_mxls
        self.mc_order: int = mc_order
        self.name: str = name
        self.tm: pd.DataFrame = pd.DataFrame() #*Transition matrix
        #*To build an 'independent' piano or a multi-voice piano
        self.multiple_voices: bool = multiple_voices
        self.voices: int = voices
        #*Take the first parsed dict's number of divisions and tempo as a general rule for the instance
        self.divisions: int = parsed_mxls[0]['Info'][0]
        self.tempo: int = parsed_mxls[0]['Info'][1]

    def build_tm(self, output_file: str = None) -> pd.DataFrame:
        """
        Build `tm` using `parsed_mxls`. It creates an (A1 x ... x An) x (A) matrix, where:
        - If `multiple_voices` is True, Ai will be the set of number of voices-tuples (where each entry is an `mc_order`-tuple) contained in the ith element of `parsed_mxls` (the ith musical piece), and A will be the set of number of voices-tuples (where each entry is an `mc_order`-tuple) contained across any of the n `parsed_mxls`'s voices.
        - Otherwise, Ai will be a tuple with a single `mc-order`-tuple obtained from the ith musical piece that should have a `voice` key (referring to the same voice across all pieces).

        Note
        ----
        Since we are going through all the events twice (one for counting the unique events and another one to feed the transition matrix).
        """
        if len(self.voices) == 0:
            raise ValueError("This instance's voice must be a list of at least one valid element, but it is empty")

        unique_events_str: set[str] = set()
        voices: list[list[Event]] = []
        #*1)Traverse through each instrument, each voice and each event to get the unique events
        for parsed_dict in self.parsed_mxls:
            for key, inst_dict in parsed_dict.items():
                if key != 'Info':
                    for voice in self.voices:
                        try:
                            voice: list[Event] = inst_dict[str(voice)] #*get the list of events for each voice (staff)
                        except KeyError:
                            print(f"Voice {voice} not in this parsed mxl's instrument keys: {list(inst_dict.keys())}. Aborting")
                            return

                    #*1.1)Joining events from different voices together and finding the unique combinations
                    voices.append(voice)
                    for i in range(len(inst_dict[str(self.voices[0])])): #*Take the length of the first voice as reference
                        event_str: str = ""
                        #*Traverse all voices for each event
                        try:
                            for voice in self.voices:
                                event_str += str(inst_dict[str(voice)][i])
                                event_str += "&" #*join them using &
                            unique_events_str.add(event_str[:-1])
                        except IndexError:
                            pass

        # print(f"Unique events: {list(unique_events_str)} \n({len(unique_events_str)} / {len(voice)})")
        print(f"Number of unique events: {len(unique_events_str)}")

        lst_unique_events_str = list(unique_events_str)
        tm: pd.DataFrame = pd.DataFrame(0, index=lst_unique_events_str, columns=lst_unique_events_str, dtype=float)
        #!For now, 1-order MC implemented
        #*For the current event (src), check the next (dest) and increase (src, dest) by 1
        for voice in voices:
            for i in range(len(voice) - 1):
                src: Event = voice[i]
                dest: Event = voice[i+1]
                tm.loc[str(src), str(dest)] += 1

        #*Normalize (rows sum 1) and avoid division by zero
        transition_sums: pd.Series = tm.sum(axis=1)
        zero_rows = transition_sums == 0
        tm.loc[zero_rows, :] = 1.0 #*assume no transition to another note means recurrent
        transition_sums: pd.Series = tm.sum(axis=1)
        tm = tm.div(transition_sums, axis=0)

        # print(tm)
        self.tm = tm
    
        if output_file is not None:
            tm.to_csv(output_file)

        return tm
        
    def compose(self, init_method: str = 'random', n_simulations: int = 50) -> list[Event]:
        """
        From an initial configuration built from an initialization method
        (`init_method`), simulate the Instrument's Markov chain (`tm`). If `tm`
        is empty, `build_tm` is called before proceeding.
        """
        if self.tm.empty:
            self.build_tm()
        #TODO: Implement a method that puts a 1 in a given event's string if present on unique_events
        if init_method == "random":
            comp: list[Event] = [] #*Musical composition to return
            rand_num: int = random.randint(0, len(self.tm) - 1)
            comp.append(Event.from_string(self.tm.index[rand_num]))
        
            #*Build a mapping note -> notes to which it has a probability > 0
            #*to go to
            nonzero_mask = self.tm > 0 #*mask
            note_mapping: dict = {
                row: nonzero_mask.columns[nonzero_mask.loc[row]].to_numpy()
                for row in nonzero_mask.index
            }

            for _ in range(n_simulations):
                current_str: str = str(comp[-1])
                successors = note_mapping[current_str]
                if len(successors) == 0:
                    comp.append(comp[-1])
                    continue
                rand_u: float = random.random()
                n_successors: int = len(successors) #*number of notes it can transition to
                current_row: pd.Series = self.tm.loc[current_str]
                # print("Current row")
                # print(current_row)
                sum_probas: float = 0 #*Cummulative transition probabilities
                for i in range(0, n_successors + 1):
                    #*TODO: Modify to use self's tm as in an updating function structure
                    sum_probas += current_row.loc[successors[i]]
                    # print("Sum of probas", sum_probas)
                    if rand_u < sum_probas:
                        i -= 1 #*explain in depth in the document (a.k.a., make the update function explicit)
                        comp.append(Event.from_string(successors[i])) 
                        break

            return comp

    def to_midi(self, events: list[Event], output_path: str, tempo: int = None, velocity: int = 127) -> None:
        """
        Converts a list of events to a MIDI file with path `output_path` using
        the provided `tempo`, `velocity` (volume, suggest to leave it at 127)
        and the instance's `divisions`.

        Parameters
        ----------
        - events: list[Event]
            List of events to parse to a MIDI file
        - output_path: str
            The path to the output MIDI file (this method DOES NOT create
            parent directories).
        - tempo: int, optional
            The tempo of the MIDI track. Defaults to this instance's tempo
        - velocity: int, optional
            The volume of the MIDI track. Defaults to 127
        """
        if not events:
            raise ValueError("No events supplied for MIDI export")
        if tempo is None:
            tempo = self.tempo

        #*1) Creates a MIDI file and track (composition)
        mid = MidiFile(ticks_per_beat=self.divisions) #*empty file
        track = MidiTrack() #*actual composition (list of messages)
        mid.tracks.append(track)
        track.append(MetaMessage('set_tempo', tempo=bpm2tempo(tempo), time=0))

        pending_time = 0
        channel = 0

        #*2) Add each event to the track as a message
        for event in events:
            #*In case an event has no durations, it is calculated based on its type and the track's divisions
            try:
                event_duration = int(event.duration) if event.duration is not None else int(event.type * self.divisions)
            except (TypeError, ValueError):
                event_duration = int(event.type * self.divisions)

            #*Convert note(s) to MIDI number(s)
            midi_notes = []
            for note in event.notes:
                midi_number = note.to_midi_number()
                if midi_number is not None:
                    midi_notes.append(midi_number)

            #*If it is not a rest, just add a delta before the next note is played
            if not midi_notes:
                pending_time += event_duration
                continue

            first = True
            for midi_note in midi_notes:
                delta = pending_time if first else 0 #*wait for a rest in case there was one before
                track.append(Message('note_on', channel=channel, note=midi_note, velocity=velocity, time=delta))
                first = False #*in case it's a chord, all the notes will be played at the same time
            pending_time = 0

            first_off = True
            for midi_note in midi_notes:
                delta = event_duration if first_off else 0 #*play the note for event_duration time units
                track.append(Message('note_off', channel=channel, note=midi_note, velocity=0, time=delta))
                first_off = False #*just like previously, if it is a chord, play the rest simultaneously

        if pending_time > 0:
            track.append(MetaMessage('end_of_track', time=pending_time)) #*in case it ends in a rest
        else:
            track.append(MetaMessage('end_of_track', time=0))

        #*3) Save MIDI file with events to output_path
        mid.save(output_path)


#TODO: Create a constructor using a string
if __name__ == "__main__":
    from .parser import Parser
    #!Weird: when joining Claire de Lune with Happy Birthday, the output track, with 100 simulations, lasts 48 minutes with tempo 200
    # parser: Parser = Parser("Data/Katyusha.mxl")
    # parser: Parser = Parser("Data/Furelise-Beethoven.mxl")
    parser: Parser = Parser("Data/Bella_Ciao_source.xml")
    # parser: Parser = Parser("Data/Gnossienne_No._1.mxl")
    # parser: Parser = Parser("Data/Ave_Maria_Schubert.mxl")
    # parser: Parser = Parser("Data/Clair_de_Lune_Debussy_source.xml")
    parser2: Parser = Parser("Data/Gymnopdie_No.1_Satie_source.xml")
    # parser: Parser = Parser("Data/Nocturne_in_E_flat_Major_Op.9_No.2_Easy_source.xml")
    # parser: Parser = Parser("Data/Happy_Birthday_To_You_source.xml")
    parsed_dict: dict = parser.parse_to_dict()
    print(parsed_dict.keys())
    # piano: Instrument = Instrument([parsed_dict], voice=2)
    piano: Instrument = Instrument([parsed_dict, parser2.parse_to_dict()], voices=[1])
    piano.build_tm()
    # print("Transition matrix")
    # print(piano.tm)
    composition = piano.compose(n_simulations=100)
    print(composition)
    piano.to_midi(composition, "output/test.mid", tempo=None)
