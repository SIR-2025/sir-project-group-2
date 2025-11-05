# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest

# Import message types and requests for motion
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiMoveToRequest,  # This is used to make the robot walk to a specific point
)

# Import libraries necessary for the demo
import time


class NaoWalkDemo(SICApplication):
    """
    NAO walking demo application.
    Demonstrates how to make NAO walk forward slowly.
    
    This demo uses NaoqiMoveToRequest to make the robot walk to a specific point.
    The robot will walk slowly and safely.
    """
    
    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoWalkDemo, self).__init__()
        
        # Demo-specific initialization
        self.nao_ip = "10.0.0.136"  # Your Nao's IP address
        self.nao = None

        self.set_log_level(sic_logging.INFO)
        
        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/nao/logs")
        
        self.setup()
    
    def setup(self):
        """Initialize and configure the NAO robot."""
        self.logger.info("Starting NAO Walking Demo...")
        
        # Initialize the NAO robot
        self.nao = Nao(ip=self.nao_ip)
    
    def run(self):
        """Main application logic."""
        try:
            # Step 1: Make sure the Nao is standing up first
            # Walking is only possible from a standing position
            self.logger.info("Making Nao stand up")
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            time.sleep(2)  # Wait for the Nao to fully stand up
            
            # Step 2: Walk forward slowly
            # Parameters: x = forward distance in meters
            #            y = sideways distance in meters (0 = straight)
            #            theta = rotation in radians (0 = no rotation)
            #self.logger.info("Walking forward 0.3 meters")
            #self.nao.motion.request(NaoqiMoveToRequest(x=0.3, y=0, theta=0))
            
            # Wait for the walking to complete
            # The Nao will automatically stop when it reaches the target
            time.sleep(2)  # Give enough time for the walk to complete
            
            #self.logger.info("rotating left 0.2 radians")
            #self.nao.motion.request(NaoqiMoveToRequest(x=0, y=0, theta=0.6))

            #time.sleep(2)
            #self.logger.info("rotating right 0.2 radians")
            #self.nao.motion.request(NaoqiMoveToRequest(x=0, y=0, theta=-0.6))
            #time.sleep(2)

            # Step 3: Walk backward slowly
            self.logger.info("Walking backward 0.3 meters")
            self.nao.motion.request(NaoqiMoveToRequest(x=0, y=0, theta=3))
            #time.sleep(5)
            
            # Step 4: Reset the LED lights (eyes)
            self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
            
            # Step 5: Always end with a rest position for safety
            # This makes the Nao crouch down safely
            self.logger.info("Putting Nao in rest position")
            self.nao.autonomous.request(NaoRestRequest())

            self.logger.info("Walking demo completed successfully")
            
        except Exception as e:
            # If something goes wrong, log the error
            self.logger.error("Error in walking demo: {}".format(e=e))
            
        finally:
            # Always shutdown the application properly
            self.logger.info("Shutting down application")
            self.shutdown()


if __name__ == "__main__":
    # Create and run the demo
    demo = NaoWalkDemo()
    demo.run()
