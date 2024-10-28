
import argparse
import gzip
from io import BytesIO
from typing import List
from dataclasses import dataclass
from enum import Enum
import events as events
from utils import read_integer, read_float, read_string, read_bytes_as_string

_EVENT_TYPES = {
    # Telemetry events with driver data such as position, speed, engine RPM, etc.
    (0, 7): events.TelemetryEvent,
    (0, 8): events.TelemetryEvent,
    (0, 9): events.TelemetryEvent,
    (0, 10): events.TelemetryEvent,
    (0, 11): events.TelemetryEvent,
    (0, 12): events.TelemetryEvent,
    (0, 13): events.TelemetryEvent,
    (0, 14): events.TelemetryEvent,
    (0, 15): events.TelemetryEvent,
    (0, 16): events.TelemetryEvent,
    # Starting lights
    (1, 10): events.LightEvent,
    # Garage events
    (1, 7): events.GarageEvent,
    # Checkpoint events
    (3, 6): events.CheckpointEvent,
    # Pit lane events
    (5, 2): events.PitLaneEvent,
    # Overtake events
    (3, 48): events.OvertakeEvent,
}


class SessionType(Enum):
    TEST_DAY = 0
    PRACTICE = 1
    QUALIFYING = 2
    WARMUP = 3
    RACE = 4


@dataclass
class Driver:
    num: int
    name: str
    codriver_name: str
    vehicle_name: str
    vehicle_uid: str
    vehicle_version: str
    veh_filename: str
    time_enter: float
    time_exit: float


@dataclass
class ReplayInfo:
    version: str
    rfm: str
    mod_info: str
    slice_count: int
    event_count_total: int
    time_start: float
    time_end: float
    scn_filename: str
    aiw_filename: str
    mod_name: str
    mod_version: str
    mod_uid: str
    track_path: str
    session_type: SessionType
    is_private_session: bool


class Replay:

    def __init__(self, file_path):
        self.vcr_file = Replay._open_vcr_file(file_path)
        self.info: ReplayInfo = self._read_replay_info()
        self.drivers: List[Driver] = self._read_driver_list()
        self._read_slices_header()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.vcr_file.close()

    @property
    def events(self):
        for _ in range(self.info.slice_count):
            slice_time = read_float(self.vcr_file)
            slice_event_count = read_integer(self.vcr_file, 2)
            for _ in range(slice_event_count):
                event_header = read_integer(self.vcr_file)
                event_size = (event_header >> 8) & 0x1ff
                event_class = event_header >> 29
                event_type = (event_header >> 17) & 0x03f
                driver_id = event_header & 0x0ff
                self.vcr_file.read(1)  # Unknown
                event_data = self.vcr_file.read(event_size)
                event = _EVENT_TYPES.get((event_class, event_type), events.UnknownEvent)
                yield event(event_class=event_class, event_type=event_type, time=slice_time, driver=driver_id if driver_id != 255 else None, size=event_size, data=BytesIO(event_data))

    @staticmethod
    def _open_vcr_file(file_path):
        vcr_file = open(file_path, "rb")
        gz_header = b"\x1f\x8b"
        gz = vcr_file.read(2)
        if gz == gz_header:
            vcr_file.close()
            vcr_file = gzip.open(file_path, "rb")
        return vcr_file

    def _read_replay_info(self) -> ReplayInfo:
        # Find the start of the vcr header (index of occurrence of 0x0A)
        header = self.vcr_file.read().find(b"\x0A") + 1
        self.vcr_file.seek(header)
        self.vcr_file.read(4)  # isr tag
        version = self.vcr_file.read(4)
        rfm = read_string(self.vcr_file)
        self.vcr_file.read(4)  # Unknown
        mod_info = read_string(self.vcr_file)
        scn_filename = read_string(self.vcr_file)
        aiw_filename = read_string(self.vcr_file)
        mod_name = read_string(self.vcr_file, 2)
        mod_version = read_string(self.vcr_file, 2)
        mod_uid = read_string(self.vcr_file, 2)
        track_path = read_string(self.vcr_file, 2)
        self.vcr_file.read(1)
        session_type, is_private_session = self._read_session_info()
        self.vcr_file.read(67)  # Unknown
        return ReplayInfo(
            version=version,
            rfm=rfm,
            mod_info=mod_info,
            slice_count=0,
            event_count_total=0,
            time_start=0,
            time_end=0,
            scn_filename=scn_filename,
            aiw_filename=aiw_filename,
            mod_name=mod_name,
            mod_version=mod_version,
            mod_uid=mod_uid,
            track_path=track_path,
            session_type=session_type,
            is_private_session=is_private_session
        )

    def _read_session_info(self) -> (SessionType, bool):
        session_info = read_integer(self.vcr_file, 1)
        session_type_number = session_info & 0xF
        print(f"session_type_number: {session_type_number}")
        if session_type_number == 0:
            session_type = SessionType.TEST_DAY
        elif 1 <= session_type_number <= 4:
            session_type = SessionType.PRACTICE
        elif 5 <= session_type_number <= 8:
            session_type = SessionType.QUALIFYING
        elif session_type_number == 9:
            session_type = SessionType.WARMUP
        elif 10 <= session_type_number <= 13:
            session_type = SessionType.RACE
        else:
            raise ValueError(f"Unknown session type: {session_type_number}")
        is_private_session = (session_info >> 7 & 1) == 1
        return session_type, is_private_session

    def _read_driver_list(self) -> List[Driver]:
        drivers: List[Driver] = []
        driver_count = read_integer(self.vcr_file)
        for _ in range(driver_count):
            num = read_integer(self.vcr_file, 1)
            name = read_string(self.vcr_file, 1)
            codriver_name = read_string(self.vcr_file, 1)
            vehicle_name = read_string(self.vcr_file, 2)
            vehicle_version = read_string(self.vcr_file, 2)
            vehicle_uid = read_string(self.vcr_file, 2)
            veh_filename = read_bytes_as_string(self.vcr_file, 32)
            self.vcr_file.read(48)  # Unknown
            time_enter = read_float(self.vcr_file)
            time_exit = read_float(self.vcr_file)
            driver: Driver = Driver(
                num=num,
                name=name,
                codriver_name=codriver_name,
                vehicle_name=vehicle_name,
                vehicle_uid=vehicle_uid,
                vehicle_version=vehicle_version,
                veh_filename=veh_filename,
                time_enter=time_enter,
                time_exit=time_exit
            )
            drivers.append(driver)
        return drivers

    def _read_slices_header(self):
        self.info.slice_count = read_integer(self.vcr_file)
        self.info.event_count_total = read_integer(self.vcr_file)
        self.info.time_start = read_float(self.vcr_file)
        self.info.time_end = read_float(self.vcr_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process rf2 replay file.")
    parser.add_argument("input", type=str, help="The input VCR file")
    args = parser.parse_args()
    with Replay(args.input) as replay:
        print(f"VCR Version: {replay.info.version}")
        print(f"Number of slices: {replay.info.slice_count}")
        print(f"Number of events: {replay.info.event_count_total}")
        print(f"Drivers:")
        for driver in replay.drivers:
            print(f"  #{driver.num} {driver.name}")
        print("Events:")
        for event in replay.events:
            if isinstance(event, events.UnknownEvent):
                continue  # Skip unknown events
            print(event)
