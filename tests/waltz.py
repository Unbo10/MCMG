from lib import instrument
from lib.parser import Parser
import time


def waltzes_e_minor():
    p1 = Parser("Data/waltz-in-e-minor-griboyedov.mxl")
    p2 = Parser("Data/waltz-in-e-minor-nikolai-titov.mxl")
    p3 = Parser("Data/waltz-no-7-in-e-minor-grant-dersom.mxl")
    
    dict1 = p1.parse_to_dict()
    dict2 = p2.parse_to_dict()
    dict3 = p3.parse_to_dict()
    piano = instrument.Instrument(
        [dict1, dict2, dict3], voices=[1, 2]
    )
    piano.build_tm(order=1, save_path=f"tms/waltz_e_minor_tm_{int(time.time())}.csv")
    composition = piano.compose(n_simulations=100)
    piano.to_midi(composition, output_path=f"output/3waltz_{int(time.time())}.mid", tempo=100, instruments=["piano", "piano"])
    print("Waltz in E minor composition generated.")

def waltzes_g_major():
    p1 = Parser("Data/waltz-in-g-major-d-844-franz-schubert.mxl")
    p2 = Parser("Data/waltz-in-g-major-nikolai-titov-nikolaj-titov.mxl")
    p3 = Parser("Data/waltz-for-piano-in-g-major-from-robert-schumanns-kinderball-op-130-no-2-but-arrangedtwo-hands.mxl")
    
    dict1 = p1.parse_to_dict()
    dict2 = p2.parse_to_dict()
    dict3 = p3.parse_to_dict()
    piano = instrument.Instrument(
        [dict1, dict2, dict3], voices=[1, 2]
    )
    piano.build_tm(order=1, save_path=f"tms/waltz_g_major_tm_{int(time.time())}.csv")
    composition = piano.compose(n_simulations=100)
    piano.to_midi(composition, output_path=f"output/3waltz_g_major_{int(time.time())}.mid", tempo=180, instruments=["piano", "piano"])
    print("Waltz in G major composition generated.")

def two_waltzes_g_major():
    p1 = Parser("Data/waltz-in-g-major-d-844-franz-schubert.mxl")
    p2 = Parser("Data/waltz-in-g-major-nikolai-titov-nikolaj-titov.mxl")
    
    dict1 = p1.parse_to_dict()
    dict2 = p2.parse_to_dict()
    piano = instrument.Instrument(
        [dict1, dict2], voices=[1, 2]
    )
    piano.build_tm(order=1, save_path=f"tms/waltz_g_major_tm_{int(time.time())}.csv")
    composition = piano.compose(n_simulations=100)
    piano.to_midi(composition, output_path=f"output/2waltz_g_major_{int(time.time())}.mid", tempo=180, instruments=["piano", "piano"])
    print("Waltz in G major composition generated.")

def griboyedov_waltz_remix():
    p = Parser("Data/waltz-in-e-minor-griboyedov.mxl")
    dict1 = p.parse_to_dict()
    piano = instrument.Instrument([dict1], voices=[1,2])
    piano.build_tm(order=3, save_path=f"tms/griboyedov_waltz_tm_{int(time.time())}.csv")
    composition = piano.compose(n_simulations=100)
    piano.to_midi(composition, output_path="output/griboyedov_waltz_remix_order_3.mid", tempo=100, instruments=["piano", "piano"])
    print("Griboyedov Waltz in E minor composition generated.")


if __name__ == "__main__":
    waltzes_g_major()
    
    