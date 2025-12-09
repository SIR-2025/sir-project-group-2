#! /usr/bin/env python3
# -*- encoding: UTF-8 -*-

"""
NaoShowController
=================

Modular helper for NAO show behavior:

- Mic pose using Motion Recorder recordings (mic_up / mic_down)
- Async walking + sideways pacing + direction-dependent gaze
- World-fixed gaze using head yaw calibration
- Airborne panic behavior with countdown when put back down

This is NOT a SICApplication. It’s meant to be used from your main
NaoQuizMaster (which already creates a Nao object and orchestrates the show).

Usage from main:

    from nao_show_controller import NaoShowController

    self.show = NaoShowController(
        nao=self.nao,
        nao_ip=self.nao_ip,
        auto_start_airborne_monitor=True,
    )

    # later, during some phase:
    self.show.initial_turn_left_90()
    self.show.say_with_mic_walk_turn_and_gaze("some long text about AZ")
"""

import os
import time
import math
import threading

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

try:
    import qi
except ImportError:
    qi = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
RECORDINGS_DIR = os.path.join(PROJECT_ROOT, "demos", "nao")

MIC_UP_PATH = os.path.join(RECORDINGS_DIR, "mic_up")
MIC_DOWN_PATH = os.path.join(RECORDINGS_DIR, "mic_down")

# --- Gaze calibration (heading = 0, robot facing audience) ---
SCREEN_YAW   = 0.877
SCREEN_PITCH = 0.0

AUDIENCE_LEFT_YAW    = -0.816
AUDIENCE_LEFT_PITCH  = 0.0

AUDIENCE_CENTER_YAW   = -1.488
AUDIENCE_CENTER_PITCH = 0.0

AUDIENCE_RIGHT_YAW   = -2.000
AUDIENCE_RIGHT_PITCH = 0.0

COHOST_YAW   = AUDIENCE_CENTER_YAW
COHOST_PITCH = AUDIENCE_CENTER_PITCH

# Walking / pacing parameters
STRAIGHT_STEP          = 1.0   # meters along the stage
GAZE_STEP_DT           = 0.8
HEAD_MOVE_TIME         = 0.8
FORWARD_PHASE_DURATION = 6.0  # rough time for 1m + gaze


