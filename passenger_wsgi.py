# cPanel/Passenger entry point
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app_flask import app as application  # Passenger looks for "application"
