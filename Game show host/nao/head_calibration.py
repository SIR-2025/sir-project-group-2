#! /usr/bin/env python3
# -*- encoding: UTF-8 -*-

import qi
import argparse
import sys

def main(session):
    motion = session.service("ALMotion")

    names = ["HeadYaw", "HeadPitch"]

    # Start with head relaxed so you can move it
    motion.setStiffnesses("Head", 0.0)
    print("Head stiffness set to 0.0 (relaxed).")
    print("Move Nao's head by hand or via Choregraphe, then press ENTER to read angles.")
    print("Press Ctrl+C to quit.\n")

    try:
        while True:
            input(">>> Position the head for a target (e.g. audience left), then press ENTER...")

            # 1) briefly stiffen so it holds pose while we read
            motion.setStiffnesses("Head", 1.0)

            angles = motion.getAngles(names, True)  # in radians
            yaw, pitch = angles
            print("Current head angles:")
            print("  HeadYaw  = {:.3f} rad".format(yaw))
            print("  HeadPitch= {:.3f} rad\n")

            # 2) relax again so you can move it to the next target
            motion.setStiffnesses("Head", 0.0)

    except KeyboardInterrupt:
        print("\nExiting calibration.")
        motion.setStiffnesses("Head", 0.5)  # mild stiffness when done

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="10.0.0.137", help="Nao IP")
    parser.add_argument("--port", type=int, default=9559, help="Naoqi port")
    args = parser.parse_args()

    session = qi.Session()
    try:
        session.connect("tcp://{}:{}".format(args.ip, args.port))
    except RuntimeError:
        print("Can't connect to Naoqi at {}:{}.".format(args.ip, args.port))
        sys.exit(1)

    main(session)