class NaoShowController(object):
    """
    Helper that reuses an existing Nao object and adds:
    - mic pose
    - pacing walk
    - gaze
    - airborne panic
    """

    def __init__(
        self,
        nao: Nao,
        nao_ip: str,
        test_mode: bool = False,
        auto_start_airborne_monitor: bool = True,
    ):
        self.nao = nao               # re-use the Nao created in NaoQuizMaster
        self.nao_ip = nao_ip
        self.test_mode = test_mode

        # Motion recorder recordings
        self.mic_up_recording = None
        self.mic_down_recording = None

        # Robot heading in world frame
        self.heading = 0.0

        # qi / NAOqi services
        self.qi_session = None
        self.motion_service = None
        self.memory_service = None
        self.leds_service = None
        self.tts_service = None

        # Threading
        self._walk_thread = None
        self._airborne_thread = None
        self._stop_airborne_monitor = False
        self._airborne_state = False
        self._airborne_handling = False
        self._ground_countdown_running = False
        self._ground_thread = None

        # Airborne events
        self._airborne_events = 0
        self._airborne_armed = False  # only react once we've seen ground

        if not self.test_mode:
            self._setup_qi()
            self._load_recordings()
        else:
            print("[NaoShowController] TEST_MODE: no qi / recordings")

        if auto_start_airborne_monitor:
            self.start_airborne_monitor()

    # ------------------------------------------------------------------
    # Public API for your main script
    # ------------------------------------------------------------------
    def wake_and_stand(self, posture: str = "Stand", speed: float = 0.7):
        """Optional helper: wake and go to a posture."""
        if self.test_mode or not self.nao:
            print("[NaoShowController] wake_and_stand(): TEST_MODE or no NAO")
            return
        try:
            from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoWakeUpRequest
            self.nao.autonomous.request(NaoWakeUpRequest())
            self.nao.motion.request(NaoPostureRequest(posture, speed))
            time.sleep(2.0)
        except Exception as e:
            print(f"[NaoShowController] ERROR in wake_and_stand: {e}")

    def initial_turn_left_90(self):
        """Turn 90° left so NAO faces along the stage."""
        self._initial_turn_left_90()

    def face_audience(self):
        """Turn robot body back to audience (heading -> 0)."""
        self._face_audience()

    def say_with_mic_walk_turn_and_gaze(self, text: str, speech_duration: float = None):
        """
        High-level behavior:
        - mic pose up (motion recorder),
        - disable left-arm swing,
        - start slow TTS,
        - pacing with gaze for ~speech_duration,
        - mic down, arms normal, face audience.
        """
        self._say_with_mic_walk_turn_and_gaze_internal(text, speech_duration)

    def go_to_rest(self):
        """Optional helper: send to rest."""
        if self.test_mode or not self.nao:
            print("[NaoShowController] go_to_rest(): TEST_MODE or no NAO")
            return
        try:
            from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
            self.nao.autonomous.request(NaoRestRequest())
        except Exception as e:
            print(f"[NaoShowController] ERROR in go_to_rest: {e}")

    def start_airborne_monitor(self):
        """Start footContact monitor in background."""
        if self.test_mode or self.memory_service is None:
            print("[NaoShowController] start_airborne_monitor(): disabled")
            return
        if self._airborne_thread is not None:
            return
        self._stop_airborne_monitor = False
        self._airborne_thread = threading.Thread(
            target=self._airborne_monitor_loop,
            daemon=True,
        )
        self._airborne_thread.start()

    def stop_airborne_monitor(self):
        """Stop the background airborne monitor."""
        self._stop_airborne_monitor = True
        self._airborne_thread = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _setup_qi(self):
        if qi is None:
            print("[NaoShowController] qi module not available; no ALMotion/ALMemory/ALLeds/TTS.")
            return
        try:
            print(f"[NaoShowController] Connecting qi.Session to tcp://{self.nao_ip}:9559 ...")
            self.qi_session = qi.Session()
            self.qi_session.connect(f"tcp://{self.nao_ip}:9559")

            self.motion_service = self.qi_session.service("ALMotion")
            self.memory_service = self.qi_session.service("ALMemory")
            self.leds_service   = self.qi_session.service("ALLeds")
            self.tts_service    = self.qi_session.service("ALTextToSpeech")

            print("[NaoShowController] Connected to ALMotion, ALMemory, ALLeds, ALTextToSpeech")
        except Exception as e:
            print(f"[NaoShowController] WARNING: Could not create qi Session / services: {e}")
            self.motion_service = None
            self.memory_service = None
            self.leds_service   = None
            self.tts_service    = None

    def _load_recordings(self):
        print(f"[NaoShowController] Loading mic_up from {MIC_UP_PATH}")
        try:
            self.mic_up_recording = NaoqiMotionRecording.load(MIC_UP_PATH)
            print("[NaoShowController] Loaded mic_up recording")
        except Exception as e:
            print(f"[NaoShowController] Could not load mic_up: {e}")

        print(f"[NaoShowController] Loading mic_down from {MIC_DOWN_PATH}")
        try:
            self.mic_down_recording = NaoqiMotionRecording.load(MIC_DOWN_PATH)
            print("[NaoShowController] Loaded mic_down recording")
        except Exception as e:
            print(f"[NaoShowController] Could not load mic_down: {e}")

    # ------------------------------------------------------------------
    # LEDs, TTS for panic
    # ------------------------------------------------------------------
    def _set_face_color(self, r: int, g: int, b: int, duration: float = 0.2):
        if self.test_mode or self.leds_service is None:
            print(f"[NaoShowController] set_face_color({r}, {g}, {b}) (no ALLeds)")
            return
        try:
            rgb = (r << 16) | (g << 8) | b
            self.leds_service.fadeRGB("FaceLeds", rgb, duration)
        except Exception as e:
            print(f"[NaoShowController] ERROR in set_face_color: {e}")

    def _stop_all_speech(self):
        if self.tts_service is None:
            print("[NaoShowController] stop_all_speech(): no ALTextToSpeech")
            return
        try:
            print("[NaoShowController] Stopping all speech via ALTextToSpeech.stopAll()")
            self.tts_service.stopAll()
        except Exception as e:
            print(f"[NaoShowController] ERROR in stop_all_speech: {e}")

    def _say_loud_fast_async(self, text: str):
        panic_text = "\\vol=130\\ \\rspd=110\\ " + text
        print(f"[NAO PANIC SAYS] {text}")
        if self.test_mode:
            return
        if self.tts_service is not None:
            def _panic_thread():
                try:
                    self.tts_service.say(panic_text)
                except Exception as e:
                    print(f"[NaoShowController] ERROR in panic say: {e}")
            threading.Thread(target=_panic_thread, daemon=True).start()
        else:
            if not self.nao:
                return
            try:
                self.nao.tts.request(NaoqiTextToSpeechRequest(panic_text), block=False)
            except Exception as e:
                print(f"[NaoShowController] ERROR in fallback panic say: {e}")

    def _say_slow_blocking(self, text: str):
        slow_text = "\\rspd=70\\ " + text
        print(f"[NAO SAYS SLOW] {text}")
        if self.test_mode:
            return
        if self.tts_service is not None:
            try:
                self.tts_service.say(slow_text)
                return
            except Exception as e:
                print(f"[NaoShowController] ERROR in direct say_slow_blocking: {e}")
        if not self.nao:
            return
        try:
            self.nao.tts.request(NaoqiTextToSpeechRequest(slow_text), block=True)
        except Exception as e:
            print(f"[NaoShowController] ERROR in fallback say_slow_blocking: {e}")

    def _say_async(self, text: str):
        slow_text = "\\rspd=80\\ " + text
        print(f"[NAO SAYS ASYNC, SLOW] {text[:60]}...")
        if self.test_mode or not self.nao:
            return
        try:
            self.nao.tts.request(NaoqiTextToSpeechRequest(slow_text), block=False)
        except Exception as e:
            print(f"[NaoShowController] ERROR in say_async: {e}")

    # ------------------------------------------------------------------
    # Mic pose via motion recorder
    # ------------------------------------------------------------------
    def _mic_up(self):
        print("[NAO] mic_up()")
        if self.test_mode or not self.nao or self.mic_up_recording is None:
            print("[NaoShowController] mic_up(): TEST_MODE or mic_up not loaded")
            return
        try:
            self.nao.motion_record.request(PlayRecording(self.mic_up_recording))
        except Exception as e:
            print(f"[NaoShowController] ERROR in mic_up(): {e}")

    def _mic_down(self):
        print("[NAO] mic_down()")
        if self.test_mode or not self.nao or self.mic_down_recording is None:
            print("[NaoShowController] mic_down(): TEST_MODE or mic_down not loaded")
            return
        try:
            self.nao.motion_record.request(PlayRecording(self.mic_down_recording))
        except Exception as e:
            print(f"[NaoShowController] ERROR in mic_down(): {e}")

    # ------------------------------------------------------------------
    # Arm swing control for walking
    # ------------------------------------------------------------------
    def _set_walk_arm_swing(self, left: bool, right: bool):
        if self.motion_service is None:
            print(f"[NaoShowController] set_walk_arm_swing({left}, {right}) – no ALMotion")
            return
        try:
            self.motion_service.setMoveArmsEnabled(left, right)
            print(f"[NAO] setMoveArmsEnabled(left={left}, right={right})")
        except Exception as e:
            print(f"[NaoShowController] ERROR in set_walk_arm_swing: {e}")

    # ------------------------------------------------------------------
    # Heading / turning
    # ------------------------------------------------------------------
    def _get_current_heading(self) -> float:
        if self.motion_service is None:
            print("[NaoShowController] _get_current_heading(): no ALMotion")
            return self.heading
        try:
            pose = self.motion_service.getRobotPosition(False)
            theta = pose[2]
            return math.atan2(math.sin(theta), math.cos(theta))
        except Exception as e:
            print(f"[NaoShowController] ERROR in _get_current_heading: {e}")
            return self.heading

    def _turn_to_heading(self, target_heading: float,
                         max_iter: int = 2, tol: float = 0.05):
        if self.motion_service is None:
            print("[NaoShowController] _turn_to_heading(): no ALMotion")
            return

        target = math.atan2(math.sin(target_heading), math.cos(target_heading))

        for i in range(max_iter):
            if self._airborne_state:
                print("[NaoShowController] _turn_to_heading(): airborne, aborting")
                break

            current = self._get_current_heading()
            diff = target - current
            diff = math.atan2(math.sin(diff), math.cos(diff))

            print(
                f"[NaoShowController] _turn_to_heading iter {i}: "
                f"current={current:.3f}, target={target:.3f}, diff={diff:.3f}"
            )

            if abs(diff) < tol:
                print("[NaoShowController] _turn_to_heading(): within tolerance")
                break

            try:
                self.motion_service.moveTo(0.0, 0.0, diff)
            except Exception as e:
                print(f"[NaoShowController] ERROR in moveTo: {e}")
                break

        self.heading = self._get_current_heading()
        print(f"[NaoShowController] Heading now ~ {self.heading:.3f} rad")

    def _turn_exact_180(self, direction: int = 1):
        current = self._get_current_heading()
        target = current + direction * math.pi
        target = math.atan2(math.sin(target), math.cos(target))
        print(f"[NaoShowController] turn_exact_180(): current={current:.3f}, target={target:.3f}")
        self._turn_to_heading(target)

    def _initial_turn_left_90(self):
        if self.motion_service is None:
            print("[NaoShowController] initial_turn_left_90(): no ALMotion")
            return
        current = self._get_current_heading()
        target = current + math.pi / 2.0
        print(f"[NaoShowController] Initial 90° LEFT: current={current:.3f}, target={target:.3f}")
        self._turn_to_heading(target)

    def _face_audience(self):
        print("[NaoShowController] Facing audience (heading -> 0)")
        self._turn_to_heading(0.0)

    # ------------------------------------------------------------------
    # Head / gaze
    # ------------------------------------------------------------------
    def _set_head(self, yaw: float, pitch: float, duration: float = HEAD_MOVE_TIME):
        if self.test_mode or self.motion_service is None:
            print(f"[NaoShowController] set_head(): yaw={yaw:.3f}, pitch={pitch:.3f}")
            return
        if self._airborne_state:
            return
        try:
            names = ["HeadYaw", "HeadPitch"]
            angles = [yaw, pitch]
            self.motion_service.setStiffnesses("Head", 1.0)
            self.motion_service.angleInterpolation(
                names, angles, [duration, duration], True
            )
        except Exception as e:
            print(f"[NaoShowController] ERROR in set_head: {e}")

    def _compensate_yaw(self, base_yaw: float) -> float:
        yaw = base_yaw - self.heading
        return math.atan2(math.sin(yaw), math.cos(yaw))

    def _look_audience_left(self):
        self._set_head(self._compensate_yaw(AUDIENCE_LEFT_YAW), AUDIENCE_LEFT_PITCH)

    def _look_audience_center(self):
        self._set_head(self._compensate_yaw(AUDIENCE_CENTER_YAW), AUDIENCE_CENTER_PITCH)

    def _look_audience_right(self):
        self._set_head(self._compensate_yaw(AUDIENCE_RIGHT_YAW), AUDIENCE_RIGHT_PITCH)

    def _look_screen(self):
        self._set_head(self._compensate_yaw(SCREEN_YAW), SCREEN_PITCH)

    def _look_cohost(self):
        self._set_head(self._compensate_yaw(COHOST_YAW), COHOST_PITCH)

    # ------------------------------------------------------------------
    # Async walking
    # ------------------------------------------------------------------
    def _walk_thread_target(self, straight: float, side: float, curve: float):
        try:
            if self.motion_service is not None:
                self.motion_service.moveTo(straight, side, curve)
            else:
                self.nao.motion.request(
                    NaoqiMoveToRequest(x=straight, y=side, theta=curve)
                )
        except Exception as e:
            print(f"[NaoShowController] ERROR in _walk_thread_target: {e}")

    def _start_walk_async(self, straight: float, side: float, curve: float = 0.0):
        print(f"[NaoShowController] start_walk_async({straight}, {side}, {curve})")
        if self.test_mode:
            print("[NaoShowController] TEST_MODE: simulate walk")
            return
        if self._airborne_state:
            print("[NaoShowController] Not walking, airborne")
            return
        try:
            if self.motion_service is not None:
                self.motion_service.stopMove()
        except Exception as e:
            print(f"[NaoShowController] WARNING stopMove: {e}")

        try:
            t = threading.Thread(
                target=self._walk_thread_target,
                args=(straight, side, curve),
                daemon=True,
            )
            t.start()
            self._walk_thread = t
        except Exception as e:
            print(f"[NaoShowController] ERROR starting walk thread: {e}")
            try:
                self.nao.motion.request(
                    NaoqiMoveToRequest(x=straight, y=side, theta=curve)
                )
            except Exception as e2:
                print(f"[NaoShowController] ERROR in blocking walk: {e2}")

    def _stop_walk(self):
        print("[NaoShowController] stop_walk()")
        if self.test_mode:
            return
        if self.motion_service is not None:
            try:
                self.motion_service.stopMove()
            except Exception as e:
                print(f"[NaoShowController] ERROR in stop_walk: {e}")

    # ------------------------------------------------------------------
    # Airborne monitoring
    # ------------------------------------------------------------------
    def _handle_airborne(self):
        if self._airborne_handling:
            return
        self._airborne_handling = True

        if self._airborne_events == 1:
            line = "Put me down, put me down, or I am going to explode!"
        else:
            line = "I am not a baby, please put me down!"

        print(f"[NaoShowController] AIRBORNE! Event #{self._airborne_events}")

        self._stop_walk()
        self._stop_all_speech()
        self._set_face_color(255, 0, 0, duration=0.1)
        self._say_loud_fast_async(line)

        time.sleep(2.0)
        self._airborne_handling = False

    def _handle_grounded_after_airborne(self):
        if self._ground_countdown_running:
            return
        self._ground_countdown_running = True
        print("[NaoShowController] Grounded after airborne: countdown")

        self._set_face_color(255, 0, 0, duration=0.2)
        for i in range(4, 0, -1):
            self._say_slow_blocking(str(i))
            time.sleep(1.0)

        self._say_slow_blocking("Just kidding.")
        self._set_face_color(255, 255, 255, duration=0.5)
        self._ground_countdown_running = False

    def _airborne_monitor_loop(self):
        if self.test_mode or self.memory_service is None:
            print("[NaoShowController] Airborne monitor disabled")
            return

        print("[NaoShowController] Airborne monitor started")
        last_state = None

        while not self._stop_airborne_monitor:
            try:
                val = self.memory_service.getData("footContact")
                airborne = (val < 0.5)
            except Exception as e:
                print(f"[NaoShowController] ERROR reading footContact: {e}")
                airborne = False

            if not airborne:
                if not self._airborne_armed:
                    print("[NaoShowController] Ground detected, arming airborne detection")
                self._airborne_armed = True

            if airborne and last_state is not True and self._airborne_armed:
                self._airborne_state = True
                self._airborne_events += 1
                threading.Thread(target=self._handle_airborne, daemon=True).start()
            elif (not airborne) and last_state is not False:
                if self._airborne_state:
                    t = threading.Thread(
                        target=self._handle_grounded_after_airborne,
                        daemon=True,
                    )
                    t.start()
                    self._ground_thread = t
                self._airborne_state = False

            last_state = airborne
            time.sleep(0.1)

        print("[NaoShowController] Airborne monitor stopped")

    # ------------------------------------------------------------------
    # Walk phases + gaze
    # ------------------------------------------------------------------
    def _update_gaze_during_speech(self, cycle_index: int, leg_sign: int):
        """
        leg_sign = +1 → direction A along stage (e.g. mostly LEFT audience)
        leg_sign = -1 → direction B (mostly RIGHT audience)
        """
        if leg_sign > 0:
            pattern = [
                self._look_audience_left,
                self._look_audience_center,
                self._look_screen,
                self._look_audience_center,
            ]
        else:
            pattern = [
                self._look_audience_right,
                self._look_audience_center,
                self._look_cohost,
                self._look_audience_center,
            ]
        func = pattern[cycle_index % len(pattern)]
        func()

    def _walk_phase_with_gaze(self, straight: float, side: float,
                              phase_duration: float, cycle_index: int,
                              leg_sign: int) -> int:
        print(f"[NaoShowController] walk_phase_with_gaze({phase_duration:.1f}s, leg_sign={leg_sign})")
        self._start_walk_async(straight, side, curve=0.0)

        start = time.time()
        while time.time() - start < phase_duration:
            if self._airborne_state:
                print("[NaoShowController] walk_phase: airborne, break")
                break
            self._update_gaze_during_speech(cycle_index, leg_sign)
            cycle_index += 1
            time.sleep(GAZE_STEP_DT)

        self._stop_walk()
        return cycle_index

    def _walk_and_turn_pattern_for_duration(self, total_duration: float):
        """
        Pacing pattern until total_duration is exceeded or airborne.
        Assumes NAO already facing along the stage (e.g. after 90° left).
        """
        start_all = time.time()
        cycle_index = 0
        leg_sign = +1

        while True:
            elapsed = time.time() - start_all
            remaining = total_duration - elapsed
            if remaining <= 0:
                break

            phase = min(FORWARD_PHASE_DURATION, max(remaining, 0.0))
            cycle_index = self._walk_phase_with_gaze(
                straight=STRAIGHT_STEP,
                side=0.0,
                phase_duration=phase,
                cycle_index=cycle_index,
                leg_sign=leg_sign,
            )

            if self._airborne_state:
                break

            elapsed = time.time() - start_all
            if elapsed >= total_duration:
                break

            if leg_sign > 0:
                print("[NaoShowController] Turning 180° left between legs")
                self._turn_exact_180(direction=+1)
            else:
                print("[NaoShowController] Turning 180° right between legs")
                self._turn_exact_180(direction=-1)

            if self._airborne_state:
                break

            leg_sign *= -1

        print(f"[NaoShowController] walk_and_turn finished. Heading={self.heading:.3f}")
        if not self._airborne_state:
            self._face_audience()

    # ------------------------------------------------------------------
    # High-level combo
    # ------------------------------------------------------------------
    def _say_with_mic_walk_turn_and_gaze_internal(self, text: str,
                                                  speech_duration: float = None):
        print("\n------------------------------------------")
        print(f"[NaoShowController] say_with_mic_walk_turn_and_gaze(): {text[:60]}...")
        print("------------------------------------------")

        if self.test_mode or not self.nao:
            print("[NaoShowController] TEST_MODE: mic+walk+gaze simulated")
            return

        if self.mic_up_recording is None or self.mic_down_recording is None:
            print("[NaoShowController] mic_up/down not loaded, just speaking")
            self._say_async(text)
            return

        # mic pose up
        self._mic_up()

        # left arm fixed, right arm free
        self._set_walk_arm_swing(False, True)

        # start speech
        self._say_async(text)

        # duration estimate or provided
        if speech_duration is None:
            approx_duration = max(10.0, (len(text) / 14.0) * 1.2)
        else:
            approx_duration = speech_duration
        print(f"[NaoShowController] Speech duration target ~{approx_duration:.1f}s")

        self._walk_and_turn_pattern_for_duration(approx_duration)

        time.sleep(2.0)

        # mic pose down, arms normal
        self._mic_down()
        self._set_walk_arm_swing(True, True)
