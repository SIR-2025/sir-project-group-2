#! /usr/bin/env python3
# -*- encoding: UTF-8 -*-

"""
Nao Mic Pose + Async Walk + Turn + World-Fixed Gaze About AZ Alkmaar
====================================================================

Behavior:
- Connects to NAO via SIC.
- Loads mic_up and mic_down recordings from:
    demos/nao/mic_up
    demos/nao/mic_down
- Uses ALMotion via qi to move the legs and head in parallel:
    - Legs: post.moveTo(...)  (non-blocking)
    - Head: angleInterpolation(...) (slow, smooth)
- Tracks robot heading (how much it has turned) in self.heading.
- While talking slowly about AZ Alkmaar:
    1) mic_up -> left arm in mic pose.
    2) Start TTS asynchronously (slower speech).
    3) Perform one pacing cycle:
         - walk forward 1m
         - turn 180°
         - walk forward 1m again
         - turn back 180°
       During each phase, head moves through:
         left audience, center audience, right audience, co-host, board,
       using heading compensation so these directions stay fixed in the room.
    4) mic_down -> arm back down.
- Finally, NAO goes to rest.
"""

import os
import time
import math

from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices import Nao

from sic_framework.devices.common_naoqi.naoqi_text_to_speech import (
    NaoqiTextToSpeechRequest,
)
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiMoveToRequest,
)
from sic_framework.devices.common_naoqi.naoqi_motion_recorder import (
    NaoqiMotionRecording,
    PlayRecording,
)
from sic_framework.devices.common_naoqi.naoqi_autonomous import (
    NaoWakeUpRequest,
    NaoRestRequest,
)

# qi SDK for ALMotion (head + legs)
try:
    import qi
except ImportError:
    qi = None

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

NAO_IP = "10.0.0.137"   # <-- put your NAO IP here
TEST_MODE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
RECORDINGS_DIR = os.path.join(PROJECT_ROOT, "demos", "nao")

MIC_UP_PATH = os.path.join(RECORDINGS_DIR, "mic_up")
MIC_DOWN_PATH = os.path.join(RECORDINGS_DIR, "mic_down")

# --- Gaze calibration (from your measurements, heading = 0) ---

# Board (screen) to the LEFT of the robot
SCREEN_YAW   = 0.877
SCREEN_PITCH = 0.0

# Audience from robot POV (to the RIGHT):
AUDIENCE_LEFT_YAW    = -0.816   # "Watch left audience" from your log
AUDIENCE_LEFT_PITCH  = 0.0

AUDIENCE_CENTER_YAW   = -1.488  # "Watch middle audience"
AUDIENCE_CENTER_PITCH = 0.0

AUDIENCE_RIGHT_YAW   = -2.000   # "Watch right audience"
AUDIENCE_RIGHT_PITCH = 0.0

# Co-host: for now reuse audience center (you can calibrate separately later)
COHOST_YAW   = AUDIENCE_CENTER_YAW
COHOST_PITCH = AUDIENCE_CENTER_PITCH

# Walking pattern parameters
STRAIGHT_STEP = 1.0      # meters
TURN_ANGLE    = 3.148    # radians (~180 degrees)

# Timing for walking phases (tune based on how fast your NAO actually moves)
FORWARD_PHASE_DURATION = 6.0   # seconds NAO will spend walking 1m forward
TURN_PHASE_DURATION    = 4.0   # seconds NAO will spend turning 180°

# Gaze timing
GAZE_STEP_DT     = 0.8         # seconds between gaze updates
HEAD_MOVE_TIME   = 0.8         # seconds for head to interpolate to new pose (slower)


