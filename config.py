from dataclasses import dataclass, field
import os
from dotenv import load_dotenv
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Debug log the environment variables
logger.debug(f"ALPACA_API_KEY: {os.environ.get('ALPACA_API_KEY')}")
logger.debug(f"ALPACA_SECRET_KEY: {os.environ.get('ALPACA_SECRET_KEY')}")

@dataclass
class AlpacaConfig:
    api_key: str = os.environ.get('ALPACA_API_KEY')
    secret_key: str = os.environ.get('ALPACA_SECRET_KEY')

@dataclass
class Config:
    alpaca: AlpacaConfig = field(default_factory=AlpacaConfig)

config = Config()

# Print configuration status
if config.alpaca.api_key and config.alpaca.secret_key:
    print("Alpaca credentials loaded from environment variables")
    logger.debug(f"API Key: {config.alpaca.api_key}")
    logger.debug(f"Secret Key: {config.alpaca.secret_key}")
else:
    print("Warning: Alpaca credentials not found in environment variables")