
from io import BytesIO
from dataclasses import dataclass, field
from utils import read_integer, read_float, read_float2, read_string, read_bytes, read_bytes_as_string


@dataclass
class ReplayEvent:
    """
    Base class for all replay events.
    """
    event_class: int
    event_type: int
    time: float
    driver: int
    size: int
    data: BytesIO  # The actual event content


@dataclass
class UnknownEvent(ReplayEvent):
    """
    Represents an unknown event. Everything that is not documented or not reverse-engineered yet will be represented as this.
    """
    def __str__(self):
        return f"[{self.time}] - UNKNOWN_EVENT (class: {self.event_class}, type: {self.event_type}) for driver {self.driver}"


@dataclass
class LightEvent(ReplayEvent):
    """
    Represents the starting lights.
    """
    light_state: int = field(init=False)

    def __post_init__(self):
        self.light_state = read_integer(self.data, 1)

    def __str__(self):
        return f"[{self.time}] - LIGHT (class: {self.event_class}, type: {self.event_type}): {self.light_state}"


@dataclass
class GarageEvent(ReplayEvent):
    """
    Represents a garage event (entering and leaving the garage).
    """
    timestamp: float = field(init=False)

    def __post_init__(self):
        self.timestamp = read_float(self.data, 4)

    def __str__(self):
        return f"[{self.time}] - GARAGE (class: {self.event_class}, type: {self.event_type}): driver={self.driver} timestamp={self.timestamp}"


@dataclass
class CheckpointEvent(ReplayEvent):
    """
    Represents a checkpoint event (driver completed a sector).
    """
    lap_or_sector_time: float = field(init=False)
    timestamp: float = field(init=False)
    lap: int = field(init=False)
    sector: int = field(init=False)

    def __post_init__(self):
        self.lap_or_sector_time = read_float(self.data, 4)
        self.timestamp = read_float(self.data, 4)
        self.lap = read_integer(self.data, 1)
        sector_idx = read_integer(self.data, 1)
        self.sector = (sector_idx >> 6) & 3

    def __str__(self):
        return f"[{self.time}] - CHECKPOINT (class: {self.event_class}, type: {self.event_type}): driver={self.driver} lap={self.lap} sector={self.sector} time={self.lap_or_sector_time}"


@dataclass
class PitLaneEvent(ReplayEvent):
    """
    Represents a pit lane event (driver entered or left the pit lane, box, requested pit, etc.).
    """
    action: int = field(init=False)

    def __post_init__(self):
        self.action = read_integer(self.data, 1)

    def __str__(self):
        action_str = "Unknown action"
        if self.action == 0:
            action_str = "Unknown, possibly related to the garage (exiting?)"
        elif self.action == 1:
            action_str = "Unknown, possibly related to the garage (entering?)"
        elif self.action == 32:
            action_str = "Exit pit lane or pit limiter disengaged"
        elif self.action == 33:
            action_str = "Requested pit"
        elif self.action == 34:
            action_str = "Entered pit lane or pit limiter engaged"
        elif self.action == 35:
            action_str = "Entered pit box or car on jacks"
        elif self.action == 36:
            action_str = "Exited pit box or car off jacks"
        return f"[{self.time}] - PIT_LANE (class: {self.event_class}, type: {self.event_type}): driver={self.driver} action={action_str} ({self.action})"


@dataclass
class OvertakeEvent(ReplayEvent):
    """
    Represents an overtake event.
    """
    standings: bytes = field(init=False)

    def __post_init__(self):
        self.data.read(21)  # Unknown
        self.standings = read_bytes(self.data, self.size - 21)

    def __str__(self):
        return f"[{self.time}] - OVERTAKE (class: {self.event_class}, type: {self.event_type}): standings={self.standings}"