class NaoMicPoseWalkTurnGazeAZAsync(SICApplication):
    def __init__(self, nao_ip: str, test_mode: bool = False):
        super(NaoMicPoseWalkTurnGazeAZAsync, self).__init__()

        self.nao_ip = nao_ip
        self.test_mode = test_mode
        self.nao = None

        self.mic_up_recording = None
        self.mic_down_recording = None

        # Robot heading (world frame), in radians.
        # 0 at show start, positive = turn left.
        self.heading = 0.0

        # qi session / ALMotion for head + legs
        self.qi_session = None
        self.motion_service = None

        self.set_log_level(sic_logging.INFO)

        if not self.test_mode:
            self._setup_nao()
            self._setup_qi()
            self._load_recordings()
        else:
            print("[NAO] Running in TEST_MODE (no real robot)")

    # -----------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------
    def _setup_nao(self):
        """Connect to NAO via SIC."""
        self.logger.info(f"Connecting to NAO at {self.nao_ip} ...")
        try:
            self.nao = Nao(ip=self.nao_ip)
            self.logger.info("Connected to NAO via SIC")
        except Exception as e:
            self.logger.error(f"Could not connect to NAO: {e}")
            self.test_mode = True

    def _setup_qi(self):
        """Connect to ALMotion via qi for head+leg control (optional)."""
        if self.test_mode or qi is None:
            print("[NAO] qi module not available or TEST_MODE, skipping ALMotion setup.")
            return

        try:
            print(f"[NAO] Connecting qi.Session to tcp://{self.nao_ip}:9559 ...")
            self.qi_session = qi.Session()
            self.qi_session.connect(f"tcp://{self.nao_ip}:9559")

            self.motion_service = self.qi_session.service("ALMotion")
            print("[NAO] Connected to ALMotion via qi")
        except Exception as e:
            print(f"[NAO] WARNING: Could not create qi Session / ALMotion: {e}")
            self.motion_service = None

    def _load_recordings(self):
        """Load mic_up and mic_down motion recordings."""
        self.logger.info(f"Loading mic_up from {MIC_UP_PATH}")
        try:
            self.mic_up_recording = NaoqiMotionRecording.load(MIC_UP_PATH)
            self.logger.info("Loaded mic_up recording")
        except Exception as e:
            self.logger.error(f"Could not load mic_up: {e}")

        self.logger.info(f"Loading mic_down from {MIC_DOWN_PATH}")
        try:
            self.mic_down_recording = NaoqiMotionRecording.load(MIC_DOWN_PATH)
            self.logger.info("Loaded mic_down recording")
        except Exception as e:
            self.logger.error(f"Could not load mic_down: {e}")

    # -----------------------------------------------------------------
    # Head / gaze helpers (world-fixed with heading compensation)
    # -----------------------------------------------------------------
    def set_head(self, yaw: float, pitch: float, duration: float = HEAD_MOVE_TIME):
        """Set head yaw/pitch via ALMotion. If missing, just log."""
        if self.test_mode or self.motion_service is None:
            print(f"[NAO] set_head(): yaw={yaw:.3f}, pitch={pitch:.3f} (no ALMotion)")
            return

        try:
            names = ["HeadYaw", "HeadPitch"]
            angles = [yaw, pitch]
            # duration is the time (in seconds) to reach the target
            self.motion_service.setStiffnesses("Head", 1.0)
            self.motion_service.angleInterpolation(
                names, angles, [duration, duration], True
            )
        except Exception as e:
            print(f"[NAO] ERROR in set_head: {e}")

    def _compensate_yaw(self, base_yaw: float) -> float:
        """
        World-fixed gaze: subtract current heading so that the head
        keeps looking at the same world direction after body turns.
        """
        yaw = base_yaw - self.heading
        # Normalize to [-pi, pi] to avoid wild spins
        yaw = math.atan2(math.sin(yaw), math.cos(yaw))
        return yaw

    def look_audience_left(self):
        yaw = self._compensate_yaw(AUDIENCE_LEFT_YAW)
        self.set_head(yaw, AUDIENCE_LEFT_PITCH)

    def look_audience_center(self):
        yaw = self._compensate_yaw(AUDIENCE_CENTER_YAW)
        self.set_head(yaw, AUDIENCE_CENTER_PITCH)

    def look_audience_right(self):
        yaw = self._compensate_yaw(AUDIENCE_RIGHT_YAW)
        self.set_head(yaw, AUDIENCE_RIGHT_PITCH)

    def look_screen(self):
        yaw = self._compensate_yaw(SCREEN_YAW)
        self.set_head(yaw, SCREEN_PITCH)

    def look_cohost(self):
        yaw = self._compensate_yaw(COHOST_YAW)
        self.set_head(yaw, COHOST_PITCH)

    # -----------------------------------------------------------------
    # Speech + mic pose
    # -----------------------------------------------------------------
    def say_async(self, text: str):
        """
        Non-blocking TTS using SIC (block=False), with slower speech.
        Uses NAO's \\rspd=80\\ markup to slow down the voice.
        """
        slow_text = "\\rspd=80\\ " + text  # 80% of normal speed
        print(f"[NAO SAYS ASYNC, SLOW] {text[:60]}...")
        if self.test_mode or not self.nao:
            return

        try:
            self.nao.tts.request(NaoqiTextToSpeechRequest(slow_text), block=False)
        except Exception as e:
            print(f"[NAO] ERROR in say_async: {e}")

    def mic_up(self):
        """Play the mic_up recording (arm to mic pose)."""
        print("[NAO] mic_up()")
        if self.test_mode or not self.nao or self.mic_up_recording is None:
            print("[NAO] mic_up(): TEST_MODE or mic_up not loaded")
            return
        try:
            self.nao.motion_record.request(PlayRecording(self.mic_up_recording))
        except Exception as e:
            print(f"[NAO] ERROR in mic_up(): {e}")

    def mic_down(self):
        """Play the mic_down recording (arm back to neutral)."""
        print("[NAO] mic_down()")
        if self.test_mode or not self.nao or self.mic_down_recording is None:
            print("[NAO] mic_down(): TEST_MODE or mic_down not loaded")
            return
        try:
            self.nao.motion_record.request(PlayRecording(self.mic_down_recording))
        except Exception as e:
            print(f"[NAO] ERROR in mic_down(): {e}")

    # -----------------------------------------------------------------
    # Async walking (legs with ALMotion.post.moveTo)
    # -----------------------------------------------------------------
    def start_walk_async(self, straight: float, side: float, curve: float):
        """
        Start a non-blocking walk using ALMotion.post.moveTo if available.
        Also updates internal heading estimate.
        """
        print(f"[NAO] start_walk_async(): straight={straight}, side={side}, curve={curve}")
        # Update heading in advance (commanded turn)
        self.heading += curve
        self.heading = math.atan2(math.sin(self.heading), math.cos(self.heading))
        print(f"[NAO] heading now ~ {self.heading:.3f} rad")

        if self.test_mode:
            print("[NAO TEST] (simulated async walk)")
            return

        # Prefer ALMotion async if available
        if self.motion_service is not None:
            try:
                # Cancel any previous walking task to avoid overlap
                self.motion_service.stopMove()
                # Non-blocking move
                self.motion_service.post.moveTo(straight, side, curve)
            except Exception as e:
                print(f"[NAO] ERROR in start_walk_async (ALMotion): {e}")
        else:
            # Fallback: blocking SIC move (head won't update during this move)
            try:
                self.nao.motion.request(
                    NaoqiMoveToRequest(x=straight, y=side, theta=curve)
                )
            except Exception as e:
                print(f"[NAO] ERROR in start_walk_async (SIC fallback): {e}")

    def stop_walk(self):
        """Stop any ongoing walk."""
        print("[NAO] stop_walk()")
        if self.test_mode:
            return

        if self.motion_service is not None:
            try:
                self.motion_service.stopMove()
            except Exception as e:
                print(f"[NAO] ERROR in stop_walk: {e}")

    # -----------------------------------------------------------------
    # Walk phases + gaze while talking
    # -----------------------------------------------------------------
    def _update_gaze_during_speech(self, cycle_index: int):
        """
        Simple gaze pattern based on cycle index.
        Uses world-fixed gaze helpers with heading compensation.
        """
        pattern = [
            self.look_audience_center,
            self.look_audience_left,
            self.look_audience_center,
            self.look_audience_right,
            self.look_cohost,
            self.look_screen,
        ]
        func = pattern[cycle_index % len(pattern)]
        func()

    def walk_phase_with_gaze(self, straight: float, side: float, curve: float,
                             phase_duration: float, cycle_index: int) -> int:
        """
        One phase of motion:
        - Start async walk (forward or turn).
        - For 'phase_duration' seconds, update gaze every GAZE_STEP_DT.
        - Stop walk at the end.
        Returns updated cycle_index for gaze pattern.
        """
        print(f"[NAO] walk_phase_with_gaze(): duration={phase_duration:.1f}s")
        self.start_walk_async(straight, side, curve)

        start = time.time()
        while time.time() - start < phase_duration:
            self._update_gaze_during_speech(cycle_index)
            cycle_index += 1
            time.sleep(GAZE_STEP_DT)

        self.stop_walk()
        return cycle_index

    def pace_one_cycle_with_gaze(self):
        """
        One full pacing cycle while talking:
        - forward 1m
        - turn 180°
        - forward 1m
        - turn back 180°
        Gaze moves through audience/board/co-host during these phases.
        """
        cycle_index = 0

        # 1) forward
        cycle_index = self.walk_phase_with_gaze(
            straight=STRAIGHT_STEP,
            side=0.0,
            curve=0.0,
            phase_duration=FORWARD_PHASE_DURATION,
            cycle_index=cycle_index,
        )

        # 2) turn 180° (left on first cycle)
        cycle_index = self.walk_phase_with_gaze(
            straight=0.0,
            side=0.0,
            curve=TURN_ANGLE,
            phase_duration=TURN_PHASE_DURATION,
            cycle_index=cycle_index,
        )

        # 3) forward again
        cycle_index = self.walk_phase_with_gaze(
            straight=STRAIGHT_STEP,
            side=0.0,
            curve=0.0,
            phase_duration=FORWARD_PHASE_DURATION,
            cycle_index=cycle_index,
        )

        # 4) turn back 180°
        cycle_index = self.walk_phase_with_gaze(
            straight=0.0,
            side=0.0,
            curve=-TURN_ANGLE,
            phase_duration=TURN_PHASE_DURATION,
            cycle_index=cycle_index,
        )

        print(f"[NAO] Completed one pacing cycle. Final heading={self.heading:.3f} rad")

    # -----------------------------------------------------------------
    # Main combined behavior
    # -----------------------------------------------------------------
    def say_with_mic_walk_turn_and_gaze(self, text: str):
        """
        High-level behavior:
        1) mic_up  -> arm to mic pose.
        2) Initial gaze: audience center.
        3) Start speech asynchronously (slower).
        4) Perform one pacing cycle (forward/turn/forward/turn) with gaze updates.
        5) mic_down -> arm back down.
        """
        print("\n------------------------------------------")
        print(f"[NAO] say_with_mic_walk_turn_and_gaze(): {text[:60]}...")
        print("------------------------------------------")

        if self.test_mode or not self.nao:
            print("[NAO TEST] (mic_up)")
            print("[NAO TEST] (async walk+turn + gaze while talking)")
            print("[NAO TEST] (mic_down)")
            return

        if self.mic_up_recording is None or self.mic_down_recording is None:
            print("[NAO] mic_up/down recordings not loaded, just speaking.")
            self.say_async(text)
            return

        # 1) arm up
        self.mic_up()

        # 2) initial gaze: audience center
        self.look_audience_center()

        # 3) async TTS (slow)
        self.say_async(text)

        # 4) one pacing cycle with gaze
        self.pace_one_cycle_with_gaze()

        # small extra wait so he can finish the last word
        time.sleep(2.0)

        # 5) arm down
        self.mic_down()

    # -----------------------------------------------------------------
    # Main test
    # -----------------------------------------------------------------
    def run(self):
        self.logger.info("Starting NaoMicPoseWalkTurnGazeAZAsync test...")

        if self.test_mode or not self.nao:
            print("[NAO] Test mode active or no NAO, nothing to do.")
            return

        try:
            # Wake up and go to Stand
            self.nao.autonomous.request(NaoWakeUpRequest())
            self.nao.motion.request(NaoPostureRequest("Stand", 0.7))
            time.sleep(2)

            # Big, slower dialogue about AZ Alkmaar
            az_text = (
                "Hallo allemaal, ik ben Nao, en vandaag wil ik het rustig hebben "
                "over een fantastische voetbalclub: A Z Alkmaar. "
                "A Z staat bekend om aanvallend en creatief voetbal, "
                "een hele sterke jeugdopleiding, en trouwe supporters in het A F A S stadion. "
                "In tweeduizend negen werd A Z kampioen van Nederland, "
                "en ook nu speelt de club vaak Europees voetbal tegen grote tegenstanders. "
                "Maar wat A Z echt bijzonder maakt, is de sfeer rondom de club: "
                "het is warm, familiair, en tegelijkertijd heel ambitieus. "
                "De spelers vechten negentig minuten lang voor iedere meter, "
                "en de supporters blijven zingen, wat er ook gebeurt. "
                "Als je houdt van attractief voetbal, talentvolle jonge spelers, "
                "en een club die nooit opgeeft, dan moet je A Z Alkmaar zeker volgen."
            )

            self.say_with_mic_walk_turn_and_gaze(az_text)

            self.logger.info("Demo behavior finished, going to rest...")
            self.nao.autonomous.request(NaoRestRequest())
        except Exception as e:
            self.logger.error(f"Error during run: {e}")
        finally:
            self.shutdown()


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("🤖  NAO MIC POSE + ASYNC WALK+TURN + GAZE ABOUT AZ ALKMAAR")
    print("=" * 60)
    print(f"Nao IP:         {NAO_IP}")
    print(f"Test mode:      {TEST_MODE}")
    print(f"Script dir:     {BASE_DIR}")
    print(f"Project root:   {PROJECT_ROOT}")
    print(f"Recordings dir: {RECORDINGS_DIR}")
    print(f"mic_up path:    {MIC_UP_PATH}")
    print(f"mic_down path:  {MIC_DOWN_PATH}")
    print(f"qi module:      {'available' if qi is not None else 'MISSING'}")
    print("=" * 60 + "\n")

    app = NaoMicPoseWalkTurnGazeAZAsync(nao_ip=NAO_IP, test_mode=TEST_MODE)
    app.run()


if __name__ == "__main__":
    main()
