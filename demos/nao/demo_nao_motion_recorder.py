# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_autonomous import (
    NaoRestRequest,
    NaoWakeUpRequest,
)

# Import message types and requests
from sic_framework.devices.common_naoqi.naoqi_motion_recorder import (
    NaoqiMotionRecorderConf,
    NaoqiMotionRecording,
    PlayRecording,
    StartRecording,
    StopRecording,
)
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness

# Import libraries necessary for the demo
import time


class NaoMotionRecorderDemo(SICApplication):
    """
    NAO motion recorder demo application.

    This version is configured to record a 'mic_down' motion:

    - It first plays the previously recorded 'mic_up' motion once
      so the left arm goes into the mic pose.
    - Then it turns stiffness off for the left arm so you can move it by hand.
    - During recording, you move the arm from mic pose DOWN to neutral.
    - The result is saved as 'mic_down' and replayed once.
    """

    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoMotionRecorderDemo, self).__init__()

        # Demo-specific initialization
        self.nao_ip = "10.0.0.137"
        self.motion_name = "mic_down"   # name under which the recording is saved
        self.record_time = 6            # seconds to move the arm from up to down
        self.nao = None

        # Only record the left arm for mic_down
        self.chain = ["LArm"]

        # Name of the existing "mic_up" recording (saved earlier)
        self.mic_up_name = "mic_up"

        self.set_log_level(sic_logging.INFO)

        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/path/to/log/folder")

        self.setup()

    def setup(self):
        """Initialize and configure the NAO robot."""
        self.logger.info("Starting NAO Motion Recorder Demo for mic_down...")

        # Initialize NAO with motion recorder configuration
        conf = NaoqiMotionRecorderConf(use_sensors=True)
        self.nao = Nao(self.nao_ip, motion_record_conf=conf)

    def run(self):
        """Main application logic."""
        try:
            # 1) Wake up the robot so joints are active
            self.logger.info("Waking up NAO...")
            self.nao.autonomous.request(NaoWakeUpRequest())
            time.sleep(1.0)

            # 2) PLAY mic_up ONCE to bring the left arm into mic pose
            try:
                self.logger.info("Loading existing 'mic_up' recording...")
                mic_up_recording = NaoqiMotionRecording.load(self.mic_up_name)
                self.logger.info("Replaying 'mic_up' to move arm into mic pose...")

                # Stiffen left arm for playback
                self.nao.stiffness.request(
                    Stiffness(stiffness=0.7, joints=self.chain)
                )
                self.nao.motion_record.request(PlayRecording(mic_up_recording))

                # Wait a bit to be sure the motion finishes
                time.sleep(2.0)
            except Exception as e:
                self.logger.error(
                    "Could not load or play 'mic_up' recording. "
                    "Make sure it exists and was saved earlier. Error: {}".format(e)
                )
                self.logger.info(
                    "You can still manually move the arm into the mic pose before recording."
                )

            # 3) Turn stiffness OFF so you can move the left arm by hand
            self.logger.info(
                "Setting stiffness to 0.0 for joints: %s (so you can move it by hand)",
                self.chain,
            )
            self.nao.stiffness.request(Stiffness(stiffness=0.0, joints=self.chain))
            time.sleep(0.5)

            # 4) Start recording mic_down
            self.logger.info(
                "Start moving the robot! (not too fast)\n"
                "For mic_down: move the LEFT arm from mic pose DOWN to neutral."
            )
            self.nao.motion_record.request(StartRecording(self.chain))
            time.sleep(self.record_time)

            # 5) Save the recording
            self.logger.info("Saving action as '%s'", self.motion_name)
            recording = self.nao.motion_record.request(StopRecording())
            recording.save(self.motion_name)

            # 6) Replay the recording once
            self.logger.info("Replaying action '%s'", self.motion_name)
            # Enable stiffness for replay
            self.nao.stiffness.request(
                Stiffness(stiffness=0.7, joints=self.chain)
            )

            recording = NaoqiMotionRecording.load(self.motion_name)
            self.nao.motion_record.request(PlayRecording(recording))

            # 7) Always end with a rest
            self.logger.info("Putting NAO to rest...")
            self.nao.autonomous.request(NaoRestRequest())
            self.logger.info("Motion recorder demo completed successfully")

        except Exception as e:
            self.logger.error("Exception: {}".format(e=e))
        finally:
            self.shutdown()


if __name__ == "__main__":
    # Create and run the demo
    demo = NaoMotionRecorderDemo()
    demo.run()