@dataclass
class TelemetryEvent(ReplayEvent):
    """
    Represents a telemetry event. Contains information about the driver's vehicle such as position, speed, engine RPM, etc.
    https://rf2-vcr-replay-format.fandom.com/wiki/Driver_data
    """
    gear: int = field(init=False)
    steer_yaw: int = field(init=False)
    throttle: int = field(init=False)
    engine_rpm: int = field(init=False)
    in_pit: bool = field(init=False)
    horn: bool = field(init=False)
    acceleration: int = field(init=False)
    following: bool = field(init=False)
    warning_light: bool = field(init=False)
    driver_visible: bool = field(init=False)
    head_light: bool = field(init=False)
    current_driver: int = field(init=False)
    dpart_debris11: bool = field(init=False)
    dpart_debris10: bool = field(init=False)
    dpart_debris9: bool = field(init=False)
    dpart_debris8: bool = field(init=False)
    dpart_debris7: bool = field(init=False)
    dpart_debris6: bool = field(init=False)
    dpart_debris5: bool = field(init=False)
    dpart_debris4: bool = field(init=False)
    dpart_debris3: bool = field(init=False)
    dpart_debris2: bool = field(init=False)
    dpart_debris1: bool = field(init=False)
    dpart_debris0: bool = field(init=False)
    dpart_rwing: bool = field(init=False)
    dpart_fwing: bool = field(init=False)
    dpart_rr: bool = field(init=False)
    dpart_rl: bool = field(init=False)
    dpart_fr: bool = field(init=False)
    dpart_fl: bool = field(init=False)
    tc_level: int = field(init=False)
    brakes: int = field(init=False)
    pos_x: float = field(init=False)
    pos_y: float = field(init=False)
    pos_z: float = field(init=False)
    rot_x: float = field(init=False)
    rot_y: float = field(init=False)
    rot_z: float = field(init=False)

    def __post_init__(self):
        self.gear = self.event_type - 8
        # Read info1 telemetry
        info1 = read_integer(self.data, 4)
        self.steer_yaw = info1 & 127
        self.throttle = info1 >> 11 & 63
        self.engine_rpm = info1 >> 18
        self.in_pit = (info1 >> 17 & 0x1) != 0
        self.horn = (info1 >> 10 & 0x1) != 0
        # Read info2
        info2 = read_integer(self.data, 4)
        self.acceleration = (info2 >> 24) & 0xFF
        self.following = (info2 >> 23 & 0x1) != 0
        self.warning_light = (info2 >> 22 & 0x1) != 0
        self.driver_visible = (info2 >> 21 & 0x1) != 0
        self.head_light = (info2 >> 20 & 0x1) != 0
        self.current_driver = (info2 >> 18) & 0x03
        # Detachable parts from info2
        self.dpart_debris11 = (info2 >> 7) & 0x1 != 0  # Bit 7
        self.dpart_debris10 = (info2 >> 6) & 0x1 != 0  # Bit 6
        self.dpart_debris9 = (info2 >> 5) & 0x1 != 0  # Bit 5
        self.dpart_debris8 = (info2 >> 4) & 0x1 != 0  # Bit 4
        self.dpart_debris7 = (info2 >> 3) & 0x1 != 0  # Bit 3
        self.dpart_debris6 = (info2 >> 2) & 0x1 != 0  # Bit 2
        self.dpart_debris5 = (info2 >> 1) & 0x1 != 0  # Bit 1
        self.dpart_debris4 = (info2 >> 0) & 0x1 != 0  # Bit 0
        self.dpart_debris3 = (info2 >> 31) & 0x1 != 0  # Bit 31
        self.dpart_debris2 = (info2 >> 30) & 0x1 != 0  # Bit 30
        self.dpart_debris1 = (info2 >> 29) & 0x1 != 0  # Bit 29
        self.dpart_debris0 = (info2 >> 28) & 0x1 != 0  # Bit 28
        self.dpart_rwing = (info2 >> 27) & 0x1 != 0  # Bit 27
        self.dpart_fwing = (info2 >> 26) & 0x1 != 0  # Bit 26
        self.dpart_rr = (info2 >> 25) & 0x1 != 0  # Bit 25
        self.dpart_rl = (info2 >> 24) & 0x1 != 0  # Bit 24
        self.dpart_fr = (info2 >> 23) & 0x1 != 0  # Bit 23
        self.dpart_fl = (info2 >> 22) & 0x1 != 0  # Bit 22
        # Speed info
        speed_info = read_integer(self.data, 5)
        self.data.read(25)  # Unknown
        # TC and brakes
        tc_brakes = read_integer(self.data, 1)
        self.tc_level = tc_brakes >> 6
        self.brakes = tc_brakes & 0x3F
        # Position (x, y, z)
        self.pos_x = read_float2(self.data, 4)
        self.pos_y = read_float2(self.data, 4)
        self.pos_z = read_float2(self.data, 4)
        # Rotation (x, y, z)
        self.rot_x = read_float2(self.data, 4)
        self.rot_y = read_float2(self.data, 4)
        self.rot_z = read_float2(self.data, 4)

    def __str__(self):
        return f"[{self.time}] - TELEMETRY: driver={self.driver} pos=({self.pos_x}, {self.pos_y}, {self.pos_z}) gear={self.gear}, throttle={self.throttle}, steer_yaw={self.steer_yaw}, engine_rpm={self.engine_rpm}, in_pit={self.in_pit}"
