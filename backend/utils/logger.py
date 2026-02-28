import logging

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

logger = logging.getLogger("arthamantri")