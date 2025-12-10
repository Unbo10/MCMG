import random

import pandas as pd
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from .event import Event
from .utils import GM_PROGRAMS
from .parser import Parser

"""
A musical instrument based on an n-th Markov chain built using one or multiple musical pieces.
"""
class Instrument:
    def __init__(self, parsed_mxls: list[dict], mc_order: int = 1, name: str = 'piano1', voices: list[int] = [1]) -> None:
        """
        Initialize an Instrument instance capable of building a Markov chain.

        Parameters
        ----------
        parsed_mxls : list[dict]
            Parsed scores (output from `Parser.parse_to_dict`).
        mc_order : int, optional
            Order (context length) of the chain. Defaults to 1.
        name : str, optional
            Identifier/name for this instrument. Defaults to 'piano1'.
        voices : list[int], optional
            Voices/staves to include. Defaults to [1].
        """
        self.parsed_mxls: list[dict] = parsed_mxls
        self.mc_order: int = mc_order
        self.name: str = name
        self.tm: pd.DataFrame = pd.DataFrame()
        self.voices: list[int] = voices
        self.divisions: int = parsed_mxls[0]['Info'][0]
        self.tempo: int = parsed_mxls[0]['Info'][1]

    def build_tm(self, order: int = 1, save_path: str = None, load_path: str = None) -> pd.DataFrame:
        """
        Build the transition matrix `tm`.

        Parameters
        ----------
        order : int, optional
            Context length (n-gram size). Defaults to 1.
        save_path : str, optional
            CSV path to save the matrix. Defaults to None.
        load_path : str, optional
            CSV path to load a precomputed matrix. Defaults to None.

        Returns
        -------
        pandas.DataFrame
            Transition matrix of shape (states x states).

        Notes
        -----
        Conceptually each state is the vector
        $$s_i = \big((e_{i}^{(1)},\\ldots,e_{i}^{(k)}), (e_{i+1}^{(1)},\\ldots,e_{i+1}^{(k)}),\\ldots,(e_{i+\\text{order}-1}^{(1)},\\ldots,e_{i+\\text{order}-1}^{(k)})\\big)$$
        where $k$ is the number of voices and $order$ is the context length. Rows/columns index states and successors $(s_i, e_{i+order})$.
        """
        if load_path is not None:
            self.tm = pd.read_csv(load_path, index_col=0)
            return self.tm

        if len(self.voices) == 0:
            raise ValueError("This instance's voice must be a list of at least one valid element, but it is empty")

        #*1) Gather all events per voice across scores
        unique_ev_str: set[str] = set()
        unique_ev_n_order_str: set[str] = set()
        voices_dict: dict[int, list[Event]] = {voice: [] for voice in self.voices}

        for parsed_dict in self.parsed_mxls:
            for key, inst_dict in parsed_dict.items():
                if key != "Info":
                    for voice in self.voices:
                        voices_dict[voice].extend(inst_dict.get(str(voice), []))

        if not voices_dict:
            raise ValueError("No voices found to build transition matrix")

        #*2) Calculate the minimum length of a voice to make sure no index errors occur
        min_voice_length = min(len(events) for events in voices_dict.values())
        if order >= min_voice_length:
            raise ValueError(f"Order ({order}) must be less than the minimum voice length ({min_voice_length})")

        #*3) Build the unique states of size `order` and their successors (which don't have +)
        for i in range(min_voice_length):
            current_ev = "+".join(
                "&".join(str(voices_dict[voice][(i + j) % min_voice_length]) for voice in self.voices)
                for j in range(order)
            ) #*Join same-time events from different voices with & and same-state lists of events from different times in the past using +
            next_ev = "&".join(str(voices_dict[voice][(i + order) % min_voice_length]) for voice in self.voices) #*Join the immediately next-time events from different voices
            unique_ev_n_order_str.add(current_ev)
            unique_ev_str.add(next_ev)

        # wrap_state = "+".join(
        #     "&".join(str(voices_dict[voice][(min_voice_length - order + j) % min_voice_length]) for voice in self.voices)
        #     for j in range(order)
        # )
        # wrap_next = "&".join(str(voices_dict[voice][0]) for voice in self.voices)
        # unique_ev_n_order_str.add(wrap_state)
        # unique_ev_str.add(wrap_next)

        if len(unique_ev_str) == 0:
            raise ValueError(f"No unique events found. May be related to the choice of the order ({order}), which must be less than the minimum voice length ({min_voice_length})")
        
        # print(f"Unique events: {list(unique_ev_str)} \n({len(unique_ev_str)} / {len(voice)})")
        print(f"Number of unique events: {len(unique_ev_str)}")
        # import pdb; pdb.set_trace()
        # print(unique_ev_str)

        tm: pd.DataFrame = pd.DataFrame(0, index=list(unique_ev_n_order_str), columns=list(unique_ev_str), dtype=float)
        
        #*4) For the current event's string (src), check the next (dest) and increase (src, dest) by 1
        for i in range(min_voice_length):
            src_segments = []
            #*Repeat the process done in 3: create current state using + and & and next state using &
            for j in range(order):
                segment = "&".join(str(voices_dict[voice][(i + j) % min_voice_length]) for voice in self.voices)
                src_segments.append(segment)
            src = "+".join(src_segments)
            dest = "&".join(str(voices_dict[voice][(i + order) % min_voice_length]) for voice in self.voices)
            tm.loc[src, dest] += 1
            # import pdb; pdb.set_trace()


        #*Normalize (rows sum 1) and avoid division by zero
        transition_sums: pd.Series = tm.sum(axis=1)
        zero_rows = transition_sums == 0
        tm.loc[zero_rows, :] = 1.0 #*assume no transition to another note means recurrent
        transition_sums: pd.Series = tm.sum(axis=1)
        tm = tm.div(transition_sums, axis=0)

        # print(tm)
        self.tm = tm
        # import pdb; pdb.set_trace()
    
        if save_path is not None:
            tm.to_csv(save_path)

        return tm
        
    def compose(self, init_method: str = 'random', n_simulations: int = 50, tm_save_path: str | None = None, tm_load_path: str | None = None) -> list[list[Event]]:
        """
        Simulate the Markov chain to obtain a new composition.

        Parameters
        ----------
        init_method : str, optional
            Initialization strategy (currently only 'random'). Defaults to 'random'.
        n_simulations : int, optional
            Number of transitions to sample. Defaults to 50.
        tm_save_path : str, optional
            Path to save `tm` if it needs to be built. Defaults to None.
        tm_load_path : str, optional
            Path to load a precomputed `tm`. Defaults to None.

        Returns
        -------
        list[list[Event]]
            Generated sequence grouped by voices.
        """
        if self.tm.empty:
            self.build_tm(save_path=tm_save_path, load_path=tm_load_path)
        if init_method == "random":
            comp: list[list[Event]] = [] #*Musical composition to return
            rand_num: int = random.randint(0, len(self.tm.columns) - 1)
            first_ev_str: list[str] = []
            current_str: str = self.tm.index[rand_num]

            #*Split in `order` lists of events
            for events in current_str.split('+'):
                first_ev_str.append([])
                for ev in events.split('&'):
                    first_ev_str[len(first_ev_str) - 1].append(ev)

            events: list[Event] = []
            for event_str in first_ev_str[len(first_ev_str) - 1]:
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
                # current_str: str = ""
                # for event in comp[-1]:
                #     current_str += str(event) + "&"
                #     # print(current_str)
                # current_str = current_str[:-1]
                # # import pdb; pdb.set_trace()
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
                    sum_probas += current_row.loc[successors[i]]
                    # print("Sum of probas", sum_probas)
                    if rand_u < sum_probas:
                        i -= 1 #*explain in depth in the document (a.k.a., make the update function explicit)
                        # print(successors[i])
                        next_event_str: str = successors[i]
                        events_str: list[str] = [ev.strip() for ev in next_event_str.split('&')] #*divide by voices (staves) using their separator, &
                        events: list[Event] = []
                        for event_str in events_str:
                            events.append(Event.from_string(event_str))
                        comp.append(events)

                        #*Remove the first events (before the first +) and append the new ones at the end in current_str
                        first_p_idx: int = current_str.find('+')
                        if first_p_idx == -1:
                            current_str = next_event_str
                        else:
                            current_str = current_str[(first_p_idx + 1):] + '+' + next_event_str

                        break

            return comp

    def _event_duration_ticks(self, event: Event) -> int:
        """
        Convert an Event into ticks (based on MusicXML duration/type).

        Parameters
        ----------
        event : Event
            Event whose duration is to be measured.

        Returns
        -------
        int
            Duration in ticks relative to `self.divisions`.
        """
        try:
            return int(event.duration) if event.duration is not None else int(event.type * self.divisions)
        except (TypeError, ValueError):
            return int(event.type * self.divisions)

    def _write_voice_track(self, events: list[Event], track: MidiTrack, channel: int, velocity: int) -> None:
        """
        Write a single voice's events to a MIDI track.

        Parameters
        ----------
        events : list[Event]
            Events to serialize.
        track : MidiTrack
            Target track to append messages.
        channel : int
            MIDI channel to use.
        velocity : int
            Velocity for note-on messages.
        """
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

    def _resolve_instrument(self, name: str) -> tuple[int, bool]:
        """
        Map a user-friendly instrument name to (program, is_percussion).

        Parameters
        ----------
        name : str
            Name key as defined in `GM_PROGRAMS`.

        Returns
        -------
        tuple[int, bool]
            Program number and whether it is percussion (channel 10).
        """
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
        Convert events into a MIDI file.

        Parameters
        ----------
        events : list[list[Event]] | list[Event]
            Either a single voice (list of events) or time steps grouped by voice.
        output_path : str
            Destination path for the MIDI file (directories must already exist).
        tempo : int, optional
            Tempo in BPM. Defaults to the instrument tempo.
        velocity : int, optional
            Note-on velocity (0-127). Defaults to 127.
        instruments : list[str] | str | None, optional
            General MIDI instrument names per voice. Defaults to piano for all.
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


