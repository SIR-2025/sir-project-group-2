"""
NAO Connection - Super Simple
==============================

Usage:
    from nao_connection import connect_nao
    nao = connect_nao("10.0.0.137")
"""

import sys
import os
from io import StringIO

from sic_framework.devices import Nao


def connect_nao(ip, quiet=True):
    """
    Connect to NAO robot.
    
    Args:
        ip: NAO IP address (example: "10.0.0.137")
        quiet: Hide verbose output (default: True)
    
    Returns:
        nao: Connected NAO robot object
    """
    print(f"Connecting to NAO at {ip}...")
    
    if quiet:
        # Redirect stdout/stderr to hide verbose SIC output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
    
    try:
        nao = Nao(ip=ip)
    finally:
        if quiet:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    print("Connected!")
    return nao

