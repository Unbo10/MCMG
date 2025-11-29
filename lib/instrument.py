import random

import pandas as pd

from .event import Event

"""
A musical instrument based on an n-th Markov chain built using one or multiple musical pieces.
"""
class Instrument:
    def __init__(self, parsed_mxls: list[dict], mc_order: int = 1, name: str = 'piano1', multiple_voices: bool = False, voice: int = -1) -> None:
        self.parsed_mxls: list[dict] = parsed_mxls
        self.mc_order: int = mc_order
        self.name: str = name
        self.tm: pd.DataFrame = pd.DataFrame() #*Transition matrix
        #*To build an 'independent' piano or a multi-voice piano
        self.multiple_voices: bool = multiple_voices
        self.voice: int = voice

    def build_tm(self) -> pd.DataFrame:
        """
        Build `tm` using `parsed_mxls`. It creates an (A1 x ... x An) x (A) matrix, where:
        - If `multiple_voices` is True, Ai will be the set of number of voices-tuples (where each entry is an `mc_order`-tuple) contained in the ith element of `parsed_mxls` (the ith musical piece), and A will be the set of number of voices-tuples (where each entry is an `mc_order`-tuple) contained across any of the n `parsed_mxls`'s voices.
        - Otherwise, Ai will be a tuple with a single `mc-order`-tuple obtained from the ith musical piece that should have a `voice` key (referring to the same voice across all pieces).

        Note
        ----
        Since we are going through all the events twice (one for counting the unique events and another one to feed the transition matrix).
        """
        if self.multiple_voices:
            pass
        else:
            unique_events: set[str] = set()
            voices: list[list[Event]] = []
            #*Traverse through each instrument, each voice and each note to get the unique events
            for parsed_dict in self.parsed_mxls:
                for key, inst_dict in parsed_dict.items():
                    try:
                        voice: list[Event] = inst_dict[str(self.voice)]
                    except KeyError:
                        print(f"Voice {voice} not in this parsed mxl's instrument keys: {list(inst_dict.keys())}. Skipping")
                        continue

                    voices.append(voice)
                    for event in voice:
                        unique_events.add(str(event))

            print(f"Unique events: {list(unique_events)} \n({len(unique_events)} / {len(voice)})")

            lst_unique_events: list[Event] = list(unique_events)
            tm: pd.DataFrame = pd.DataFrame(0, index=lst_unique_events, columns=lst_unique_events, dtype=float)
            #!For now, 1-order MC implemented
            #*For the current event (src), check the next (dest) and increase (src, dest) by 1
            for voice in voices:
                for i in range(len(voice) - 1):
                    src: Event = voice[i]
                    dest: Event = voice[i+1]
                    tm.loc[src, dest] += 1

            #*Make sure all the rows sum 1
            transition_sums: pd.Series = tm.sum(axis=1)
            zero_rows = transition_sums == 0
            tm.loc[zero_rows, :] = 1.0 #*assume no transition to another note means recurrent
            #*Normalize (rows sum 1) and avoid division by zero
            transition_sums: pd.Series = tm.sum(axis=1)
            tm = tm.div(transition_sums, axis=0)

            # print(tm)
            self.tm = tm
            return tm
        
    def simulate(self, init_method: str = 'random', n_simulations: int = 50) -> list[str]:
        """
        From an initial configuration built from an initialization method
        (`init_method`), simulate the Instrument's Markov chain (`tm`). If `tm`
        is empty, `build_tm` is called before proceeding.
        """
        if self.tm.empty:
            self.build_tm()
        #TODO: Implement a method that puts a 1 in a given event's string if present on unique_events
        if init_method == "random":
            #!For now, it is a list of strings, but once the constructor of Event from a str is built, should be refactored to be a list of strings. This is a must before playing it using Midi.
            configs: list[str] = []
            rand_num: int = random.randint(0, len(self.tm) - 1)
            configs.append(self.tm.index[rand_num])
        
            #*Build a mapping note -> notes to which it has a probability > 0
            #*to go to
            nonzero_mask = self.tm > 0 #*mask
            note_mapping: dict = {
                row: nonzero_mask.columns[nonzero_mask.loc[row]].to_numpy()
                for row in nonzero_mask.index
            }
            print(note_mapping)

            for n in range(n_simulations):
                rand_u: float = random.random()
                config_len: int = len(note_mapping[configs[len(configs) - 1]]) #*number of notes it can transition to
                for i in range(1, config_len + 1):
                    print(note_mapping[configs[len(configs) - 1]])
                    if rand_u < i/config_len:
                        i -= 1 #*explain in depth in the document (a.k.a., make the update function explicit)
                        configs.append(note_mapping[configs[len(configs) - 1]][i]) 
                        break

            return configs
            



#TODO: Create a constructor using a string
if __name__ == "__main__":
    parsed_dict: dict = {'Piano': {'1': ["(F,4)C2|staccato>(F,4)C3|>>1/8|1", "(F,4)D3|staccato>>1/8|1", "(F,4)F3|staccato>(F,4)A3|>>1/8|1", "(F,4)A2|staccato>>1/8|1", "(F,4)F3|staccato>(F,4)A3|>>1/8|1", "(F,4)D3|staccato>>1/8|1", "(F,4)F3|staccato>(F,4)A3|>>1/8|1", "(F,4)A2|staccato>>1/8|1", "(F,4)F3|staccato>(F,4)A3|>>1/8|1", "(F,4)A2|staccato>>1/8|1", "(F,4)C3|staccato>(F,4)E3|>>1/8|1", "(F,4)E2|staccato>>1/8|1", "(F,4)C3|staccato>(F,4)E3|>>1/8|1", "(F,4)A2|staccato>>1/8|1", "(F,4)C3|staccato>(F,4)E3|>>1/8|1", "(F,4)E2|staccato>>1/8|1", "(F,4)C3|staccato>(F,4)E3|>>1/8|1", "(F,4)E2|staccato>>1/8|1", "(F,4)B2|staccato>(F,4)E3|>>1/8|1", "(F,4)B1|staccato>>1/8|1", "(F,4)B2|staccato>(F,4)E3|>>1/8|1", "(F,4)E2|staccato>>1/8|1", "(F,4)B2|staccato>(F,4)E3|>>1/8|1", "(F,4)B1|staccato>>1/8|1", "(F,4)B2|staccato>(F,4)E3|>>1/8|1", "(F,4)A2|>>1/2|4"]}}
    piano: Instrument = Instrument([parsed_dict], voice=1)
    # piano.build_tm()
    configs = piano.simulate()
    print(configs)
