import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scheduler.solver import TimeSlot
a = TimeSlot('M', 540, 600)
assert not a.overlaps(TimeSlot('M', 600, 660))
assert a.overlaps(TimeSlot('M', 599, 660))
assert not a.overlaps(TimeSlot('T', 540, 600))
print('Adjacent-class boundary passed')