if __name__ == "__main__":
    
    #!Weird: when joining Claire de Lune with Happy Birthday, the output track, with 100 simulations, lasts 48 minutes with tempo 200
    parser: Parser = Parser("Data/Katyusha.mxl")
    # parser: Parser = Parser("Data/Furelise-Beethoven.mxl")
    # parser: Parser = Parser("Data/Bella_Ciao_source.xml")
    parser: Parser = Parser("Data/Gnossienne_No._1.mxl")
    # parser: Parser = Parser("Data/Ave_Maria_Schubert.mxl")
    # parser2: Parser = Parser("Data/Clair_de_Lune_Debussy_source.xml")
    #parser2: Parser = Parser("Data/Gymnopdie_No.1_Satie_source.xml")
    # parser2: Parser = Parser("Data/Nocturne_in_E_flat_Major_Op.9_No.2_Easy_source.xml")
    # parser: Parser = Parser("Data/Happy_Birthday_To_You.mxl")
    # parser: Parser = Parser("Data/Whiplash-Caravan_by_B.F.mxl")
    # parser: Parser = Parser("Data/Katyusha_source_modified2.mxl")
    # parser: Parser = Parser("Data/Van_gogh.mxl")
    parsed_dict: dict = parser.parse_to_dict()
    #parsed_dict2: dict = parser2.parse_to_dict()
    print(parsed_dict.keys())
    # print(parsed_dict['Piano']["1"][:5])
    # print(parsed_dict['Piano']["2"][:5])
    piano: Instrument = Instrument([parsed_dict], voices=[1, 2])
    # piano: Instrument = Instrument([parsed_dict, parser2.parse_to_dict()], voices=[1, 2])
    piano.build_tm(order=3, save_path="tms/test.csv")
    # print("Transition matrix")
    # print(piano.tm)
    composition = piano.compose(n_simulations=100)
    print(composition)
    # piano.to_midi(composition, "output/test.mid", tempo=200, instruments=['guitar', 'piano'])
    piano.to_midi(composition, "output/test.mid", tempo=200, instruments=['accordion'])
