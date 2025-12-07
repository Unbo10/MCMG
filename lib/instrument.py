import random

import pandas as pd
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from .event import Event
from .utils import GM_PROGRAMS

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
        voices_dict: dict = {} #*dictionary of each voice's events
        #*1)Traverse through each instrument, each voice and each event to get the unique events
        for parsed_dict in self.parsed_mxls:
            #!Assumes one instrument
            for key, inst_dict in parsed_dict.items():
                if key != 'Info':
                    min_voice_length: int = len(inst_dict[str(self.voices[0])])
                    #*Store the list of events for each voice (staff)
                    for voice in self.voices:
                        try:
                            voices_dict[voice] += inst_dict[str(voice)]
                        except KeyError:
                            voices_dict[voice] = inst_dict[str(voice)]
                            # print(f"Voice {voice} not in this parsed mxl's instrument keys: {list(inst_dict.keys())}. Aborting")
                    for voice, voice_list in voices_dict.items():
                        # print(len(inst_dict[str(voice)]))
                        min_voice_length = min(min_voice_length, len(inst_dict[str(voice)]))

                    #*1.1)Joining events from different voices together and finding the unique combinations
                    for i in range(min_voice_length): #*Take the length of the first voice as reference
                        event_str: str = ""
                        #*Traverse all voices for each event
                        try:
                            for voice in self.voices:
                                event_str += str(voices_dict[voice][i])
                                event_str += "&" #*join them using &
                            unique_events_str.add(event_str[:-1])
                        except IndexError:
                            pass

        # print(f"Unique events: {list(unique_events_str)} \n({len(unique_events_str)} / {len(voice)})")
        print(f"Number of unique events: {len(unique_events_str)}")
        # import pdb; pdb.set_trace()
        # print(unique_events_str)

        lst_unique_events_str = list(unique_events_str)
        tm: pd.DataFrame = pd.DataFrame(0, index=lst_unique_events_str, columns=lst_unique_events_str, dtype=float)
        #!For now, 1-order MC implemented
        #*For the current event's string (src), check the next (dest) and increase (src, dest) by 1
        for i in range(min_voice_length - 1):
            src: str = ""
            dest: str = ""
            for voice_key, voice_events in voices_dict.items():
                src += str(voice_events[i]) + '&'
                dest += str(voice_events[i+1]) + '&'
            tm.loc[src[:-1], dest[:-1]] += 1

        #*Normalize (rows sum 1) and avoid division by zero
        transition_sums: pd.Series = tm.sum(axis=1)
        zero_rows = transition_sums == 0
        tm.loc[zero_rows, :] = 1.0 #*assume no transition to another note means recurrent
        transition_sums: pd.Series = tm.sum(axis=1)
        tm = tm.div(transition_sums, axis=0)

        # print(tm)
        self.tm = tm
        # import pdb; pdb.set_trace()
    
        if output_file is not None:
            tm.to_csv(output_file)

        return tm
        
    def compose(self, init_method: str = 'random', n_simulations: int = 50) -> list[list[Event]]:
        """
        From an initial configuration built from an initialization method
        (`init_method`), simulate the Instrument's Markov chain (`tm`). If `tm`
        is empty, `build_tm` is called before proceeding.
        """
        if self.tm.empty:
            self.build_tm()
        #TODO: Implement a method that puts a 1 in a given event's string if present on unique_events
        if init_method == "random":
            comp: list[list[Event]] = [] #*Musical composition to return
            rand_num: int = random.randint(0, len(self.tm) - 1)
            events_str: list[str] = [ev.strip() for ev in self.tm.index[rand_num].split('&')] #*divide by voices (staves) using their separator, &
            events: list[Event] = []
            for event_str in events_str:
                events.append(Event.from_string(event_str))
            comp.append(events)
        
            #*Build a mapping note -> notes to which it has a probability > 0
            #*to go to
            nonzero_mask = self.tm > 0 #*mask
            note_mapping: dict = {
                row: nonzero_mask.columns[nonzero_mask.loc[row]].to_numpy()
                for row in nonzero_mask.index
            }
            # print(note_mapping)

            for _ in range(n_simulations):
                current_str: str = ""
                for event in comp[-1]:
                    current_str += str(event) + "&"
                    # print(current_str)
                current_str = current_str[:-1]
                # import pdb; pdb.set_trace()
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
                for i in range(0, n_successors):
                    #*TODO: Modify to use self's tm as in an updating function structure
                    sum_probas += current_row.loc[successors[i]]
                    # print("Sum of probas", sum_probas)
                    if rand_u < sum_probas:
                        i -= 1 #*explain in depth in the document (a.k.a., make the update function explicit)
                        # print(successors[i])
                        events_str: list[str] = [ev.strip() for ev in successors[i].split('&')] #*divide by voices (staves) using their separator, &
                        events: list[Event] = []
                        for event_str in events_str:
                            events.append(Event.from_string(event_str))
                        comp.append(events)
                        break

            return comp

    def _event_duration_ticks(self, event: Event) -> int:
        try:
            return int(event.duration) if event.duration is not None else int(event.type * self.divisions)
        except (TypeError, ValueError):
            return int(event.type * self.divisions)

    def _write_voice_track(self, events: list[Event], track: MidiTrack, channel: int, velocity: int) -> None:
        pending_time = 0
        for event in events:
            event_duration = self._event_duration_ticks(event)
            midi_notes = []
            for note in event.notes:
                midi_number = note.to_midi_number()
                if midi_number is not None:
                    midi_notes.append(midi_number)

            if not midi_notes:
                pending_time += event_duration
                continue

            first = True
            for midi_note in midi_notes:
                delta = pending_time if first else 0
                track.append(Message('note_on', channel=channel, note=midi_note, velocity=velocity, time=delta))
                first = False
            pending_time = 0

            first_off = True
            for midi_note in midi_notes:
                delta = event_duration if first_off else 0
                track.append(Message('note_off', channel=channel, note=midi_note, velocity=0, time=delta))
                first_off = False

        if pending_time > 0:
            track.append(MetaMessage('end_of_track', time=pending_time))
        else:
            track.append(MetaMessage('end_of_track', time=0))

    #TODO: Document the code

    def _resolve_instrument(self, name: str) -> tuple[int, bool]:
        program = GM_PROGRAMS.get(name.lower())
        if program is None:
            raise ValueError(f"Unknown instrument '{name}'. Available options: {', '.join(sorted(GM_PROGRAMS.keys()))}")
        return program

    def to_midi(
        self,
        events: list[list[Event]] | list[Event],
        output_path: str,
        tempo: int = None,
        velocity: int = 127,
        instruments: list[str] | str | None = None,
    ) -> None:
        """
        Converts a list of lists events to a MIDI file with path `output_path` using
        the provided `tempo`, `velocity` (volume, suggest to leave it at 127)
        and the instance's `divisions`. You can optionally specify one instrument
        name or a list of instrument names (per voice) using General MIDI labels.

        Parameters
        ----------
        - events: list[list[Event]]
            List of lists of events (each representing an event in a voice)
            to parse to a MIDI file
        - output_path: str
            The path to the output MIDI file (this method DOES NOT create
            parent directories).
        - tempo: int, optional
            The tempo of the MIDI track. Defaults to this instance's tempo
        - velocity: int, optional
            The volume of the MIDI track. Defaults to 127
        - instruments: list[str] | str | None, optional
            Instrument names for each voice. Use common names such as "piano",
            "violin", "guitar", "flute", "drums", etc. Defaults to piano.
        """
        if not events:
            raise ValueError("No events supplied for MIDI export")
        if tempo is None:
            tempo = self.tempo

        # Ensure events organized per voice
        if isinstance(events[0], Event):
            voice_sequences = [events]
        else:
            num_voices = len(events[0])
            voice_sequences = [[] for _ in range(num_voices)]
            for timestep in events:
                if len(timestep) != num_voices:
                    raise ValueError("All time steps must contain the same number of voices")
                for idx, event in enumerate(timestep):
                    voice_sequences[idx].append(event)

        # Resolve instrument list
        if instruments is None:
            instrument_names = ["piano"] * len(voice_sequences)
        elif isinstance(instruments, str):
            instrument_names = [instruments] * len(voice_sequences)
        else:
            if len(instruments) != len(voice_sequences):
                raise ValueError("Number of instruments must match the number of voices")
            instrument_names = instruments

        mid = MidiFile(ticks_per_beat=self.divisions)
        melodic_channel = 0
        for channel, voice_events in enumerate(voice_sequences):
            program, is_percussion = self._resolve_instrument(instrument_names[channel])
            if is_percussion:
                midi_channel = 9
            else:
                midi_channel = melodic_channel
                if midi_channel == 9:
                    midi_channel += 1
                    melodic_channel = midi_channel
                melodic_channel += 1

            track = MidiTrack()
            if channel == 0:
                track.append(MetaMessage('set_tempo', tempo=bpm2tempo(tempo), time=0))
            if not is_percussion:
                track.append(Message('program_change', channel=midi_channel, program=program, time=0))
            mid.tracks.append(track)
            self._write_voice_track(voice_events, track, midi_channel, velocity)

        mid.save(output_path)


#TODO: Create a constructor using a string
if __name__ == "__main__":
    from .parser import Parser
    #!Weird: when joining Claire de Lune with Happy Birthday, the output track, with 100 simulations, lasts 48 minutes with tempo 200
    parser: Parser = Parser("Data/Katyusha.mxl")
    # parser: Parser = Parser("Data/Furelise-Beethoven.mxl")
    # parser: Parser = Parser("Data/Bella_Ciao_source.xml")
    # parser: Parser = Parser("Data/Gnossienne_No._1.mxl")
    # parser: Parser = Parser("Data/Ave_Maria_Schubert.mxl")
    # parser: Parser = Parser("Data/Clair_de_Lune_Debussy_source.xml")
    # parser: Parser = Parser("Data/Gymnopdie_No.1_Satie_source.xml")
    # parser: Parser = Parser("Data/Nocturne_in_E_flat_Major_Op.9_No.2_Easy_source.xml")
    # parser: Parser = Parser("Data/Happy_Birthday_To_You_source.xml")
    # parser: Parser = Parser("Data/Whiplash-Caravan_by_B.F.mxl")
    parser: Parser = Parser("Data/Katyusha_source_modified2.mxl")
    parsed_dict: dict = parser.parse_to_dict()
    print(parsed_dict.keys())
    piano: Instrument = Instrument([parsed_dict], voices=[1, 2])
    # piano: Instrument = Instrument([parsed_dict, parser2.parse_to_dict()], voices=[1, 2])
    piano.build_tm()
    # print("Transition matrix")
    # print(piano.tm)
    composition = piano.compose(n_simulations=50)
    print(composition)
    piano.to_midi(composition, "output/test.mid", tempo=None, instruments=['accordion', 'bass'])
